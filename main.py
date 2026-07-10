import logging
import sys
import os
import traceback

from manager.ConfigManager import ConfigManager
from step.clockIn import clock_in
from step.fetchPlan import fetch_plan
from step.login import login
from manager.UserInfoManager import UserInfoManager
from util.HelperFunctions import get_checkin_types, desensitize_phone

# ======================
# 日志配置
# ======================
log_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "main.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),  # 写入日志文件
        logging.StreamHandler(sys.stdout)  # 控制台输出
    ]
)


def execute_tasks_for_user(user_index: int) -> bool:
    """为单个用户执行打卡任务"""
    try:
        # 设置当前用户索引
        ConfigManager.set_current_user(user_index)
        UserInfoManager.set_current_user(user_index)
        
        phone = ConfigManager.get("user", "phone", default="未知")
        phone_masked = desensitize_phone(phone)
        # logging.info(f"========== 开始处理用户 {user_index + 1}: {phone} ==========")
        logging.info(f"========== 开始处理用户 {user_index + 1}: {phone_masked} ==========")
        
        # 登录
        isLogin = login()
        if not isLogin:
            # logging.warning(f"用户 {phone} 登录失败")
            logging.warning(f"用户 {phone_masked} 登录失败")
            return False

        logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
        if UserInfoManager.get("userType") != "student":
            # logging.error(f"用户 {phone} 不是学生，跳过打卡")
            logging.error(f"用户 {phone_masked} 不是学生，跳过打卡")
            return False

        # 获取打卡信息
        hasPlan = fetch_plan()
        if not hasPlan:
            # logging.warning(f"用户 {phone} 未获取到打卡信息")
            logging.warning(f"用户 {phone_masked} 未获取到打卡信息")
            return False

        # 根据模式执行打卡（支持 twice_daily 一天两次打卡）
        checkin_types = get_checkin_types()
        logging.info(f"打卡模式：{ConfigManager.get('clockIn', 'mode', default='single')}，共 {len(checkin_types)} 次打卡")
        for checkin in checkin_types:
            result = clock_in(force_type=checkin)
            logging.info(result)

        # logging.info(f"用户 {phone} 打卡任务完成")
        logging.info(f"用户 {phone_masked} 打卡任务完成")
        return True

    except Exception as e:
        phone = ConfigManager.get("user", "phone", default="未知")
        phone_masked = desensitize_phone(phone)
        # logging.error(f"用户 {phone} 执行打卡任务时发生异常")
        logging.error(f"用户 {phone_masked} 执行打卡任务时发生异常")
        logging.error(traceback.format_exc())
        return False


def execute_tasks():
    try:
        logging.info("开始执行打卡任务")
        
        # 获取用户数量
        user_count = ConfigManager.get_user_count()
        if user_count == 0:
            logging.error("未找到任何用户配置")
            input("按回车键退出...")
            return
        
        logging.info(f"共检测到 {user_count} 个用户配置")
        
        # 遍历所有用户执行打卡
        success_count = 0
        for i in range(user_count):
            if execute_tasks_for_user(i):
                success_count += 1
        
        logging.info(f"========== 所有用户处理完成: {success_count}/{user_count} 个用户成功 ==========")
        input("按回车键退出...")

    except Exception as e:
        logging.error("执行打卡任务时发生异常")
        logging.error(traceback.format_exc())
        input("按回车键退出...")


if __name__ == '__main__':
    execute_tasks()