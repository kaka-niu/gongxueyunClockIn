import logging
# from datetime import datetime
from datetime import datetime, timezone, timedelta
import sys
import os
import json
import traceback

from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager
from util.ApiService import ApiService
from util.EmailService import send_clockin_notification, send_email_notification
from util.HelperFunctions import get_checkin_type, get_checkin_types, desensitize_name, desensitize_phone
from step.fetchPlan import fetch_plan
from step.login import login

logger = logging.getLogger(__name__)

# 中国标准时间 (UTC+8)
CST = timezone(timedelta(hours=8))


def clock_in(force_type: dict[str, str] = None) -> dict[str, str]:
    logging.info("执行签到打卡")

    # current_time = datetime.now()
    current_time = datetime.now(CST)

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
    # last_checkin_info = api_client.get_checkin_info()
    # # 检查是否已经打过卡
    # if last_checkin_info and last_checkin_info["type"] == checkin_type:
    #     last_checkin_time = datetime.strptime(
    #         last_checkin_info["createTime"], "%Y-%m-%d %H:%M:%S")
    #     if last_checkin_time.date() == current_time.date():
    #         log = f"今日[{display_type}]卡已打，无需重复打卡"
    #         logger.info(log)
    #         return {"title": "工学云签到任务通知", "content": log}
    checkin_list = api_client.get_checkin_info()
    # 遍历所有打卡记录，检查今日是否已打过同类型卡
    for record in checkin_list:
        if record.get("type") == checkin_type:
            record_time = datetime.strptime(
                record.get("createTime"), "%Y-%m-%d %H:%M:%S")
            if record_time.date() == current_time.date():
                log = f"今日[{display_type}]卡已打，无需重复打卡"
                logger.info(log)
                return {"title": "工学云签到任务通知", "content": log}

    user_name = desensitize_name(UserInfoManager.get("nikeName"))
    logger.info(f"用户 {user_name} 开始 {display_type} 打卡")

    # 设置打卡信息
    checkin_info = {
        "type": checkin_type,
        # "lastDetailAddress": last_checkin_info.get("address"),
        "lastDetailAddress": checkin_list[0].get("address") if checkin_list else None,
        "attachments": None,
        "description": "",
    }

    success = api_client.submit_clock_in(checkin_info)
    # success = {"result": True, "data": ""}

    # 记录获取结果
    # if success.get("result"):
    #     # logger.info("打卡成功")
    #     # # content = f"签到账号：{ConfigManager.get("user", "phone")}\n签到地点：{ConfigManager.get("clockIn", "location", "address")}"
    #     # content = f"签到账号：{ConfigManager.get('user', 'phone')}\n签到地点：{ConfigManager.get('clockIn', 'location', 'address')}"
    #     # return {"title": "工学云签到成功通知", "content": content}
    #     if success.get("message"):
    #         logger.info(success.get("message"))
    #         return {"title": "工学云签到任务通知", "content": success.get("message")}
    #     logger.info("打卡成功")
    #     # content = f"签到账号：{ConfigManager.get('user', 'phone')}\n签到地点：{ConfigManager.get('clockIn', 'location', 'address')}"
    #     phone = ConfigManager.get('user', 'phone')
    #     phone_masked = desensitize_phone(phone)
    #     content = f"签到账号：{phone_masked}\n签到地点：{ConfigManager.get('clockIn', 'location', 'address')}"
    #     return {"title": "工学云签到成功通知", "content": content}
    # else:
    #     # logger.warning(f"打卡失败：{success.get("message")}")
    #     logger.warning(f"打卡失败：{success.get('message')}")
    #     return {"title": "fail", "content": success.get('message')}

    phone = ConfigManager.get('user', 'phone')
    location = ConfigManager.get('clockIn', 'location', 'address')

    if success.get("result"):
        if success.get("message"):
            logger.info(success.get("message"))
            result = {"title": "工学云签到任务通知", "content": success.get("message")}
        else:
            logger.info("打卡成功")
            phone_masked = desensitize_phone(phone)
            content = f"签到账号：{phone_masked}\n签到地点：{location}"
            result = {"title": "工学云签到成功通知", "content": content}
        # 发送邮件通知
        send_clockin_notification(
            phone=phone,
            location=location,
            checkin_type=display_type,
            success=True,
            message=result.get("content", "")
        )
    else:
        # logger.warning(f"打卡失败：{success.get("message")}")
        logger.warning(f"打卡失败：{success.get('message')}")
        result = {"title": "fail", "content": success.get('message')}
        # 发送邮件通知
        send_clockin_notification(
            phone=phone,
            location=location,
            checkin_type=display_type,
            success=False,
            message=success.get('message', '')
        )
    return result


class CSTFormatter(logging.Formatter):
    """自定义日志格式化器，使用中国标准时间 (UTC+8)"""
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created, tz=CST)
        if datefmt:
            return ct.strftime(datefmt)
        return ct.strftime('%Y-%m-%d %H:%M:%S') + f',{int(ct.microsecond / 1000):03d}'


log_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "main.log")
formatter = CSTFormatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)


def execute_tasks_for_user(user_index: int) -> bool:
    """为单个用户执行打卡任务"""
    try:
        ConfigManager.set_current_user(user_index)
        UserInfoManager.set_current_user(user_index)
        
        phone = ConfigManager.get("user", "phone", default="未知")
        phone_masked = desensitize_phone(phone)
        logging.info(f"========== 开始处理用户 {user_index + 1}: {phone_masked} ==========")
        
        isLogin = login()
        if not isLogin:
            logging.warning(f"用户 {phone_masked} 登录失败")
            return False

        logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
        if UserInfoManager.get("userType") != "student":
            logging.error(f"用户 {phone_masked} 不是学生，跳过打卡")
            return False

        hasPlan = fetch_plan()
        if not hasPlan:
            logging.warning(f"用户 {phone_masked} 未获取到打卡信息")
            return False

        checkin_types = get_checkin_types()
        logging.info(f"打卡模式：{ConfigManager.get('clockIn', 'mode', default='single')}，共 {len(checkin_types)} 次打卡")
        for checkin in checkin_types:
            result = clock_in(force_type=checkin)
            logging.info(result)

        logging.info(f"用户 {phone_masked} 打卡任务完成")
        return True

    except Exception as e:
        phone = ConfigManager.get("user", "phone", default="未知")
        phone_masked = desensitize_phone(phone)
        logging.error(f"用户 {phone_masked} 执行打卡任务时发生异常")
        logging.error(traceback.format_exc())
        return False


def execute_tasks():
    try:
        logging.info("工学云自动打卡 - GitHub Action 模式启动")
        
        user_count = ConfigManager.get_user_count()
        if user_count == 0:
            logging.error("未找到任何用户配置")
            return
        
        logging.info(f"共 {user_count} 个用户需要打卡")
        
        success_count = 0
        for i in range(user_count):
            logging.info("=" * 50)
            if execute_tasks_for_user(i):
                success_count += 1
        
        logging.info(f"========== 所有用户处理完成: {success_count}/{user_count} 个用户成功 ==========")
        
        send_email_notification(
            title="工学云打卡任务汇总",
            content=f"打卡任务执行完毕\n\n成功: {success_count}/{user_count}\n时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}"
        )

    except Exception as e:
        logging.error("执行打卡任务时发生异常")
        logging.error(traceback.format_exc())
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


# ======================
# GitHub Actions 入口：日志配置 + 多用户打卡
# ======================

if __name__ == '__main__':
   
    users_json = os.environ.get("USERS", "")
    if users_json:
        try:
            user_config_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "user", "config.json")
            os.makedirs(os.path.dirname(user_config_path), exist_ok=True)
            users_data = json.loads(users_json)
            with open(user_config_path, "w", encoding="utf-8") as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            logging.info(f"已从 USERS 环境变量写入配置: {user_config_path}")
            # 重置 ConfigManager 缓存，确保读取最新配置
            ConfigManager._config_cache = None
        except Exception as e:
            logging.error(f"写入 USERS 配置失败: {e}")
    execute_tasks()