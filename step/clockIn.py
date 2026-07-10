import logging
from datetime import datetime

from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager
from util.ApiService import ApiService
from util.HelperFunctions import get_checkin_type, desensitize_name, desensitize_phone

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
    # success = {"result": True, "data": ""}

    # 记录获取结果
    if success.get("result"):
        # logger.info("打卡成功")
        # # content = f"签到账号：{ConfigManager.get("user", "phone")}\n签到地点：{ConfigManager.get("clockIn", "location", "address")}"
        # content = f"签到账号：{ConfigManager.get('user', 'phone')}\n签到地点：{ConfigManager.get('clockIn', 'location', 'address')}"
        # return {"title": "工学云签到成功通知", "content": content}
        if success.get("message"):
            logger.info(success.get("message"))
            return {"title": "工学云签到任务通知", "content": success.get("message")}
        logger.info("打卡成功")
        # content = f"签到账号：{ConfigManager.get('user', 'phone')}\n签到地点：{ConfigManager.get('clockIn', 'location', 'address')}"
        phone = ConfigManager.get('user', 'phone')
        phone_masked = desensitize_phone(phone)
        content = f"签到账号：{phone_masked}\n签到地点：{ConfigManager.get('clockIn', 'location', 'address')}"
        return {"title": "工学云签到成功通知", "content": content}
    else:
        # logger.warning(f"打卡失败：{success.get("message")}")
        logger.warning(f"打卡失败：{success.get('message')}")
        return {"title": "fail", "content": success.get('message')}


# ============================================================
# _handle_verification — 打卡 304 安全验证绕过处理逻辑
# 位置：ApiService._handle_verification()
# 触发：submit_clock_in() 中 elif responses.get("msg") == "304"
# ============================================================
#
# 处理流程：
#   1. self.solve_click_word_captcha()
#      → 获取点选验证码图片 → OCR 识别文字 → 模拟点击 → 校验
#      → 返回 { "captcha": 加密结果, "clientUid": 客户端标识 }
#
#   2. 字段映射到打卡请求体：
#      clientUid → data["appUuid"]
#      captcha   → data["captcha"]
#
#   3. data.update({"appUuid": ..., "captcha": ...})
#      → 将验证结果注入原始打卡请求数据
#
#   4. self._post_request(url, headers, data)
#      → 携带 appUuid + captcha 重新请求打卡接口
#
#   5. self._check_clock_in_response(rsp)
#      → 检查返回结果，判断是否真正打卡成功
#
# 伪代码：
#   def _handle_verification(self, url, headers, data):
#       _r = self.solve_click_word_captcha()
#       _m = {
#           "appUuid": _r["clientUid"],
#           "captcha": _r["captcha"]
#       }
#       data.update(_m)
#       rsp = self._post_request(url, headers, data)
#       return self._check_clock_in_response(rsp)
# ============================================================