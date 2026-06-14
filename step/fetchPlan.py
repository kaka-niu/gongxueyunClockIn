import logging

from manager.PlanInfoManager import PlanInfoManager
from util.ApiService import ApiService

logger = logging.getLogger(__name__)


def fetch_plan() -> bool:
    """
    获取打卡计划信息

    Returns:
        bool: 获取成功返回True，获取失败返回False
    """
    logging.info("检查打卡信息")

    # 检查本地是否已存在打卡计划信息
    planId = PlanInfoManager.get_plan_id()
    if planId:
        logger.info("检测到本地已有打卡信息 ，跳过获取打卡信息")
        return True

    logger.info("未检测到打卡信息，开始执行获取打卡信息")

    # 调用API服务获取打卡计划信息
    api_client = ApiService()
    success = api_client.fetch_plan()

    # 记录获取结果
    if success:
        logger.info("打卡信息获取成功")
    else:
        logger.warning("打卡信息获取失败")

    return success
