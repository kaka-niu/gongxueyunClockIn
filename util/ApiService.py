import os
import json
import logging
import random
import re
import time
import uuid
from typing import Dict, Any, List, Optional
import numpy as np
import requests

from manager.ConfigManager import ConfigManager
from manager.PlanInfoManager import PlanInfoManager
from manager.UserInfoManager import UserInfoManager
from util.CaptchaUtils import recognize_blockPuzzle_captcha, recognize_clickWord_captcha
from util.CryptoUtils import create_sign, aes_encrypt, aes_decrypt
from util.HelperFunctions import get_current_month_info
from util.image_utils import save_snapshot

logger = logging.getLogger(__name__)

# 常量
BASE_URL = "https://api.moguding.net:9000/"
HEADERS = {
    "user-agent": "Mozilla/5.0 (Linux; Android 16; 2510DRK44C Build/BP2A.250605.081) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.260 Mobile Safari/537.36",
    "content-type": "application/json; charset=utf-8",
    "accept-encoding": "gzip",
    "host": "api.moguding.net:9000",
    "Connection": "keep-alive",
    "Accept": "*/*",
}


class ApiService:
    def __init__(self):

        self.max_retries = 5  # 控制重新尝试的次数

    def _post_request(
            self,
            url: str,
            headers: Dict[str, str],
            data: Dict[str, Any],
            retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        发送POST请求，并处理请求过程中可能发生的错误。
        包括自动重试机制和Token失效处理。

        Args:
            url (str): 请求的API地址（不包括BASE_URL部分）。
            headers (Dict[str, str]): 请求头信息，包括授权信息。
            data (Dict[str, Any]): POST请求的数据。
            msg (str, optional): 如果请求失败，输出的错误信息前缀，默认为'请求失败'。
            retry_count (int, optional): 当前请求的重试次数，默认为0。

        Returns:
            Dict[str, Any]: 如果请求成功，返回响应的JSON数据。

        Raises:
            ValueError: 如果请求失败或响应包含错误信息，则抛出包含详细错误信息的异常。
        """
        try:
            response = requests.post(f"{BASE_URL}{url}",
                                     headers=headers,
                                     json=data,
                                     timeout=10)
            response.raise_for_status()
            rsp = response.json()
            logger.info(f"API响应 [{url}]: code={rsp.get('code')}, msg={rsp.get('msg')}")

            if rsp.get("code") == 200 and rsp.get("msg", "未知错误") == "302":
                raise ValueError("打卡失败，触发行为验证码")

            if rsp.get("code") == 200 or rsp.get("code") == 6111:
                return rsp

            if ("token失效" in rsp.get("msg", "未知错误")
                    and retry_count < self.max_retries):
                wait_time = 1 * (2 ** retry_count)
                time.sleep(wait_time)
                logger.warning("Token失效，正在重新登录...")
                if self.login():
                    new_token = UserInfoManager.get_token()
                    headers["authorization"] = new_token
                    logger.info("已更新 Authorization Token，重试请求")
                    return self._post_request(url, headers, data, retry_count + 1)
            else:
                raise ValueError(rsp.get("msg", "未知错误"))

        except (requests.RequestException, ValueError) as e:
            if re.search(r"[\u4e00-\u9fff]",
                         str(e)) or retry_count >= self.max_retries:
                raise ValueError(f"{str(e)}")

            wait_time = 1 * (2 ** retry_count)
            logger.warning(
                f"重试 {retry_count + 1}/{self.max_retries}，等待 {wait_time:.2f} 秒"
            )
            time.sleep(wait_time)

        return self._post_request(url, headers, data, retry_count + 1)

    def pass_blockPuzzle_captcha(self, max_attempts: int = 5) -> str:
        """
        通过行为验证码（验证码类型为blockPuzzle）。

        Args:
            max_attempts (Optional[int]): 最大尝试次数，默认为5次。

        Returns:
            str: 验证参数。

        Raises:
            Exception: 当达到最大尝试次数时抛出异常。
        """
        attempts = 0
        while attempts < max_attempts:
            captcha_url = "session/captcha/v1/get"
            request_data = {
                "clientUid": str(uuid.uuid4()).replace("-", ""),
                "captchaType": "blockPuzzle",
            }
            captcha_info = self._post_request(
                captcha_url,
                HEADERS,
                request_data,
            )
            slider_data = recognize_blockPuzzle_captcha(
                captcha_info["data"]["jigsawImageBase64"],
                captcha_info["data"]["originalImageBase64"],
            )
            check_slider_url = "session/captcha/v1/check"
            check_slider_data = {
                "pointJson":
                    aes_encrypt(slider_data, captcha_info["data"]["secretKey"],
                                "b64"),
                "token":
                    captcha_info["data"]["token"],
                "captchaType":
                    "blockPuzzle",
            }
            check_result = self._post_request(
                check_slider_url,
                HEADERS,
                check_slider_data,
            )
            if check_result.get("code") != 6111:
                return aes_encrypt(
                    captcha_info["data"]["token"] + "---" + slider_data,
                    captcha_info["data"]["secretKey"],
                    "b64",
                )
            attempts += 1
            time.sleep(random.uniform(1, 3))
        raise Exception("通过滑块验证码失败")

    def solve_click_word_captcha(self, max_retries: int = 3) -> str:
        retry_count = 0
        while retry_count < max_retries:

            # 获取验证码的接口地址
            captcha_endpoint = "attendence/clock/v1/get"
            captcha_request_payload = {
                "clientUid": str(uuid.uuid4()).replace("-", ""),  # 生成唯一客户端标识
                "captchaType": "clickWord",  # 验证码类型
            }

            # 向服务器请求验证码信息
            try:
                captcha_response = self._post_request(
                    captcha_endpoint,
                    self._get_authenticated_headers(),
                    captcha_request_payload,
                )
            except ValueError as e:
                if "触发行为验证码" in str(e):
                    logger.warning("验证码获取过程中遇到行为验证码，重试...")
                    retry_count += 1
                    time.sleep(random.uniform(1, 3))
                    continue
                else:
                    raise

            # 解析验证码图片数据
            try:
                captcha_solution = recognize_clickWord_captcha(
                    captcha_response["data"]["originalImageBase64"],
                    captcha_response["data"]["wordList"],
                )
                logger.info(f"生成的验证码坐标（未加密）: {captcha_solution}")
            except Exception as e:
                logger.warning(f"验证码识别失败: {e}，重试获取新验证码...")
                retry_count += 1
                time.sleep(random.uniform(1, 3))
                continue

            # 在发送验证请求前保存快照，显示将要发送的坐标 - 仅在手动测试模式下
            if os.environ.get('SAVE_CAPTCHA_SNAPSHOTS') == '1':
                try:
                    import os as _os
                    import sys as _sys
                    import cv2
                    import base64
                    import json
                    _os.chdir(_os.path.dirname(_os.path.abspath(_sys.argv[0])))
                    snapshot_dir = _os.path.join(_os.path.dirname(_os.path.abspath(_sys.argv[0])), "captcha_snapshots")
                    _os.makedirs(snapshot_dir, exist_ok=True)
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    before_submit_path = _os.path.join(snapshot_dir, f"before_submit_{timestamp}.png")
                    
                    captcha_bytes = base64.b64decode(captcha_response["data"]["originalImageBase64"])
                    captcha_image = cv2.imdecode(np.frombuffer(captcha_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                    
                    try:
                        coordinates = json.loads(captcha_solution)
                        for i, coord in enumerate(coordinates):
                            x = coord.get("x", 0)
                            y = coord.get("y", 0)
                            cv2.circle(captcha_image, (x, y), 15, (0, 255, 255), 2)
                            cv2.circle(captcha_image, (x, y), 3, (0, 255, 255), -1)
                            cv2.putText(captcha_image, str(i+1), (x-10, y-20), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        logger.info(f"已在提交前快照上绘制 {len(coordinates)} 个即将发送的点击位置")
                    except Exception as e:
                        logger.warning(f"绘制点击位置失败: {e}")
                    
                    cv2.imwrite(before_submit_path, captcha_image)
                    logger.info(f"验证码提交前快照已保存: {before_submit_path}")
                except Exception as e:
                    logger.warning(f"保存提交前快照失败: {e}")

            # 验证验证码的接口地址
            verification_endpoint = "attendence/clock/v1/check"
            encrypted_solution = aes_encrypt(captcha_solution,
                                captcha_response["data"]["secretKey"],
                                "b64")
            verification_payload = {
                "pointJson": encrypted_solution,  # 加密的点位数据
                "token": captcha_response["data"]["token"],  # 验证码令牌
                "captchaType": "clickWord",  # 验证码类型
            }
            logger.info(f"加密后的验证码坐标: {encrypted_solution[:50]}...")  # 只显示前50个字符

            # 验证用户点击结果
            try:
                verification_response = self._post_request(
                    verification_endpoint,
                    self._get_authenticated_headers(),
                    verification_payload,
                )
                logger.info(f"验证码验证响应: code={verification_response.get('code')}, msg={verification_response.get('msg')}")
            except ValueError as e:
                if "触发行为验证码" in str(e):
                    logger.warning("验证码验证过程中遇到行为验证码，重试...")
                    retry_count += 1
                    time.sleep(random.uniform(1, 3))
                    continue
                else:
                    logger.error(f"验证码验证异常: {e}")
                    raise

            # 如果验证码验证成功，则返回加密结果
            if verification_response.get("code") != 6111:  # 6111 表示验证码验证失败
                logger.info(f"验证码验证成功！响应数据: {verification_response}")
                # 验证成功后保存验证码图片快照 - 仅在手动测试模式下
                if os.environ.get('SAVE_CAPTCHA_SNAPSHOTS') == '1':
                    try:
                        import os as _os
                        import sys as _sys
                        import cv2
                        import base64
                        import json
                        _os.chdir(_os.path.dirname(_os.path.abspath(_sys.argv[0])))
                        snapshot_dir = _os.path.join(_os.path.dirname(_os.path.abspath(_sys.argv[0])), "captcha_snapshots")
                        _os.makedirs(snapshot_dir, exist_ok=True)
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        after_verify_path = _os.path.join(snapshot_dir, f"after_verify_{timestamp}.png")
                        captcha_bytes = base64.b64decode(captcha_response["data"]["originalImageBase64"])
                        captcha_image = cv2.imdecode(np.frombuffer(captcha_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                        try:
                            coordinates = json.loads(captcha_solution)
                            for i, coord in enumerate(coordinates):
                                x = coord.get("x", 0)
                                y = coord.get("y", 0)
                                cv2.circle(captcha_image, (x, y), 15, (0, 255, 0), 2)
                                cv2.circle(captcha_image, (x, y), 3, (0, 255, 0), -1)
                                cv2.putText(captcha_image, str(i+1), (x-10, y-20), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            logger.info(f"已在验证后快照上绘制 {len(coordinates)} 个成功点击位置")
                        except Exception as e:
                            logger.warning(f"绘制点击位置失败: {e}")
                        cv2.imwrite(after_verify_path, captcha_image)
                        logger.info(f"验证码验证后快照已保存: {after_verify_path}")
                    except Exception as e:
                        logger.warning(f"保存验证后快照失败: {e}")
                
                encrypted_result = aes_encrypt(
                    captcha_response["data"]["token"] + "---" +
                    captcha_solution,
                    captcha_response["data"]["secretKey"],
                    "b64",
                )
                return encrypted_result
            else:
                logger.warning(f"验证码验证失败！响应数据: {verification_response}")
                # 验证失败时也保存快照 - 仅在手动测试模式下
                if os.environ.get('SAVE_CAPTCHA_SNAPSHOTS') == '1':
                    try:
                        import os as _os
                        import sys as _sys
                        import cv2
                        import base64
                        import json
                        _os.chdir(_os.path.dirname(_os.path.abspath(_sys.argv[0])))
                        snapshot_dir = _os.path.join(_os.path.dirname(_os.path.abspath(_sys.argv[0])), "captcha_snapshots")
                        _os.makedirs(snapshot_dir, exist_ok=True)
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        failed_verify_path = _os.path.join(snapshot_dir, f"failed_verify_{timestamp}.png")
                        captcha_bytes = base64.b64decode(captcha_response["data"]["originalImageBase64"])
                        captcha_image = cv2.imdecode(np.frombuffer(captcha_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                        try:
                            coordinates = json.loads(captcha_solution)
                            for i, coord in enumerate(coordinates):
                                x = coord.get("x", 0)
                                y = coord.get("y", 0)
                                cv2.circle(captcha_image, (x, y), 15, (0, 0, 255), 2)
                                cv2.circle(captcha_image, (x, y), 3, (0, 0, 255), -1)
                                cv2.putText(captcha_image, str(i+1), (x-10, y-20), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            logger.info(f"已在失败快照上绘制 {len(coordinates)} 个失败点击位置")
                        except Exception as e:
                            logger.warning(f"绘制点击位置失败: {e}")
                        cv2.imwrite(failed_verify_path, captcha_image)
                        logger.info(f"验证码验证失败快照已保存: {failed_verify_path}")
                    except Exception as e:
                        logger.warning(f"保存失败快照失败: {e}")

            # 验证失败，增加重试次数
            retry_count += 1
            # 随机等待以模拟正常用户行为
            time.sleep(random.uniform(1, 3))

        # 超过最大重试次数，抛出异常
        raise Exception("通过点选验证码失败")

    def _get_authenticated_headers(
            self,
            sign_data: Optional[List[Optional[str]]] = None  # 允许 List[str | None]
    ) -> Dict[str, str]:
        """
        生成带有认证信息的请求头。

        该方法会从配置管理器中获取用户的Token、用户ID及角色Key，并生成包含这些信息的请求头。
        如果提供了sign_data，还会生成并添加签名信息。

        Args:
            sign_data (Optional[List[str]]): 用于生成签名的数据列表，默认为None。

        Returns:
            包含认证信息和签名的请求头字典。
        """
        headers = {
            **HEADERS,
            "authorization": UserInfoManager.get_token(),
            "userid": UserInfoManager.get_userid(),
            "rolekey": UserInfoManager.get("roleKey"),
        }
        if sign_data:
            headers["sign"] = create_sign(*sign_data)
        return headers

    def login(self) -> bool:
        """
        执行用户登录操作，成功后将 user_info 写入 UserInfoManager 管理的缓存和文件。

        Returns:
            bool: 登录并写入成功返回 True，否则返回 False
        """
        logger.info("执行登录")

        try:
            url = "session/user/v6/login"
            data = {
                "phone": aes_encrypt(ConfigManager.get("user", "phone")),
                "password": aes_encrypt(ConfigManager.get("user", "password")),
                "captcha": self.pass_blockPuzzle_captcha(),
                "loginType": "android",
                "uuid": str(uuid.uuid4()).replace("-", ""),
                "device": "android",
                "version": "5.31.6",
                "t": aes_encrypt(str(int(time.time() * 1000))),
            }

            logger.info(f"登录数据：{data}")
            response = self._post_request(url, HEADERS, data)

            encrypted_data = response.get("data")
            if not encrypted_data:
                logger.error("登录失败：返回数据为空")
                return False

            user_info = json.loads(aes_decrypt(encrypted_data))
            logger.info(f"登录结果：{user_info}")

            # 使用 UserInfoManager 写入缓存和文件
            UserInfoManager.set_userinfo(user_info)

            logger.info("用户信息已保存到 UserInfoManager 管理的文件和缓存中")
            return True

        except Exception as e:
            logger.exception(f"登录过程发生异常：{e}")
            return False

    def fetch_plan(self) -> bool:
        """
        获取当前用户的实习计划并更新 PlanInfoManager 中的 planInfo。

        返回:
            bool: 成功获取并更新 planInfo 返回 True，否则返回 False
        """
        try:
            # 生成请求
            url = "practice/plan/v3/getPlanByStu"
            data = {
                "pageSize": 999999,
                "t": aes_encrypt(str(int(time.time() * 1000)))
            }
            headers = self._get_authenticated_headers(sign_data=[
                UserInfoManager.get_userid(),
                UserInfoManager.get("roleKey"),
            ])

            # 发送请求
            rsp = self._post_request(url, headers, data)

            # 获取实习计划列表
            data_list = rsp.get("data")
            if not data_list or not isinstance(data_list, list):
                logger.warning("未获取到实习计划数据，rsp 内容: %s", rsp)
                return False

            plan_info = data_list[0]
            if not plan_info:
                logger.warning("实习计划数据为空")
                return False
            logger.info("获取到的实习计划数据: %s", plan_info)
            # 更新缓存和文件
            PlanInfoManager.set_planinfo(plan_info)
            logger.info("实习计划信息已更新到 PlanInfoManager")
            return True

        except Exception as e:
            logger.exception("获取实习计划过程中发生异常: %s", e)
            return False

    def get_checkin_info(self) -> Dict[str, Any]:
        """
        获取用户的打卡信息。

        该方法会发送请求获取当前用户当月的打卡记录。

        Returns:
            包含用户打卡信息的字典。

        Raises:
            ValueError: 如果获取打卡信息失败，抛出包含详细错误信息的异常。
        """
        url = "attendence/clock/v2/listSynchro"
        if UserInfoManager.get("userType") == "teacher":
            url = "attendence/clock/teacher/v1/listSynchro"
        headers = self._get_authenticated_headers()
        data = {
            **get_current_month_info(),
            "t":
                aes_encrypt(str(int(time.time() * 1000))),
        }
        rsp = self._post_request(url, headers, data)
        logger.info(f"打卡记录查询响应: code={rsp.get('code')}, msg={rsp.get('msg')}, data_type={type(rsp.get('data')).__name__}")
        if isinstance(rsp.get('data'), list):
            logger.info(f"data数组长度: {len(rsp.get('data', []))}")
            if rsp.get('data'):
                first_item = rsp['data'][0]
                logger.info(f"data[0] keys: {list(first_item.keys()) if isinstance(first_item, dict) else type(first_item).__name__}")
                if isinstance(first_item, dict):
                    log_list = first_item.get('logDtoList', [])
                    logger.info(f"logDtoList长度: {len(log_list)}, 类型: {[l.get('type') for l in log_list]}, 时间: {[l.get('createTime') for l in log_list]}")
        elif isinstance(rsp.get('data'), dict):
            logger.info(f"data keys: {list(rsp['data'].keys())}")
        # 返回打卡记录列表，兼容新旧格式
        data = rsp.get("data")
        if isinstance(data, list):
            if data and isinstance(data[0], dict) and "logDtoList" in data[0]:
                return data[0]
            return data
        return data if data else {}

    def has_morning_clock_in_today(self) -> bool:
        """
        检查今天是否已打上班卡。

        Returns:
            bool: 已打上班卡返回 True，否则返回 False
        """
        today_str = time.strftime("%Y-%m-%d")
        checkin_data = self.get_checkin_info()

        if not checkin_data:
            logger.info(f"未获取到打卡记录，判定今日({today_str})未打上班卡")
            return False

        # 兼容新旧格式：新格式是list，旧格式是dict带logDtoList
        if isinstance(checkin_data, list):
            log_list = checkin_data
        else:
            log_list = checkin_data.get("logDtoList", [])

        logger.info(f"打卡记录数: {len(log_list)}, 记录类型: {[log.get('type') for log in log_list[:5]]}, 记录时间: {[log.get('createTime') for log in log_list[:5]]}")
        if not log_list:
            logger.info(f"今日({today_str})无打卡记录，未打上班卡")
            return False

        for log in log_list:
            create_time = log.get("createTime", "")
            log_type = log.get("type", "")
            if create_time.startswith(today_str) and log_type == "START":
                logger.info(f"今日({today_str})上班卡已打: {create_time}")
                return True

        logger.info(f"今日({today_str})未找到上班卡记录")
        return False

    def has_evening_clock_in_today(self) -> bool:
        """
        检查今天是否已打下班卡。

        Returns:
            bool: 已打下班卡返回 True，否则返回 False
        """
        today_str = time.strftime("%Y-%m-%d")
        checkin_data = self.get_checkin_info()

        if not checkin_data:
            return False

        # 兼容新旧格式
        if isinstance(checkin_data, list):
            log_list = checkin_data
        else:
            log_list = checkin_data.get("logDtoList", [])

        if not log_list:
            return False

        for log in log_list:
            create_time = log.get("createTime", "")
            log_type = log.get("type", "")
            if create_time.startswith(today_str) and log_type == "END":
                logger.info(f"今日({today_str})下班卡已打: {create_time}")
                return True

        logger.info(f"今日({today_str})未找到下班卡记录")
        return False

    def _validate_clock_in_response(self, rsp: Dict[str, Any]) -> dict[str, dict[str, Any] | bool]:
        """
        验证打卡响应是否真正成功。

        检查响应的 code、msg 和 data 字段，确认打卡是否真正成功。

        Args:
            rsp: API 响应字典

        Returns:
            dict: {"result": True/False, "data": 响应数据或错误信息}
        """
        code = rsp.get("code")
        msg = rsp.get("msg", "")
        data = rsp.get("data")

        logger.info(f"打卡响应详情: code={code}, msg={msg}, data={data}")

        # code 6111 通常表示重复打卡或已打卡
        if code == 6111:
            logger.warning(f"打卡可能重复: code={code}, msg={msg}")
            return {"result": False, "data": f"打卡失败: {msg} (code={code})"}

        # code 200 需要进一步检查 msg
        if code == 200:
            if msg == "success" or msg == "SUCCESS":
                logger.info("打卡响应确认为成功")
                return {"result": True, "data": rsp}
            elif msg:
                logger.warning(f"打卡响应 code=200 但 msg 异常: {msg}")
                return {"result": False, "data": f"打卡失败: {msg}"}
            elif data is not None:
                logger.info("打卡响应 code=200, data 非空，视为成功")
                return {"result": True, "data": rsp}
            else:
                logger.warning("打卡响应 code=200 但 data 为空")
                return {"result": False, "data": "打卡失败: 服务器返回空数据"}

        # 其他情况
        logger.error(f"打卡响应异常: code={code}, msg={msg}")
        return {"result": False, "data": f"打卡失败: {msg} (code={code})"}

    def submit_clock_in(self, checkin_info: Dict[str, Any]) -> dict[str, dict[str, Any] | bool] | None:
        """
        提交打卡信息。

        该方法会根据传入的打卡信息生成打卡请求，并发送至服务器完成打卡操作。

        Args:
            checkin_info (Dict[str, Any]): 包含打卡类型及相关信息的字典。

        Raises:
            ValueError: 如果打卡提交失败，抛出包含详细错误信息的异常。
        """
        url = "attendence/clock/teacher/v2/save"
        sign_data = None
        planId = PlanInfoManager.get_plan_id()

        if UserInfoManager.get("userType") != "teacher":
            url = "attendence/clock/v6/save"
            sign_data = [
                ConfigManager.get("device"),
                checkin_info.get("type"),
                planId,
                UserInfoManager.get_userid(),
                ConfigManager.get("clockIn", "location", "address")
            ]

        logger.info(f'打卡类型：{checkin_info.get("type")}')

        data = {
            "distance": None,
            "content": None,
            "lastAddress": None,
            "lastDetailAddress": checkin_info.get("lastDetailAddress"),
            "attendanceId": None,
            "country": "中国",
            "createBy": None,
            "createTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "description": checkin_info.get("description", None),
            "device": ConfigManager.get("device"),
            "images": None,
            "isDeleted": None,
            "isReplace": None,
            "modifiedBy": None,
            "modifiedTime": None,
            "schoolId": None,
            "state": "NORMAL",
            "teacherId": None,
            "teacherNumber": None,
            "type": checkin_info.get("type"),
            "stuId": None,
            "planId": planId,
            "attendanceType": None,
            "username": None,
            "attachments": checkin_info.get("attachments", None),
            "userId": UserInfoManager.get_userid(),
            "isSYN": None,
            "studentId": None,
            "applyState": None,
            "studentNumber": None,
            "memberNumber": None,
            "headImg": None,
            "attendenceTime": None,
            "depName": None,
            "majorName": None,
            "className": None,
            "logDtoList": None,
            "isBeyondFence": None,
            "practiceAddress": None,
            "tpJobId": None,
            "version": "5.31.6",
            "t": aes_encrypt(str(int(time.time() * 1000))),
        }

        data.update(ConfigManager.get("clockIn", "location"))

        headers = self._get_authenticated_headers(sign_data)

        try:
            responses = self._post_request(url, headers, data)
        except ValueError as e:
            if "触发行为验证码" in str(e):
                logger.info("检测到行为验证码，正在通过第一次验证码...")
                data["captcha"] = self.solve_click_word_captcha(max_retries=2)
                # 添加延时，模拟人类操作
                time.sleep(random.uniform(4, 8))  # 增加延时到4-8秒，更像真人操作
                # 重新提交打卡请求，处理可能再次遇到的验证码
                try:
                    rsp = self._post_request(url, headers, data)
                    logger.info(f"第一次验证码后打卡结果: {rsp}")
                    return self._validate_clock_in_response(rsp)
                except ValueError as e2:
                    if "触发行为验证码" in str(e2):
                        logger.info("再次遇到行为验证码，正在通过第二次验证码...")
                        data["captcha"] = self.solve_click_word_captcha(max_retries=2)
                        # 添加延时，模拟人类操作
                        time.sleep(random.uniform(4, 8))  # 增加延时到4-8秒，更像真人操作
                        try:
                            rsp = self._post_request(url, headers, data)
                            logger.info(f"第二次验证码后打卡结果: {rsp}")
                            return self._validate_clock_in_response(rsp)
                        except ValueError as e3:
                            if "触发行为验证码" in str(e3):
                                logger.error("连续三次遇到行为验证码，打卡失败")
                                return {"result": False, "data": "打卡失败，多次触发行为验证码"}
                            else:
                                raise
                    else:
                        raise
            else:
                raise
        
        if responses.get("msg") == "302":
            logger.info("检测到行为验证码，正在通过第一次验证码...")
            data["captcha"] = self.solve_click_word_captcha(max_retries=2)
            # 添加延时，模拟人类操作
            time.sleep(random.uniform(4, 8))  # 增加延时到4-8秒，更像真人操作
            # 重新提交打卡请求，处理可能再次遇到的验证码
            try:
                rsp = self._post_request(url, headers, data)
                logger.info(f"第一次验证码后打卡结果: {rsp}")
                return self._validate_clock_in_response(rsp)
            except ValueError as e:
                if "触发行为验证码" in str(e):
                    logger.info("再次遇到行为验证码，正在通过第二次验证码...")
                    data["captcha"] = self.solve_click_word_captcha(max_retries=2)
                    # 添加延时，模拟人类操作
                    time.sleep(random.uniform(4, 8))  # 增加延时到4-8秒，更像真人操作
                    try:
                        rsp = self._post_request(url, headers, data)
                        logger.info(f"第二次验证码后打卡结果: {rsp}")
                        return self._validate_clock_in_response(rsp)
                    except ValueError as e2:
                        if "触发行为验证码" in str(e2):
                            logger.error("连续三次遇到行为验证码，打卡失败")
                            return {"result": False, "data": "打卡失败，多次触发行为验证码"}
                        else:
                            raise
                else:
                    raise
        else:
            return self._validate_clock_in_response(responses)