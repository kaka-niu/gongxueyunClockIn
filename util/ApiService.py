import json
import logging
import random
import re
import time
import uuid
from typing import Dict, Any, List, Optional

import requests

from manager.ConfigManager import ConfigManager
from manager.PlanInfoManager import PlanInfoManager
from manager.UserInfoManager import UserInfoManager
from util.CaptchaUtils import recognize_blockPuzzle_captcha, recognize_clickWord_captcha
from util.CryptoUtils import create_sign, aes_encrypt, aes_decrypt
from util.HelperFunctions import get_current_month_info

logger = logging.getLogger(__name__)

# 常量
BASE_URL = "https://api.moguding.net:9000/"
HEADERS = {
    "user-agent": "Dart/2.17 (dart:io)",
    "content-type": "application/json; charset=utf-8",
    "accept-encoding": "gzip",
    "host": "api.moguding.net:9000",
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

            # if rsp.get("code") == 200 and rsp.get("msg", "未知错误") == "302":
            #     raise ValueError("打卡失败，触发行为验证码")
            if rsp.get("code") == 200 and rsp.get("msg", "未知错误") == "302":
                return rsp

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
                logger.info(f"服务端返回详情: code={rsp.get('code')}, msg={rsp.get('msg')}, data={rsp.get('data')}")
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

    # def solve_click_word_captcha(self, max_retries: int = 5) -> str:
    # def solve_click_word_captcha(self, max_retries: int = 2) -> str:
    def solve_click_word_captcha(self, max_retries: int = 2) -> dict:
        retry_count = 0
        while retry_count < max_retries:

            # 获取验证码的接口地址
            captcha_endpoint = "/attendence/clock/v1/get"
            captcha_request_payload = {
                "clientUid": str(uuid.uuid4()).replace("-", ""),  # 生成唯一客户端标识
                "captchaType": "clickWord",  # 验证码类型
            }

            # 向服务器请求验证码信息
            captcha_response = self._post_request(
                captcha_endpoint,
                self._get_authenticated_headers(),
                captcha_request_payload,
            )

            # 解析验证码图片数据
            captcha_solution = recognize_clickWord_captcha(
                captcha_response["data"]["originalImageBase64"],
                captcha_response["data"]["wordList"],
            )

            # 验证验证码的接口地址
            verification_endpoint = "/attendence/clock/v1/check"
            verification_payload = {
                "pointJson":
                    aes_encrypt(captcha_solution,
                                captcha_response["data"]["secretKey"],
                                "b64"),  # 加密的点位数据
                "token":
                    captcha_response["data"]["token"],  # 验证码令牌
                "captchaType":
                    "clickWord",  # 验证码类型
            }

            # 验证用户点击结果
            try:
                verification_response = self._post_request(
                    verification_endpoint,
                    self._get_authenticated_headers(),
                    verification_payload,
                )
            except ValueError:
                logger.warning("验证码校验请求失败，重试中...")
                retry_count += 1
                time.sleep(random.uniform(1, 3))
                continue

            # 如果验证码验证成功，则返回加密结果 + clientUid
            # if verification_response.get("code") != 6111:  # 6111 表示验证码验证失败
            if verification_response.get("code") == 200:
                encrypted_result = aes_encrypt(
                    captcha_response["data"]["token"] + "---" +
                    captcha_solution,
                    captcha_response["data"]["secretKey"],
                    "b64",
                )
                return {
                    "captcha": encrypted_result,
                    "clientUid": captcha_request_payload["clientUid"],
                }

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
            "version": "5.31.6",
        }
        if sign_data:
            headers["sign"] = create_sign(*sign_data)
            logger.info(f"[DEBUG] _get_authenticated_headers 生成签名: {headers['sign']}")
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
        # 每月第一天的第一次打卡返回的是空，所以特殊处理返回空字典
        # return rsp.get("data", [{}])[0] if rsp.get("data") else {}
        return rsp.get("data", [])

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

        # ========== 调试日志：打印签名组成 ==========
        if sign_data:
            logger.info(f"[DEBUG] 签名组成字段: device={sign_data[0]}")
            logger.info(f"[DEBUG] 签名组成字段: type={sign_data[1]}")
            logger.info(f"[DEBUG] 签名组成字段: planId={sign_data[2]}")
            logger.info(f"[DEBUG] 签名组成字段: userId={sign_data[3]}")
            logger.info(f"[DEBUG] 签名组成字段: address={sign_data[4]}")
            sign_raw = "".join(sign_data)
            logger.info(f"[DEBUG] 签名拼接原文: {sign_raw}")
            logger.info(f"[DEBUG] 签名盐值: 3478cbbc33f84bd00d75d7dfa69e0daa")
            logger.info(f"[DEBUG] 最终签名: {create_sign(*sign_data)}")
        # ========== 调试日志结束 ==========

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
            "t": aes_encrypt(str(int(time.time() * 1000))),
            "version": "5.31.6",
        }

        data.update(ConfigManager.get("clockIn", "location"))

        headers = self._get_authenticated_headers(sign_data)

        # ========== 调试日志：打印完整请求信息 ==========
        logger.info(f"[DEBUG] 请求URL: {BASE_URL}{url}")
        logger.info(f"[DEBUG] 请求头: {json.dumps(headers, ensure_ascii=False)}")
        logger.info(f"[DEBUG] 请求体(部分关键字段): device={data.get('device')}, type={data.get('type')}, planId={data.get('planId')}, userId={data.get('userId')}, address={data.get('address')}, lat={data.get('latitude')}, lng={data.get('longitude')}, version={data.get('version')}")
        # ========== 调试日志结束 ==========

        responses = self._post_request(url, headers, data)
        
        # 原始逻辑：处理302行为验证码
        if responses.get("msg") == "302":
            logger.info("检测到行为验证码，正在通过···")
            captcha_result = self.solve_click_word_captcha()
            data["captcha"] = captcha_result["captcha"]
            rsp = self._post_request(url, headers, data)
            logger.info(f"打卡结果: {rsp}")
            # return {"result": True, "data": rsp}
            logger.info(f"打卡接口返回完整响应(验证码): code={rsp.get('code')}, msg={rsp.get('msg')}, data={rsp.get('data')}")
            # if rsp.get("code") == 200 or rsp.get("code") == 6111:
            #     return {"result": True, "data": rsp}
            # else:
            #     return {"result": False, "data": rsp, "message": rsp.get("msg", "打卡失败")}
            return self._check_clock_in_response(rsp)
        
        # 原代码（点选验证码绕过安全验证）：
        # elif responses.get("msg") == "304":
        #     logger.warning("需要安全验证，尝试通过验证码绕过...")
        #     captcha_result = self.solve_click_word_captcha()
        #     data["appUuid"] = captcha_result["clientUid"]
        #     data["captcha"] = captcha_result["captcha"]
        #     rsp = self._post_request(url, headers, data)
        #     logger.info(f"安全验证后打卡结果: code={rsp.get('code')}, msg={rsp.get('msg')}, data={rsp.get('data')}")
        #     return self._check_clock_in_response(rsp)
        
        elif responses.get("msg") == "304":
            return self._handle_verification(url, headers, data)
        
        else:
            logger.info(f"打卡接口返回完整响应: code={responses.get('code')}, msg={responses.get('msg')}, data={responses.get('data')}")
            # if responses.get("code") == 200 or responses.get("code") == 6111:
            #     return {"result": True, "data": responses}
            # else:
            #     return {"result": False, "data": responses, "message": responses.get("msg", "打卡失败")}
            return self._check_clock_in_response(responses)

    def _handle_verification(self, url, headers, data):
        """处理验证流程"""
        _r = self.solve_click_word_captcha()
        _m = {
            "appUuid": _r["clientUid"],
            "captcha": _r["captcha"]
        }
        data.update(_m)
        rsp = self._post_request(url, headers, data)
        logger.info(f"验证处理后结果: code={rsp.get('code')}, msg={rsp.get('msg')}")
        return self._check_clock_in_response(rsp)

    def _try_bypass_face_recognition(self, url: str, headers: Dict[str, str], 
                                      original_data: Dict[str, Any], 
                                      checkin_info: Dict[str, Any]) -> Optional[dict]:
        """
        尝试绕过304人脸认证
        
        策略：
        1. 修改设备参数（将 isPhysicalDevice 改为 false）
        2. 尝试使用旧版本API（v5）
        3. 添加人脸认证相关参数（faceVerified=false）
        
        Args:
            url: 原始请求URL
            headers: 原始请求头
            original_data: 原始请求数据
            checkin_info: 打卡信息
            
        Returns:
            dict: 如果绕过成功返回成功结果，否则返回None
        """
        logger.info("开始尝试绕过人脸认证...")
        
        # 策略1：修改设备参数，将 isPhysicalDevice 改为 false
        logger.info("策略1：修改设备参数 (isPhysicalDevice=false)")
        try:
            modified_device = ConfigManager.get("device").copy() if isinstance(ConfigManager.get("device"), dict) else {}
            modified_device["isPhysicalDevice"] = False
            
            bypass_data = original_data.copy()
            bypass_data["device"] = modified_device
            bypass_data["faceVerified"] = False
            bypass_data["needFaceVerify"] = False
            
            # 重新生成签名（因为device改变了）
            if UserInfoManager.get("userType") != "teacher":
                sign_data = [
                    json.dumps(modified_device, ensure_ascii=False),
                    checkin_info.get("type"),
                    PlanInfoManager.get_plan_id(),
                    UserInfoManager.get_userid(),
                    ConfigManager.get("clockIn", "location", "address")
                ]
                bypass_headers = self._get_authenticated_headers(sign_data)
            else:
                bypass_headers = headers.copy()
            
            rsp1 = self._post_request(url, bypass_headers, bypass_data)
            logger.info(f"策略1响应: code={rsp1.get('code')}, msg={rsp1.get('msg')}")
            
            if rsp1.get("msg") == "success" or (rsp1.get("code") == 200 and rsp1.get("data")):
                logger.info("策略1绕过成功！")
                return self._check_clock_in_response(rsp1)
        except Exception as e:
            logger.warning(f"策略1失败: {e}")
        
        # 策略2：尝试使用旧版本API（v5）
        logger.info("策略2：尝试使用旧版本API (v5)")
        try:
            old_url = "attendence/clock/v5/save"
            
            # 使用原始数据，但修改URL
            rsp2 = self._post_request(old_url, headers, original_data)
            logger.info(f"策略2响应: code={rsp2.get('code')}, msg={rsp2.get('msg')}")
            
            if rsp2.get("msg") == "success" or (rsp2.get("code") == 200 and rsp2.get("data")):
                logger.info("策略2绕过成功！")
                return self._check_clock_in_response(rsp2)
        except Exception as e:
            logger.warning(f"策略2失败: {e}")
        
        # 策略3：修改version参数
        logger.info("策略3：修改version参数")
        try:
            bypass_headers = headers.copy()
            bypass_headers["version"] = "5.30.0"  # 使用旧版本号
            
            bypass_data = original_data.copy()
            bypass_data["version"] = "5.30.0"
            
            rsp3 = self._post_request(url, bypass_headers, bypass_data)
            logger.info(f"策略3响应: code={rsp3.get('code')}, msg={rsp3.get('msg')}")
            
            if rsp3.get("msg") == "success" or (rsp3.get("code") == 200 and rsp3.get("data")):
                logger.info("策略3绕过成功！")
                return self._check_clock_in_response(rsp3)
        except Exception as e:
            logger.warning(f"策略3失败: {e}")
        
        # 策略4：添加模拟的人脸认证信息
        logger.info("策略4：添加模拟人脸认证信息")
        try:
            bypass_data = original_data.copy()
            bypass_data["faceVerified"] = True
            bypass_data["faceVerifyTime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            bypass_data["faceScore"] = 0.95  # 模拟人脸相似度分数
            bypass_data["isFaceVerify"] = True
            
            rsp4 = self._post_request(url, headers, bypass_data)
            logger.info(f"策略4响应: code={rsp4.get('code')}, msg={rsp4.get('msg')}")
            
            if rsp4.get("msg") == "success" or (rsp4.get("code") == 200 and rsp4.get("data")):
                logger.info("策略4绕过成功！")
                return self._check_clock_in_response(rsp4)
        except Exception as e:
            logger.warning(f"策略4失败: {e}")
        
        logger.warning("所有绕过策略均失败")
        return None

    def _check_clock_in_response(self, rsp: Dict[str, Any]) -> dict:
        """检查打卡接口返回结果，根据 msg 和 data 判断是否真正成功

        常见 msg 值：
        - "success": 打卡成功
        - "302": 触发行为验证码（已在 submit_clock_in 中处理）
        - "304": 需要人脸认证，脚本无法处理
        - 其他非空值: 可能为各种错误

        Args:
            rsp: API 返回的原始响应

        Returns:
            dict: {"result": bool, "data": ..., "message": ...}
        """
        code = rsp.get("code")
        msg = rsp.get("msg")
        data = rsp.get("data")

        # code 必须为 200
        if code != 200 and code != 6111:
            return {"result": False, "data": rsp, "message": str(msg) if msg else "打卡失败"}

        # msg=success: 明确成功
        if msg == "success":
            return {"result": True, "data": rsp}

        # msg=304: 需要人脸认证，脚本无法处理，需在手机上手动打卡
        if msg == "304":
            logger.warning("打卡接口返回 msg=304，需要人脸认证，脚本无法处理")
            return {"result": False, "data": rsp, "message": "打卡失败(304)：需要人脸认证，请在手机 APP 上完成打卡"}

        # data 为空视为失败
        if data is None:
            logger.warning(f"打卡接口返回 data 为空，msg={msg}")
            return {"result": False, "data": rsp, "message": f"打卡失败：服务器未返回打卡数据(msg={msg})"}

        # 其他情况：有 data 则视为成功
        return {"result": True, "data": rsp}