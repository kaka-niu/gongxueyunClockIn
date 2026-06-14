import logging

from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager
from util.ApiService import ApiService

logger = logging.getLogger(__name__)


def login() -> bool:
    """
    登录流程：
    1. 如果本地 token 存在，直接返回 True
    2. 否则调用 ApiService.login() 执行登录并写入 userInfo.json
    """
    logging.info("检查登录状态")
    token = UserInfoManager.get_token()
    isSame = ConfigManager.get("user", "phone") == UserInfoManager.get("phone")
    if isSame:
        if token:
            logger.info("检测到本地 token，跳过登录")
            return True
        else:
            logger.info("未检测到 token，开始执行登录")
    else:
        logger.info("检测到用户信息不一致，执行重新登录")
    api_client = ApiService()
    success = api_client.login()

    if success:
        logger.info("登录成功")
    else:
        logger.warning("登录失败")

    return success
