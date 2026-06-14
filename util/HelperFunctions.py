import logging
import threading
from datetime import datetime, timedelta

import requests

from manager.ConfigManager import ConfigManager

# 尝试导入主模块的日志上下文，失败则创建本地版本
try:
    from main import _log_ctx
except ImportError:
    _log_ctx = threading.local()

logger = logging.getLogger(__name__)


def get_current_month_info() -> dict:
    """
    获取当前月份的开始和结束时间。

    该方法计算当前月份的开始日期和结束日期，并将它们返回为字典，
    字典中包含这两项的字符串表示。

    Returns:
        包含当前月份开始和结束时间的字典。
    """
    now = datetime.now()
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


def is_workday_realtime() -> bool:
    """
    实时判断今天是否为法定工作日。

    通过调用第三方节假日 API（https://timor.tech/api/holiday）获取当前日期的节假日信息，
    并根据返回结果判断是否为法定工作日。若调用失败或解析异常，则降级使用 weekday 判断。

    返回值:
        bool: True 表示是法定工作日，False 表示是非工作日（周末或节假日）
    """

    check_date = datetime.today()
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
    获取打卡类型。

    该方法根据配置文件获取打卡类型，并返回一个字典，包含打卡类型和显示名称。

    Returns:
        dict[str, str]: 包含打卡类型和显示名称的字典。
    """
    mode = ConfigManager.get("clockIn", "mode")
    # 1. 法定工作日模式
    if mode == "weekday":
        # 判断今天是否为工作日
        if is_workday_realtime():
            return {"type": "START", "display": "上班"}
        else:
            return {"type": "HOLIDAY", "display": "休息/节假日"}

    # 2. 每天执行
    if mode == "everyday":
        return {"type": "START", "display": "上班"}

    # 3. 自定义模式
    if mode == "customize":
        custom_days = ConfigManager.get("clockIn", "customDays", default=[])
        today = datetime.today().weekday() + 1  # 1=星期一, 7=星期天
        if today in custom_days:
            return {"type": "START", "display": "上班"}
        else:
            return {"type": "HOLIDAY", "display": "休息/节假日"}
    
    # 4. 一天打两次卡模式（新增）
    if mode == "twice_daily":
        current_time = datetime.now()
        hour = current_time.hour
        # 12点前打上班卡，12点后打下班卡
        if hour < 12:
            return {"type": "START", "display": "上班"}
        else:
            return {"type": "END", "display": "下班"}
    
    # 默认返回上班卡
    return {"type": "START", "display": "上班"}