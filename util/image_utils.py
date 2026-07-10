# util/image_utils.py
import cv2
import numpy as np
from PIL import Image, ImageGrab
import os
import logging
from datetime import datetime
from util.ocr import ocr_predict

def save_snapshot(filepath):
    """
    保存当前屏幕截图到指定路径
    :param filepath: 截图保存路径
    """
    # 使用 OpenCV 捕获屏幕（此处为模拟，实际需调用系统 API）
    # 示例：使用 PIL 模拟截图
    try:
        screenshot = ImageGrab.grab()
        screenshot.save(filepath)
        logging.info(f"截图已保存至: {filepath}")
    except Exception as e:
        logging.error(f"截图失败: {e}")
        raise


def get_text_coordinates(image):
    """
    使用 OCR 识别图片中的文字及其位置
    :param image: 图像数据（numpy.ndarray）或文件路径（str）
    :return: [(text, (x, y, w, h)), ...]
    """
    try:
        # 支持接收 numpy 数组或文件路径
        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = image
            
        if img is None or img.size == 0:
            logging.error("图片加载失败或为空")
            return []

        # 转换为灰度图并二值化
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 使用轮廓检测找到文字区域
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        text_coords = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 10 and h > 10:  # 过滤小区域
                roi = img[y:y+h, x:x+w]
                # 使用 OCR 识别文字（简化版）
                text = ocr_predict(roi)  # 假设 ocr_predict 已定义
                if text:
                    text_coords.append((text, (x, y, w, h)))

        return text_coords
    except Exception as e:
        logging.error(f"文字识别失败: {e}")
        return []