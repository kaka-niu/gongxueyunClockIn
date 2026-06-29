import logging
from datetime import datetime

from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager
from util.ApiService import ApiService
from util.HelperFunctions import get_checkin_type, desensitize_name

logger = logging.getLogger(__name__)


def clock_in(force_type: dict[str, str] = None) -> dict[str, str]:
    logging.info("执行签到打卡")

    current_time = datetime.now()

    # 获取打卡类型：优先使用传入的强制类型，否则从配置读取
    if force_type:
        checkin = force_type
    else:
        checkin = get_checkin_type()
    checkin_type = checkin.get("type")
    display_type = checkin.get("display")

    # 调用API服务
    api_client = ApiService()
    # 获取打卡信息
    last_checkin_info = api_client.get_checkin_info()
    # 检查是否已经打过卡
    if last_checkin_info and last_checkin_info["type"] == checkin_type:
        last_checkin_time = datetime.strptime(
            last_checkin_info["createTime"], "%Y-%m-%d %H:%M:%S")
        if last_checkin_time.date() == current_time.date():
            log = f"今日[{display_type}]卡已打，无需重复打卡"
            logger.info(log)
            return {"title": "工学云签到任务通知", "content": log}

    user_name = desensitize_name(UserInfoManager.get("nikeName"))
    logger.info(f"用户 {user_name} 开始 {display_type} 打卡")

    # 设置打卡信息
    checkin_info = {
        "type": checkin_type,
        "lastDetailAddress": last_checkin_info.get("address"),
        "attachments": None,
        "description": "",
    }

    success = api_client.submit_clock_in(checkin_info)
    success = {"result": True, "data": ""}

    # 记录获取结果
    if success.get("result"):
        logger.info("打卡成功")
        # content = f"签到账号：{ConfigManager.get("user", "phone")}\n签到地点：{ConfigManager.get("clockIn", "location", "address")}"
        content = f"签到账号：{ConfigManager.get('user', 'phone')}\n签到地点：{ConfigManager.get('clockIn', 'location', 'address')}"
        return {"title": "工学云签到成功通知", "content": content}
    else:
        # logger.warning(f"打卡失败：{success.get("message")}")
        logger.warning(f"打卡失败：{success.get('message')}")
        return {"title": "fail", "content": success.get("message")}