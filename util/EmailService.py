import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
# from datetime import datetime
from datetime import datetime, timezone, timedelta

from manager.ConfigManager import ConfigManager
from util.HelperFunctions import desensitize_phone, desensitize_address

logger = logging.getLogger(__name__)

# 中国标准时间 (UTC+8)
CST = timezone(timedelta(hours=8))


def send_email_notification(title: str, content: str) -> bool:
    """
    发送邮件通知。

    Args:
        title (str): 邮件标题。
        content (str): 邮件内容。

    Returns:
        bool: 发送成功返回 True，否则返回 False。
    """
    smtp_config = ConfigManager.get("smtp", default={})
    
    if not smtp_config.get("enable", False):
        logger.info("SMTP 未启用，跳过邮件发送")
        return False

    host = smtp_config.get("host")
    port = smtp_config.get("port", 465)
    username = smtp_config.get("username")
    password = smtp_config.get("password")
    from_name = smtp_config.get("from", "工学云打卡通知")
    to_list = smtp_config.get("to", [])

    if not host or not username or not password:
        logger.warning("SMTP 配置不完整，跳过邮件发送")
        return False

    if not to_list:
        logger.warning("未配置收件人邮箱，跳过邮件发送")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{from_name} <{username}>"
        msg["To"] = ", ".join(to_list)
        msg["Subject"] = Header(title, "utf-8")

        text_content = f"""
工学云打卡通知

{content}

发送时间：{datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")}
        """

        html_content = f"""
<html>
<body>
    <h2>工学云打卡通知</h2>
    <p>{content.replace(chr(10), "<br>")}</p>
    <p style="color: #999; font-size: 12px;">发送时间：{datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")}</p>
</body>
</html>
        """

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()

        server.login(username, password)
        server.sendmail(username, to_list, msg.as_string())
        server.quit()

        logger.info(f"邮件发送成功，收件人: {to_list}")
        return True

    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def send_clockin_notification(phone: str, location: str, checkin_type: str, success: bool, message: str = "") -> bool:
    """
    发送打卡通知邮件（手机号和地址已脱敏）。

    Args:
        phone (str): 手机号（将自动脱敏）。
        location (str): 打卡地点（将自动脱敏）。
        checkin_type (str): 打卡类型（上班/下班）。
        success (bool): 是否打卡成功。
        message (str): 附加消息。

    Returns:
        bool: 发送成功返回 True，否则返回 False。
    """
    desensitized_phone = desensitize_phone(phone)
    desensitized_location = desensitize_address(location)

    if success:
        title = "工学云签到成功通知"
        content = f"签到账号：{desensitized_phone}\n打卡类型：{checkin_type}\n签到地点：{desensitized_location}"
    else:
        title = "工学云签到失败通知"
        content = f"签到账号：{desensitized_phone}\n打卡类型：{checkin_type}\n失败原因：{message}"

    return send_email_notification(title, content)