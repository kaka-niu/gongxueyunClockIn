#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工学云自动签到脚本
支持多用户配置，可在GitHub Actions上运行
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
# 在文件顶部的导入部分添加
import yaml
# 导入现有模块
from manager.ConfigManager import ConfigManager, CONFIG_PATH as ORIGINAL_CONFIG_PATH
from manager.UserInfoManager import UserInfoManager, USER_INFO_PATH as ORIGINAL_USER_INFO_PATH
from manager.PlanInfoManager import PlanInfoManager, PLAN_INFO_PATH as ORIGINAL_PLAN_INFO_PATH
from step.clockIn import clock_in
from step.fetchPlan import fetch_plan
from step.login import login
from step.sendEmail import send_email
from util.ApiService import ApiService
from util.HelperFunctions import get_checkin_type

# ======================
# 日志配置
# ======================
def setup_logging():
    """设置日志配置"""
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),  # 写入日志文件
            logging.StreamHandler(sys.stdout)  # 控制台输出
        ]
    )

def load_users_config():
    """从环境变量或配置文件加载用户配置
    GitHub Actions模式下（USERS环境变量存在），只从环境变量加载，不读取本地配置文件。
    本地模式下，依次尝试从 config.json 和 auto.yaml 加载。
    """
    users_json = os.environ.get('USERS', None)

    if users_json:
        try:
            users = json.loads(users_json)
            # 兼容单用户对象格式：如果是dict则自动包装为列表
            if isinstance(users, dict):
                users = [users]
            logging.info(f"从环境变量加载了 {len(users)} 个用户配置")
            return users
        except json.JSONDecodeError as e:
            logging.error(f"解析环境变量中的用户配置失败: {e}")
            return None

    logging.info("未检测到USERS环境变量，切换到本地模式，尝试从配置文件加载...")

    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                users = [config]
                logging.info(f"从 config.json 加载了 {len(users)} 个用户配置")
                return users
        except Exception as e:
            logging.error(f"从 config.json 加载用户配置失败: {e}")
            return None

    yaml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto.yaml")
    if os.path.exists(yaml_file):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                users = config.get('users', [])
                logging.info(f"从 auto.yaml 加载了 {len(users)} 个用户配置")
                return users
        except Exception as e:
            logging.error(f"从 auto.yaml 加载用户配置失败: {e}")
            return None

    logging.error("未找到用户配置")
    return None

def setup_user_config(user_config):
    """为单个用户设置配置"""
    # 创建临时目录存储用户配置
    temp_dir = tempfile.mkdtemp()
    
    # 设置配置文件路径
    config_path = os.path.join(temp_dir, "config.json")
    user_dir = os.path.join(temp_dir, "user")
    os.makedirs(user_dir, exist_ok=True)
    
    # 写入配置文件
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(user_config, f, ensure_ascii=False, indent=4)
    
    # 保存原始路径
    original_config_path = ORIGINAL_CONFIG_PATH
    original_user_info_path = ORIGINAL_USER_INFO_PATH
    original_plan_info_path = ORIGINAL_PLAN_INFO_PATH
    
    # 导入模块并修改路径常量
    import manager.ConfigManager as cm
    import manager.UserInfoManager as uim
    import manager.PlanInfoManager as pim
    
    # 更新路径常量
    cm.CONFIG_PATH = Path(config_path)
    uim.USER_INFO_PATH = Path(user_dir) / "userInfo.json"
    pim.PLAN_INFO_PATH = Path(user_dir) / "planInfo.json"
    
    # 清除缓存
    ConfigManager._config_cache = None
    UserInfoManager._userInfo_cache = None
    PlanInfoManager._planinfo_cache = None
    
    # 返回临时目录和原始路径，以便后续恢复
    return temp_dir, original_config_path, original_user_info_path, original_plan_info_path

def execute_clock_in(user_config, clock_type=None):
    """为单个用户执行打卡操作"""
    phone = user_config.get("config", {}).get("user", {}).get("phone", "未知用户")
    logging.info(f"开始为用户 {phone} 执行打卡任务")
    
    # 设置用户配置
    temp_dir, original_config_path, original_user_info_path, original_plan_info_path = setup_user_config(user_config)
    
    try:
        # 判断打卡类型
        if clock_type is None:
            current_time = datetime.now()
            hour = current_time.hour
            clock_type = "上班" if hour < 12 else "下班"
        
        logging.info(f"执行{clock_type}卡打卡")
        
        # 登录
        is_login = login()
        if not is_login:
            logging.warning(f"用户 {phone} 登录失败")
            return False
        
        logging.info(f"用户 {phone} 登录成功")
        
        # 获取打卡信息
        has_plan = fetch_plan()
        if not has_plan:
            logging.warning(f"用户 {phone} 未获取到打卡信息")
            return False
        
        # 打卡前判断
        api_client = ApiService()
        if clock_type == "上班":
            if api_client.has_morning_clock_in_today():
                logging.info(f"用户 {phone} 今日上班卡已打卡，无需重复打卡")
                return True
        else:
            # 下班卡：先判断上班卡
            if not api_client.has_morning_clock_in_today():
                logging.warning(f"用户 {phone} 今日上班卡尚未打卡，先执行上班卡")
                morning_result = clock_in(force_type="START")
                logging.info(f"用户 {phone} 上班卡补打结果：{morning_result}")
                if morning_result.get("title") != "success":
                    logging.error(f"用户 {phone} 上班卡补打失败，跳过下班卡")
                    if user_config.get("config", {}).get("smtp", {}).get("enable", False):
                        send_email("工学云签到 - 上班卡补打失败", morning_result["content"])
                    return False
            else:
                logging.info(f"用户 {phone} 今日上班卡已打卡")
            # 再判断下班卡
            if api_client.has_evening_clock_in_today():
                logging.info(f"用户 {phone} 今日下班卡已打卡，无需重复打卡")
                return True
        
        # 执行打卡
        if clock_type == "上班":
            result = clock_in(force_type="START")
        elif clock_type == "下班":
            result = clock_in(force_type="END")
        else:
            result = clock_in()
        logging.info(f"用户 {phone} 打卡结果: {result}")
        
        # 发送邮件通知
        if user_config.get("config", {}).get("smtp", {}).get("enable", False):
            email_title = "工学云签到 - 打卡成功" if result["title"] == "success" else "工学云签到 - 打卡失败"
            send_email(email_title, result["content"])
        
        return True
    
    except Exception as e:
        logging.error(f"用户 {phone} 打卡过程中发生异常: {e}")
        return False
    
    finally:
        # 恢复原始路径
        import manager.ConfigManager as cm
        import manager.UserInfoManager as uim
        import manager.PlanInfoManager as pim
        
        cm.CONFIG_PATH = original_config_path
        uim.USER_INFO_PATH = original_user_info_path
        pim.PLAN_INFO_PATH = original_plan_info_path
        
        # 清除缓存
        ConfigManager._config_cache = None
        UserInfoManager._userInfo_cache = None
        PlanInfoManager._planinfo_cache = None
        
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    """主函数"""
    setup_logging()
    
    # 获取执行模式
    mode = os.environ.get('MODE', 'manual')  # 默认为手动模式
    
    # 加载用户配置
    users = load_users_config()
    if not users:
        logging.error("未找到用户配置，程序退出")
        sys.exit(1)
    
    # 判断打卡类型
    clock_type = None
    if mode == 'morning':
        clock_type = "上班"
    elif mode == 'evening':
        clock_type = "下班"
    
    # 执行打卡
    success_count = 0
    total_count = len(users)
    
    for user_config in users:
        if execute_clock_in(user_config, clock_type):
            success_count += 1
    
    logging.info(f"打卡任务完成，成功: {success_count}/{total_count}")
    
    # 如果有用户打卡失败，返回非零退出码
    if success_count < total_count:
        sys.exit(1)

if __name__ == '__main__':
    main()