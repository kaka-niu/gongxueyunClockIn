import json
import logging
from pathlib import Path
from typing import Any, Optional
import sys
import copy

from util.HelperFunctions import desensitize_phone

logger = logging.getLogger(__name__)

# ======================
# 根目录 & userInfo 路径
# ======================
if getattr(sys, 'frozen', False):
    # 打包 exe 后
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # 源码运行
    BASE_DIR = Path(__file__).resolve().parent.parent

USER_DIR = BASE_DIR / "user"
USER_DIR.mkdir(parents=True, exist_ok=True)  # 不存在则自动创建

USER_INFO_PATH = USER_DIR / "userInfo.json"


class UserInfoManager:
    """
    管理 userInfo.json：
    - 支持多用户（数组格式）
    - 加载到缓存
    - 提供 token、userId 及其他任意字段访问
    - 更新缓存并写回文件
    """
    _userInfo_cache: list | dict | None = None
    _current_user_index: int = 0

    @classmethod
    def _load_from_file(cls) -> Optional[list | dict]:
        # 原代码（单用户）：
        # if not USER_INFO_PATH.exists():
        #     logger.warning(f"userInfo.json 不存在: {USER_INFO_PATH.resolve()}")
        #     return None
        # try:
        #     with open(USER_INFO_PATH, "r", encoding="utf-8") as f:
        #         data = json.load(f)
        #     return data.get("userInfo")
        # except Exception as e:
        #     logger.error(f"读取 userInfo 失败: {e}")
        #     return None
        
        # 新代码（支持多用户）：
        if not USER_INFO_PATH.exists():
            logger.warning(f"userInfo.json 不存在: {USER_INFO_PATH.resolve()}")
            return None
        try:
            with open(USER_INFO_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 支持多用户配置（数组格式）和单用户配置（对象格式）
            if isinstance(data, list):
                return data
            else:
                # 兼容旧格式，转换为数组
                return [data]
        except Exception as e:
            logger.error(f"读取 userInfo 失败: {e}")
            return None

    @classmethod
    def load(cls) -> Optional[list | dict]:
        """获取缓存中的 userInfo，如果没有缓存则从文件加载"""
        if cls._userInfo_cache is not None:
            return cls._userInfo_cache
        cls._userInfo_cache = cls._load_from_file()
        return cls._userInfo_cache

    @classmethod
    def set_current_user(cls, index: int):
        """设置当前操作的用户索引"""
        cls._current_user_index = index

    @classmethod
    def get_current_user_info(cls) -> Optional[dict]:
        """获取当前用户的 userInfo"""
        userinfo = cls.load()
        if not userinfo:
            return None
        if isinstance(userinfo, list):
            if 0 <= cls._current_user_index < len(userinfo):
                user_data = userinfo[cls._current_user_index]
                return user_data.get("userInfo") if isinstance(user_data, dict) else None
            return None
        return userinfo.get("userInfo") if isinstance(userinfo, dict) else None

    @classmethod
    def set_userinfo(cls, userinfo: dict):
        # 原代码（单用户）：
        # cls._userInfo_cache = userinfo
        # try:
        #     USER_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)
        #     with open(USER_INFO_PATH, "w", encoding="utf-8") as f:
        #         json.dump({"userInfo": userinfo}, f, ensure_ascii=False, indent=4)
        #     logger.info(f"userInfo.json 已更新: {USER_INFO_PATH.resolve()}")
        # except Exception as e:
        #     logger.error(f"写入 userInfo.json 失败: {e}")
        
        # 新代码（支持多用户）：
        cache_data = cls.load()
        if cache_data is None:
            cache_data = []
        
        if isinstance(cache_data, list):
            # 确保数组长度足够
            while len(cache_data) <= cls._current_user_index:
                cache_data.append({})
            cache_data[cls._current_user_index] = {"userInfo": userinfo}
        else:
            cache_data = {"userInfo": userinfo}
        
        cls._userInfo_cache = cache_data
        # 写入文件时对手机号脱敏
        try:
            # 深拷贝一份用于写入文件，脱敏 phone 字段
            cache_data_for_file = copy.deepcopy(cache_data)
            if isinstance(cache_data_for_file, list):
                for item in cache_data_for_file:
                    if isinstance(item, dict) and "userInfo" in item:
                        ui = item["userInfo"]
                        if isinstance(ui, dict) and "phone" in ui:
                            ui["phone"] = desensitize_phone(ui["phone"])
            else:
                ui = cache_data_for_file.get("userInfo")
                if isinstance(ui, dict) and "phone" in ui:
                    ui["phone"] = desensitize_phone(ui["phone"])
            
            USER_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(USER_INFO_PATH, "w", encoding="utf-8") as f:
                json.dump(cache_data_for_file, f, ensure_ascii=False, indent=4)
            logger.info(f"userInfo.json 已更新: {USER_INFO_PATH.resolve()}")
        except Exception as e:
            logger.error(f"写入 userInfo.json 失败: {e}")

    @classmethod
    def get(cls, *keys: str, default: Any = None) -> Any:
        # 原代码（单用户）：
        # userinfo = cls.load()
        # if not userinfo:
        #     return default
        # data = userinfo
        # for key in keys:
        #     if isinstance(data, dict) and key in data:
        #         data = data[key]
        #     else:
        #         return default
        # return data
        
        # 新代码（支持多用户）：
        userinfo = cls.get_current_user_info()
        if not userinfo:
            return default
        data = userinfo
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data

    @classmethod
    def get_token(cls) -> Optional[str]:
        """获取 token"""
        return cls.get("token")

    @classmethod
    def get_userid(cls) -> Optional[str]:
        """获取 userId"""
        return cls.get("userId")