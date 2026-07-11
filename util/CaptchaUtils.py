import base64
import json
import logging
import os
import random
import struct
# from datetime import datetime
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

from cv2.typing import MatLike
import numpy as np
import onnxruntime as ort
import cv2

logger = logging.getLogger(__name__)

# 中国标准时间 (UTC+8)
CST = timezone(timedelta(hours=8))


def calculate_precise_slider_distance(target_start_x: int, target_end_x: int,
                                      slider_width: int) -> float:
    """
    计算滑块需要移动的精确距离，并添加微小随机偏移。

    Args:
        target_start_x (int): 目标区域的起始x坐标。
        target_end_x (int): 目标区域的结束x坐标。
        slider_width (int): 滑块的宽度。

    Returns:
        float: 精确到小数点后1位的滑动距离，包含微小随机偏移。
    """
    try:
        # 计算目标区域的中心点x坐标
        target_center_x = (target_start_x + target_end_x) / 2

        # 计算滑块初始位置的中心点x坐标
        slider_initial_center_x = slider_width / 2

        # 计算滑块需要移动的精确距离
        precise_distance = target_center_x - slider_initial_center_x

        # 添加一个随机的微小偏移，模拟真实用户滑动
        random_offset = random.uniform(-0.1, 0.1)

        # 将最终距离四舍五入到小数点后1位
        final_distance = round(precise_distance + random_offset, 1)

        logger.info(f"计算滑块距离成功: {final_distance}")
        return final_distance

    except Exception as e:
        logger.error(f"计算滑块距离时发生错误: {e}")
        raise


def extract_png_width(png_binary: bytes) -> int:
    """
    从PNG二进制数据中提取图像宽度。

    Args:
        png_binary (bytes): PNG图像的二进制数据。

    Returns:
        int: PNG图像的宽度（以像素为单位）。

    Raises:
        ValueError: 如果输入数据不是有效的PNG图像。
    """
    try:
        # 检查PNG文件头是否合法（固定8字节的PNG签名）
        if png_binary[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("无效的PNG签名：不是有效的PNG图像")

        # 从PNG数据的固定位置提取宽度信息
        width = struct.unpack(">I", png_binary[16:20])[0]
        logger.info(f"提取PNG宽度成功: {width}")
        return width

    except struct.error as e:
        logger.error(f"无法从PNG数据中提取宽度信息: {e}")
        raise ValueError("无法从PNG数据中提取宽度信息") from e

    except Exception as e:
        logger.error(f"提取PNG宽度时发生错误: {e}")
        raise


def slide_match(target_bytes: bytes, background_bytes: bytes) -> list:
    """
    获取验证区域坐标，使用目标检测算法。

    Args:
        target_bytes (bytes): 滑块图片二进制数据，默认为 None。
        background_bytes (bytes): 背景图片二进制数据，默认为 None。

    Returns:
        list: 目标区域左边界坐标，右边界坐标。
    """
    try:
        # 解码滑块和背景图像为OpenCV格式
        target = cv2.imdecode(np.frombuffer(target_bytes, np.uint8),
                              cv2.IMREAD_ANYCOLOR)
        background = cv2.imdecode(np.frombuffer(background_bytes, np.uint8),
                                  cv2.IMREAD_ANYCOLOR)

        # 应用Canny边缘检测，将图像转换为二值图像
        background = cv2.Canny(background, 100, 200)
        target = cv2.Canny(target, 100, 200)

        # 将二值图像转换为RGB格式，便于后续处理
        background = cv2.cvtColor(background, cv2.COLOR_GRAY2RGB)
        target = cv2.cvtColor(target, cv2.COLOR_GRAY2RGB)

        # 使用模板匹配算法找到滑块在背景中的最佳匹配位置
        res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)  # 获取最大相似度及其对应位置

        # 获取滑块的高度和宽度
        h, w = target.shape[:2]

        # 计算目标区域的右下角坐标
        bottom_right = (max_loc[0] + w, max_loc[1] + h)

        logger.info(f"滑块匹配成功，最大相似度: {max_val}")
        return [int(max_loc[0]), int(bottom_right[0])]

    except Exception as e:
        logger.error(f"滑块匹配时发生错误: {e}")
        raise


def recognize_blockPuzzle_captcha(target: str, background: str) -> str:
    """
    识别图像验证码。

    Args:
        target (str): 目标图像的二进制数据的base64编码。
        background (str): 背景图像的二进制数据的base64编码。

    Returns:
        str: 滑块需要滑动的距离。
    """
    try:
        # 将base64编码的字符串解码为二进制数据
        target_bytes = base64.b64decode(target)
        background_bytes = base64.b64decode(background)

        # 调用滑块匹配算法获取目标区域的坐标
        res = slide_match(target_bytes=target_bytes,
                          background_bytes=background_bytes)

        # 从滑块图像提取宽度信息
        target_width = extract_png_width(target_bytes)

        # 计算滑块需要移动的距离
        slider_distance = calculate_precise_slider_distance(
            res[0], res[1], target_width)

        # 构造返回的数据，格式为JSON
        slider_data = {
            "x": slider_distance,
            "y": 5,
        }  # 固定y值为5
        logger.info(f"验证码识别成功: {slider_data}")
        return json.dumps(slider_data, separators=(",", ":"))

    except Exception as e:
        logger.error(f"验证码识别时发生错误: {e}")
        raise


def detect_objects(model_path: str,
                   image_data: MatLike,
                   use_gpu: bool = False) -> list[list[int]]:
    """
    使用ONNX模型进行目标检测。
    :param model_path: ONNX模型路径。
    :param image_data: 待检测图片的二进制数据。
    :param use_gpu: 是否使用GPU进行推理。
    :return: 检测到的目标边界框坐标列表，格式为 [[x1, y1, x2, y2], ...]。
    :raises: RuntimeError, ValueError
    """
    try:
        # 调整图像大小并填充到640x640
        scale = min(640 / image_data.shape[1], 640 / image_data.shape[0])
        img_resized = cv2.resize(
            image_data,
            (int(image_data.shape[1] * scale), int(
                image_data.shape[0] * scale)),
        )
        new_image = np.full((640, 640, 3), 128, dtype=np.uint8)
        dh, dw = (640 - img_resized.shape[0]) // 2, (640 -
                                                     img_resized.shape[1]) // 2
        new_image[dh:dh + img_resized.shape[0],
                  dw:dw + img_resized.shape[1]] = (img_resized)

        # 将图片转换成模型需要的输入格式
        input_img = (np.expand_dims(new_image.transpose(
            (2, 0, 1)), axis=0).astype(np.float32) / 255.0)

        # 加载模型并运行
        providers = ["CUDAExecutionProvider"
                     ] if use_gpu else ["CPUExecutionProvider"]
        session = ort.InferenceSession(model_path, providers=providers)
        result = session.run(None, {session.get_inputs()[0].name: input_img})

        # 解析模型输出并应用非极大值抑制（NMS）
        detections = result[0][0]
        boxes = [[
            x_center - width / 2,
            y_center - height / 2,
            x_center + width / 2,
            y_center + height / 2,
        ] for x_center, y_center, width, height, confidence, *class_scores in
                 detections if confidence >= 0.5]
        scores = [
            max(class_scores)
            for _, _, _, _, confidence, *class_scores in detections
            if confidence >= 0.5
        ]

        if boxes:
            indices = cv2.dnn.NMSBoxes(boxes, scores, 0.5, 0.5)
            boxes = [boxes[i] for i in indices]

        # 将边界框坐标还原到原始图像的尺寸，并裁剪到图片边界内，过滤无效框
        img_h, img_w = image_data.shape[:2]
        valid_boxes = []
        for x1, y1, x2, y2 in boxes:
            nx1 = max(0, int((x1 - dw) / scale))
            ny1 = max(0, int((y1 - dh) / scale))
            nx2 = min(img_w, int((x2 - dw) / scale))
            ny2 = min(img_h, int((y2 - dh) / scale))
            if nx2 > nx1 and ny2 > ny1:
                valid_boxes.append([nx1, ny1, nx2, ny2])
        return valid_boxes

    except Exception as e:
        raise ValueError(f"目标检测失败: {e}")


def predict_ocr(model_path: str,
                image: np.ndarray,
                use_gpu: bool = False) -> str:
    """
    使用ONNX模型进行OCR预测。
    :param model_path: ONNX模型路径。
    :param image: 待检测的图片（OpenCV格式，numpy.ndarray）。
    :param use_gpu: 是否使用GPU进行推理。
    :return: 预测的字符。
    :raises: Exception 如果模型加载或推理过程中发生错误。
    """
    try:
        # 加载ONNX模型
        session = ort.InferenceSession(
            model_path,
            providers=(["CUDAExecutionProvider"]
                       if use_gpu else ["CPUExecutionProvider"]),
        )

        # 检查图片是否为空或无效
        if image is None or image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
            raise ValueError("输入图片为空或尺寸无效")

        # 预处理图片
        image = np.expand_dims(
            cv2.cvtColor(cv2.resize(image,
                                    (64, 64)), cv2.COLOR_BGR2RGB).transpose(
                                        (2, 0, 1)).astype(np.float32) / 255.0,
            axis=0,
        )

        # 字符集
        charset = [
            "士",
            "候",
            "之",
            "科",
            "孩",
            "雪",
            "万",
            "章",
            "导",
            "治",
            "亲",
            "社",
            "所",
            "似",
            "验",
            "习",
            "吃",
            "历",
            "写",
            "业",
            "为",
            "睛",
            "睡",
            "将",
            "林",
            "法",
            "你",
            "观",
            "信",
            "掉",
            "觉",
            "站",
            "确",
            "老",
            "方",
            "道",
            "海",
            "性",
            "好",
            "感",
            "女",
            "术",
            "如",
            "重",
            "细",
            "青",
            "流",
            "心",
            "包",
            "越",
            "且",
            "风",
            "哥",
            "菜",
            "劳",
            "必",
            "阶",
            "代",
            "令",
            "志",
            "国",
            "们",
            "记",
            "知",
            "谁",
            "讲",
            "眼",
            "提",
            "由",
            "民",
            "怎",
            "度",
            "村",
            "没",
            "呀",
            "许",
            "以",
            "四",
            "政",
            "点",
            "离",
            "说",
            "带",
            "关",
            "答",
            "出",
            "放",
            "告",
            "夜",
            "识",
            "兴",
            "做",
            "难",
            "八",
            "叶",
            "月",
            "马",
            "办",
            "行",
            "三",
            "最",
            "小",
            "亮",
            "作",
            "晚",
            "义",
            "活",
            "公",
            "旁",
            "色",
            "看",
            "从",
            "话",
            "系",
            "高",
            "水",
            "您",
            "到",
            "装",
            "中",
            "研",
            "雨",
            "住",
            "因",
            "少",
            "原",
            "什",
            "片",
            "准",
            "脚",
            "张",
            "深",
            "力",
            "让",
            "顶",
            "石",
            "山",
            "类",
            "野",
            "阵",
            "赶",
            "见",
            "七",
            "立",
            "整",
            "屋",
            "再",
            "读",
            "相",
            "弟",
            "两",
            "接",
            "种",
            "车",
            "近",
            "外",
            "几",
            "停",
            "认",
            "特",
            "战",
            "化",
            "子",
            "定",
            "边",
            "多",
            "产",
            "形",
            "她",
            "衣",
            "共",
            "音",
            "分",
            "级",
            "别",
            "千",
            "连",
            "理",
            "往",
            "先",
            "队",
            "围",
            "满",
            "在",
            "领",
            "画",
            "他",
            "反",
            "花",
            "农",
            "被",
            "名",
            "这",
            "席",
            "众",
            "很",
            "渐",
            "乡",
            "极",
            "实",
            "城",
            "取",
            "题",
            "儿",
            "响",
            "那",
            "主",
            "进",
            "去",
            "思",
            "找",
            "总",
            "应",
            "船",
            "身",
            "牛",
            "歌",
            "团",
            "爬",
            "岁",
            "着",
            "冲",
            "早",
            "利",
            "受",
            "忽",
            "苦",
            "也",
            "表",
            "通",
            "有",
            "像",
            "现",
            "对",
            "头",
            "开",
            "般",
            "呼",
            "又",
            "的",
            "把",
            "帮",
            "收",
            "军",
            "怕",
            "饭",
            "或",
            "就",
            "年",
            "背",
            "来",
            "革",
            "压",
            "斗",
            "位",
            "房",
            "飞",
            "都",
            "块",
            "跳",
            "变",
            "今",
            "命",
            "区",
            "爱",
            "门",
            "入",
            "九",
            "动",
            "根",
            "南",
            "造",
            "其",
            "者",
            "便",
            "每",
            "事",
            "座",
            "算",
            "然",
            "笑",
            "阳",
            "半",
            "大",
            "是",
            "会",
            "一",
            "非",
            "树",
            "旧",
            "里",
            "至",
            "无",
            "问",
            "发",
            "河",
            "物",
            "东",
            "叔",
            "它",
            "百",
            "拿",
            "叫",
            "明",
            "刚",
            "脸",
            "干",
            "样",
            "呢",
            "更",
            "底",
            "忙",
            "我",
            "结",
            "地",
            "界",
            "草",
            "论",
            "还",
            "轻",
            "数",
            "世",
            "只",
            "用",
            "长",
            "个",
            "光",
            "此",
            "沙",
            "面",
            "白",
            "转",
            "哪",
            "想",
            "件",
            "文",
            "未",
            "啦",
            "口",
            "十",
            "人",
            "各",
            "并",
            "敌",
            "打",
            "古",
            "合",
            "完",
            "啊",
            "线",
            "回",
            "嘴",
            "究",
            "岸",
            "听",
            "内",
            "土",
            "跑",
            "日",
            "平",
            "咱",
            "快",
            "坚",
            "真",
            "够",
            "工",
            "些",
            "已",
            "争",
            "得",
            "望",
            "伟",
            "却",
            "处",
            "但",
            "过",
            "唱",
            "时",
            "热",
            "走",
            "书",
            "不",
            "起",
            "神",
            "使",
            "本",
            "自",
            "倒",
            "比",
            "前",
            "新",
            "直",
            "经",
            "解",
            "步",
            "胜",
            "次",
            "该",
            "六",
            "后",
            "报",
            "体",
            "家",
            "急",
            "际",
            "五",
            "北",
            "等",
            "员",
            "何",
            "火",
            "吗",
            "机",
            "当",
            "么",
            "天",
            "枪",
            "量",
            "意",
            "同",
            "决",
            "钱",
            "情",
            "手",
            "强",
            "全",
            "了",
            "可",
            "果",
            "气",
            "加",
            "学",
            "息",
            "黑",
            "刻",
            "而",
            "慢",
            "紧",
            "照",
            "指",
            "改",
            "上",
            "运",
            "声",
            "二",
            "吧",
            "己",
            "字",
            "才",
            "教",
            "于",
            "向",
            "要",
            "建",
            "展",
            "句",
            "史",
            "给",
            "坐",
            "和",
            "第",
            "成",
            "落",
            "跟",
            "群",
            "星",
            "生",
            "部",
            "送",
            "服",
            "穿",
            "友",
            "下",
            "拉",
            "任",
            "太",
            "常",
            "场",
            "敢",
            "清",
            "路",
            "破",
            "传",
            "空",
            "师",
            "切",
            "条",
        ]

        # 运行模型推理并处理输出
        return "".join(charset[item] for item in session.run(
            None, {session.get_inputs()[0].name: image})[1])

    except Exception as e:
        raise Exception(f"OCR预测失败: {e}")


def save_click_word_snapshot(image: np.ndarray, bboxes: list, click_points: list,
                             wordlist: list, recognized_dict: dict,
                             stage: str = "predict") -> str:
    """
    保存文字点选验证码的快照，在原图上绘制检测框和点击坐标。

    Args:
        image: 原始图片（OpenCV 格式）。
        bboxes: 所有检测到的边界框列表 [[x1, y1, x2, y2], ...]。
        click_points: 点击坐标列表 [{"x": x, "y": y}, ...]。
        wordlist: 需要点击的文字列表。
        recognized_dict: 识别结果字典 {文字: [x1, y1, x2, y2]}。
        stage: 快照阶段标识（"predict" 或 "verify"）。

    Returns:
        str: 保存的快照文件路径。
    """
    snapshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "snapshots")
    os.makedirs(snapshot_dir, exist_ok=True)

    # OpenCV 转 PIL 以支持中文
    img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    # 尝试加载系统字体，失败则用默认
    font_path = None
    for fp in [
        "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
        "/System/Library/Fonts/PingFang.ttc",  # macOS
    ]:
        if os.path.exists(fp):
            font_path = fp
            break

    try:
        font_label = ImageFont.truetype(font_path, 16) if font_path else ImageFont.load_default()
        font_click = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
    except Exception:
        font_label = ImageFont.load_default()
        font_click = ImageFont.load_default()

    # 绘制绿色检测框 + 文字标签
    for word, bbox in recognized_dict.items():
        x1, y1, x2, y2 = bbox
        draw.rectangle([x1, y1, x2, y2], outline=(0, 255, 0), width=2)
        draw.text((x1, y1 - 18), word, fill=(0, 255, 0), font=font_label)

    # 绘制红色点击点 + 编号文字
    for i, pt in enumerate(click_points):
        x, y = pt["x"], pt["y"]
        r = 6
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 0, 0))
        label = f"{i + 1}.{wordlist[i] if i < len(wordlist) else '?'}"
        draw.text((x + 10, y - 14), label, fill=(255, 0, 0), font=font_click)

    # PIL 转回 OpenCV 格式保存
    annotated = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    timestamp = datetime.now(CST).strftime("%Y%m%d_%H%M%S_%f")
    filename = os.path.join(snapshot_dir,
                            f"click_word_{stage}_{timestamp}.png")
    cv2.imwrite(filename, annotated)
    logger.info(f"文字点选快照已保存: {filename}")
    return filename


def recognize_clickWord_captcha(target: str, wordlist: list) -> str:
    """
    从给定的图像中识别点击文字验证码，并返回单词的坐标。

    此函数初始化ddddocr检测器和识别器，以检测和识别验证码中的单词。然后，它使用识别到的单词为给定单词列表中的单词生成随机坐标。

    Args:
        target (str): base64编码的图像字符串。
        wordlist (list): 要识别的单词列表。

    Returns:
        str: 单词列表中的单词的坐标的JSON字符串列表。

    引发：
        logger.warning: 在处理文本框时出错或未找到字符时。
    """
    target_bytes = base64.b64decode(target)

    # 将图片转换为 OpenCV 格式
    image = cv2.imdecode(np.frombuffer(target_bytes, dtype=np.uint8),
                         cv2.IMREAD_COLOR)

    bboxes = detect_objects("./models/yolov5n.onnx", image)

    # 识别每个文本框中的文本，并存储为字典以便快速查找
    recognized_dict = {}
    for bbox in bboxes:
        try:
            x_min, y_min, x_max, y_max = bbox
            text = predict_ocr("./models/ocr.onnx", image[y_min:y_max,
                                                          x_min:x_max])
            recognized_dict[text] = bbox
            logger.info(f"OCR识别: [{text}] @ ({x_min},{y_min})-({x_max},{y_max})")
        except Exception as e:
            logger.warning(f"处理文本框时出错: {e}")

    logger.info(f"需要点击: {wordlist}")
    logger.info(f"识别结果: {list(recognized_dict.keys())}")

    # 根据wordlist的顺序找到对应的文本框，并生成随机坐标
    random_coordinates = []
    for word in wordlist:
        bbox = recognized_dict.get(word)
        if bbox:
            # 生成随机坐标
            x = random.randint(bbox[0], bbox[2])
            y = random.randint(bbox[1], bbox[3])
            random_coordinates.append({"x": x, "y": y})
        else:
            logger.warning(f"未找到字符: {word}")

    # 保存快照（检测框 + 点击坐标）
    save_click_word_snapshot(image, bboxes, random_coordinates, wordlist,
                             recognized_dict, stage="predict")

    return json.dumps(random_coordinates, separators=(",", ":"))