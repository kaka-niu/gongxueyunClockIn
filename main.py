import logging
import sys
import os
import traceback

from manager.ConfigManager import ConfigManager
from step.clockIn import clock_in
from step.fetchPlan import fetch_plan
from step.login import login
from manager.UserInfoManager import UserInfoManager
from util.HelperFunctions import get_checkin_types

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
    try:
        logging.info("开始执行打卡任务")
        # 登录
        isLogin = login()
        if not isLogin:
            logging.warning("登录失败")
            input("按回车键退出...")  # 阻塞窗口，方便查看
            return

        logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
        if UserInfoManager.get("userType") != "student":
            logging.error("当前用户不是学生，结束执行打卡任务")
            input("按回车键退出...")
            return

        # 获取打卡信息
        hasPlan = fetch_plan()
        if not hasPlan:
            logging.warning("未获取到打卡信息")
            input("按回车键退出...")
            return

        # 根据模式执行打卡（支持 twice_daily 一天两次打卡）
        checkin_types = get_checkin_types()
        logging.info(f"打卡模式：{ConfigManager.get('clockIn', 'mode', default='single')}，共 {len(checkin_types)} 次打卡")
        for checkin in checkin_types:
            result = clock_in(force_type=checkin)
            logging.info(result)

        logging.info("打卡任务完成")
        input("按回车键退出...")

    except Exception as e:
        logging.error("执行打卡任务时发生异常")
        logging.error(traceback.format_exc())
        input("按回车键退出...")


if __name__ == '__main__':
    execute_tasks()