import logging
import threading
# from datetime import datetime, timedelta
from datetime import datetime, timedelta, timezone

import requests

from manager.ConfigManager import ConfigManager

# 尝试导入主模块的日志上下文，失败则创建本地版本
try:
    from main import _log_ctx
except ImportError:
    _log_ctx = threading.local()

logger = logging.getLogger(__name__)

# 中国标准时间 (UTC+8)
CST = timezone(timedelta(hours=8))


def get_current_month_info() -> dict:
    """
    获取当前月份的开始和结束时间。

    该方法计算当前月份的开始日期和结束日期，并将它们返回为字典，
    字典中包含这两项的字符串表示。

    Returns:
        包含当前月份开始和结束时间的字典。
    """
    # now = datetime.now()
    now = datetime.now(CST)
    # 当前月份的第一天
    start_of_month = datetime(now.year, now.month, 1)

    # 下个月的第一天
    if now.month == 12:
        next_month_start = datetime(now.year + 1, 1, 1)
    else:
        next_month_start = datetime(now.year, now.month + 1, 1)

    # 当前月份的最后一天（下个月第一天减一天）
    end_of_month = next_month_start - timedelta(days=1)

    # 格式化为字符串
    start_time_str = start_of_month.strftime("%Y-%m-%d %H:%M:%S")
    end_time_str = end_of_month.strftime("%Y-%m-%d 00:00:00Z")

    return {"startTime": start_time_str, "endTime": end_time_str}


def desensitize_name(name: str) -> str:
    """
    对姓名进行脱敏处理，将中间部分字符替换为星号。

    Args:
        name (str): 待脱敏的姓名。

    Returns:
        str: 脱敏后的姓名。
    """
    name = name.strip()  # 去除前后空格，防止输入有空格影响判断

    n = len(name)
    if n < 3:
        return f"{name[0]}*"
    else:
        return f"{name[0]}{'*' * (n - 2)}{name[-1]}"


def desensitize_phone(phone: str) -> str:
    """
    对手机号进行脱敏处理，保留前3位和后4位，中间用星号替代。

    Args:
        phone (str): 待脱敏的手机号。

    Returns:
        str: 脱敏后的手机号，如 138****1234。
    """
    phone = phone.strip()
    n = len(phone)
    if n < 7:
        return phone[:1] + '*' * (n - 1) if n > 1 else '*'
    return f"{phone[:3]}{'*' * (n - 7)}{phone[-4:]}"


def desensitize_address(address: str) -> str:
    """
    对地址进行脱敏处理，保留省市信息，详细地址用星号替代。

    Args:
        address (str): 待脱敏的地址。

    Returns:
        str: 脱敏后的地址，如 四川省 · 成都市 · ***。
    """
    address = address.strip()
    if not address:
        return address
    parts = address.split('·')
    if len(parts) >= 3:
        parts = parts[:2] + ['***']
        return ' · '.join(p.strip() for p in parts)
    return address[:3] + '***' if len(address) > 3 else '***'


def is_workday_realtime() -> bool:
    """
    实时判断今天是否为法定工作日。

    通过调用第三方节假日 API（https://timor.tech/api/holiday）获取当前日期的节假日信息，
    并根据返回结果判断是否为法定工作日。若调用失败或解析异常，则降级使用 weekday 判断。

    返回值:
        bool: True 表示是法定工作日，False 表示是非工作日（周末或节假日）
    """

    # check_date = datetime.today()
    check_date = datetime.now(CST)
    date_str = check_date.strftime("%Y-%m-%d")
    url = f"https://timor.tech/api/holiday/info/{date_str}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # 默认降级结果：weekday < 5 为工作日
    fallback_is_workday = check_date.weekday() < 5

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            logging.warning(f"API 非 200 状态码: {resp.status_code}, 内容: {resp.text[:200]}")
            return fallback_is_workday

        data = resp.json()
        logging.debug(f"API 返回数据: {data}")

        # Timor API：code == 0 表示请求成功
        if data.get("code") != 0:
            logging.warning(f"API 业务码异常: {data}")
            return fallback_is_workday

        # 解析 type.type 字段以判断日期类型：
        # 0 - 工作日；1 - 周末；2 - 节假日；3 - 调休日（视为工作日）
        day_type = data.get("type", {}).get("type")
        if day_type is None:
            logging.warning(f"返回数据缺少 type.type 字段: {data}")
            return fallback_is_workday

        is_workday = day_type in (0, 3)
        logging.info(f"{date_str} 是否为法定工作日: {is_workday}")

        return is_workday

    except Exception as e:
        logging.error(f"API 调用异常: {e}")
        return fallback_is_workday


def get_checkin_type() -> dict[str, str]:
    """
    获取打卡类型（单次模式）。

    该方法根据配置文件获取打卡类型，并返回一个字典，包含打卡类型和显示名称。
    适用于 single 模式（只打一次卡）。

    Returns:
        dict[str, str]: 包含打卡类型和显示名称的字典。
    """
    type = ConfigManager.get("clockIn", "type")
    if type == "START":
        return {"type": "START", "display": "上班"}
    elif type == "END":
        return {"type": "END", "display": "下班"}
    else:
        return {"type": "HOLIDAY", "display": "休息/节假日"}


def get_checkin_types() -> list[dict[str, str]]:
    """
    根据打卡模式获取打卡类型列表。

    支持的模式：
    - twice_daily: 一天两次打卡（上班 + 下班）
    - single: 单次打卡，根据 clockIn.type 决定类型
    - 其他/未配置: 默认休息/节假日打卡

    Returns:
        list[dict[str, str]]: 打卡类型列表，每个元素包含 type 和 display。
    """
    mode = ConfigManager.get("clockIn", "mode", default="single")
    if mode == "twice_daily":
        return [
            {"type": "START", "display": "上班"},
            {"type": "END", "display": "下班"},
        ]
    else:
        return [get_checkin_type()]