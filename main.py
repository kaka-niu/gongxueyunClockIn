import logging
import os
import sys
from datetime import datetime
from manager.ConfigManager import ConfigManager
from step.clockIn import clock_in
from step.fetchPlan import fetch_plan
from step.login import login
from manager.UserInfoManager import UserInfoManager
from step.sendEmail import send_email
from util.ApiService import ApiService

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


def execute_tasks():
    # 登录
    isLogin = login()
    if not isLogin:
        logging.warning("登录失败")
        return
    logging.info(f"用户数据：{UserInfoManager.load()}")
    logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
    if UserInfoManager.get("userType") != "student":
        sys.exit("当前用户不是学生，结束执行打卡任务")
    # 获取打卡信息
    hasPlan = fetch_plan()
    if not hasPlan:
        logging.warning("未获取到打卡信息")
        return
    # 执行打卡
    str = clock_in()
    logging.info(str)
    # 发送邮件通知
    if ConfigManager.get("smtp", "enable"):
        send_email(str["title"], str["content"])


def test_clock_in():
    """
    测试模式：只打卡一次，根据当前时间判断上班卡还是下班卡
    """
    # 手动测试模式启用快照保存
    os.environ['SAVE_CAPTCHA_SNAPSHOTS'] = '1'
    
    current_time = datetime.now()
    hour = current_time.hour
    
    # 判断打卡类型
    if hour < 12:
        clock_type = "上班"
    else:
        clock_type = "下班"
    logging.info(f"当前时间 {current_time.strftime('%H:%M')}，执行{clock_type}卡测试")
    
    # 登录
    isLogin = login()
    if not isLogin:
        logging.warning("登录失败")
        return
    logging.info(f"用户数据：{UserInfoManager.load()}")
    logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
    if UserInfoManager.get("userType") != "student":
        sys.exit("当前用户不是学生，结束执行打卡任务")
    
    # 获取打卡信息
    hasPlan = fetch_plan()
    if not hasPlan:
        logging.warning("未获取到打卡信息")
        return
    
    # 打卡前判断
    api_client = ApiService()
    if clock_type == "上班":
        if api_client.has_morning_clock_in_today():
            logging.info("今日上班卡已打卡，无需重复打卡")
            return {"title": "skip", "content": "今日上班卡已打卡"}
    else:
        # 下班卡：先判断上班卡有没有打
        if not api_client.has_morning_clock_in_today():
            logging.warning("今日上班卡尚未打卡，先执行上班卡")
            morning_result = clock_in(force_type="START")
            logging.info(f"上班卡补打结果：{morning_result}")
            if morning_result.get("title") != "success":
                logging.error("上班卡补打失败，跳过下班卡")
                if ConfigManager.get("smtp", "enable"):
                    send_email(morning_result["title"], f"上班卡补打失败: {morning_result['content']}")
                return morning_result
        else:
            logging.info("今日上班卡已打卡")
        # 再判断下班卡有没有打
        if api_client.has_evening_clock_in_today():
            logging.info("今日下班卡已打卡，无需重复打卡")
            return {"title": "skip", "content": "今日下班卡已打卡"}
    
    # 执行打卡
    result = clock_in()
    logging.info(f"{clock_type}卡测试结果：{result}")
    
    # 发送邮件通知
    if ConfigManager.get("smtp", "enable"):
        send_email(result["title"], result["content"])
    
    return result

if __name__ == '__main__':
    # 测试模式：只打卡一次
    test_clock_in()