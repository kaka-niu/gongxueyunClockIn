import cv2
import numpy as np
from PIL import Image
import os
import time
import logging
from util.image_utils import get_text_coordinates, save_snapshot
from util.ocr import ocr_predict
from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager
from manager.PlanInfoManager import PlanInfoManager
from util.ApiService import ApiService
from util.HelperFunctions import get_checkin_type

def mask_phone(phone: str) -> str:
    """手机号脱敏：保留前3位和后4位，中间用****替代"""
    if not phone or len(phone) < 7:
        return phone or "未知"
    return phone[:3] + "****" + phone[-4:]


def clock_in(force_type: str = None):
    """执行打卡操作

    Args:
        force_type: 强制指定打卡类型，如 'START' 或 'END'。为 None 时自动判断。

    Returns:
        dict: {
            "title": "success" / "fail",
            "content": 格式化后的推送内容,
            "phone": 脱敏手机号,
            "address": 签到地址,
            "clock_type": "上班卡" / "下班卡",
            "error_detail": 失败时的原始错误信息
        }
    """
    phone = ConfigManager.get("user", "phone") or "未知"
    address = ConfigManager.get("clockIn", "location", "address") or "未知"

    try:
        # 获取打卡类型
        if force_type:
            clock_type = force_type
            clock_type_display = "上班卡" if force_type == "START" else "下班卡"
        else:
            clock_type_info = get_checkin_type()
            clock_type = clock_type_info.get("type")
            clock_type_display = clock_type_info.get("display", "未知")
        logging.info(f"打卡类型: {clock_type}")

        # 创建 API 客户端
        api_client = ApiService()

        # 构建打卡信息
        checkin_info = {
            "type": clock_type,
            "lastDetailAddress": address,
            "description": None,
            "attachments": None
        }

        # 提交打卡
        result = api_client.submit_clock_in(checkin_info)

        if result and result.get("result"):
            content = (
                f"签到账号：{mask_phone(phone)}\n"
                f"签到地点：{address}\n"
                f"签到类型：{clock_type_display}\n"
                f"签到结果：成功"
            )
            return {
                "title": "success",
                "content": content,
                "phone": phone,
                "address": address,
                "clock_type": clock_type_display,
                "error_detail": None
            }
        else:
            error_detail = result.get("data", "打卡失败") if result else "打卡失败"
            content = (
                f"签到账号：{mask_phone(phone)}\n"
                f"签到地点：{address}\n"
                f"签到类型：{clock_type_display}\n"
                f"签到结果：失败\n"
                f"失败原因：{error_detail}"
            )
            return {
                "title": "fail",
                "content": content,
                "phone": phone,
                "address": address,
                "clock_type": clock_type_display,
                "error_detail": str(error_detail)
            }

    except Exception as e:
        logging.error(f"打卡失败: {e}")
        error_detail = str(e)
        content = (
            f"签到账号：{mask_phone(phone)}\n"
            f"签到地点：{address}\n"
            f"签到类型：未知\n"
            f"签到结果：失败\n"
            f"失败原因：{error_detail}"
        )
        return {
            "title": "fail",
            "content": content,
            "phone": phone,
            "address": address,
            "clock_type": "未知",
            "error_detail": error_detail
        }