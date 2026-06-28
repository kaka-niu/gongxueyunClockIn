import json
import logging
import os
import sys
import traceback
from pathlib import Path

# 确保能导入项目模块
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager
from manager.PlanInfoManager import PlanInfoManager
from step.clockIn import clock_in
from step.fetchPlan import fetch_plan
from step.login import login
from util.HelperFunctions import get_checkin_types

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def load_users_from_secret() -> list[dict]:
    """
    从环境变量 USERS 读取用户配置，支持单用户和多用户两种格式。

    Returns:
        list[dict]: 用户配置列表，每个元素为 {"config": {...}} 格式
    """
    users_env = os.environ.get("USERS", "")
    if not users_env:
        logger.error("未设置 USERS 环境变量")
        return []

    try:
        data = json.loads(users_env)
    except json.JSONDecodeError as e:
        logger.error(f"USERS 环境变量 JSON 解析失败: {e}")
        return []

    # 判断是单用户还是多用户
    if isinstance(data, list):
        # 多用户：直接返回列表
        return data
    elif isinstance(data, dict) and "config" in data:
        # 单用户：包装成列表
        return [data]
    else:
        logger.error("USERS 环境变量格式不正确")
        return []


def execute_for_user(user_config: dict) -> dict:
    """
    为单个用户执行完整的打卡流程。

    Args:
        user_config: 单个用户的配置，格式为 {"config": {...}}

    Returns:
        dict: 执行结果 {"success": bool, "phone": str, "message": str}
    """
    config = user_config.get("config", {})
    phone = config.get("user", {}).get("phone", "unknown")

    logger.info(f"{'='*50}")
    logger.info(f"开始处理用户: {phone}")
    logger.info(f"{'='*50}")

    try:
        # 将用户配置写入缓存（不写文件，避免并发冲突）
        ConfigManager._config_cache = config

        # 清空之前的用户信息缓存，确保重新登录
        UserInfoManager._cache = None
        PlanInfoManager._cache = None

        # 登录
        is_login = login()
        if not is_login:
            logger.warning(f"用户 {phone} 登录失败")
            return {"success": False, "phone": phone, "message": "登录失败"}

        # 获取打卡计划
        has_plan = fetch_plan()
        if not has_plan:
            logger.warning(f"用户 {phone} 未获取到打卡计划")
            return {"success": False, "phone": phone, "message": "未获取到打卡计划"}

        # 执行打卡
        checkin_types = get_checkin_types()
        logger.info(f"用户 {phone} 打卡模式：{ConfigManager.get('clockIn', 'mode', default='single')}，共 {len(checkin_types)} 次打卡")

        all_success = True
        for checkin in checkin_types:
            result = clock_in(force_type=checkin)
            logger.info(f"用户 {phone} 打卡结果: {result}")
            if not result.get("result"):
                all_success = False

        if all_success:
            logger.info(f"用户 {phone} 打卡任务全部完成")
            return {"success": True, "phone": phone, "message": "打卡成功"}
        else:
            logger.warning(f"用户 {phone} 部分打卡失败")
            return {"success": False, "phone": phone, "message": "部分打卡失败"}

    except Exception as e:
        logger.error(f"用户 {phone} 执行异常: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "phone": phone, "message": str(e)}


def main():
    """
    GitHub Action 入口：读取 USERS 环境变量，遍历所有用户执行打卡。
    """
    logger.info("工学云自动打卡 - GitHub Action 模式启动")

    users = load_users_from_secret()
    if not users:
        logger.error("没有可用的用户配置，退出")
        sys.exit(1)

    logger.info(f"共 {len(users)} 个用户需要打卡")

    results = []
    for user_config in users:
        result = execute_for_user(user_config)
        results.append(result)

    # 汇总结果
    logger.info(f"{'='*50}")
    logger.info("所有用户打卡完成，汇总结果：")
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    for r in results:
        status = "✅ 成功" if r["success"] else "❌ 失败"
        logger.info(f"  {status} - {r['phone']}: {r['message']}")
    logger.info(f"总计: {success_count} 成功, {fail_count} 失败")
    logger.info(f"{'='*50}")

    # 如果有失败，退出码设为 1
    if fail_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()