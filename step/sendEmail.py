import smtplib
import logging
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

from manager.ConfigManager import ConfigManager

logger = logging.getLogger(__name__)

def send_email(title, content):
    to_emails = ConfigManager.get("smtp", "to")
    
    for to_email in to_emails:
        try:
            # 设置 MIMEText 对象
            message = MIMEText(content, 'plain', 'utf-8')
            message['Subject'] = Header(title, 'utf-8')
            from_header = Header(ConfigManager.get("smtp", "from"), 'utf-8')
            message['From'] = formataddr((from_header.encode(), ConfigManager.get("smtp", "username")))
            message['To'] = to_email

            # 连接到 SMTP 服务器，添加超时设置
            with smtplib.SMTP_SSL(
                ConfigManager.get("smtp", "host"), 
                ConfigManager.get("smtp", "port"),
                timeout=30  # 添加超时设置
            ) as server:
                # 登录到邮箱账户
                server.login(ConfigManager.get("smtp", "username"), ConfigManager.get("smtp", "password"))
                # 发送邮件
                server.sendmail(ConfigManager.get("smtp", "username"), to_email, message.as_string())
                logger.info(f"邮件已成功发送到 {to_email}")
        except smtplib.SMTPResponseException as e:
            logger.error(f"邮件成功发送了 SMTP响应异常：{e}")
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP服务器断开连接：{e}")
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP连接错误：{e}")
        except Exception as e:
            logger.error(f"发送邮件失败：{e}")