import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

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
    - 加载到缓存
    - 提供 token、userId 及其他任意字段访问
    - 更新缓存并写回文件
    """
    _userInfo_cache: dict | None = None

    @classmethod
    def _load_from_file(cls) -> Optional[dict]:
        """从文件读取 userInfo"""
        if not USER_INFO_PATH.exists():
            logger.warning(f"userInfo.json 不存在: {USER_INFO_PATH.resolve()}")
            return None
        try:
            with open(USER_INFO_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("userInfo")  # 改成大写 I
        except Exception as e:
            logger.error(f"读取 userInfo 失败: {e}")
            return None

    @classmethod
    def load(cls) -> Optional[dict]:
        """获取缓存中的 userInfo，如果没有缓存则从文件加载"""
        if cls._userInfo_cache is not None:
            return cls._userInfo_cache
        cls._userInfo_cache = cls._load_from_file()
        return cls._userInfo_cache

    @classmethod
    def set_userinfo(cls, userinfo: dict):
        """更新缓存并写回文件"""
        cls._userInfo_cache = userinfo
        try:
            USER_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(USER_INFO_PATH, "w", encoding="utf-8") as f:
                json.dump({"userInfo": userinfo}, f, ensure_ascii=False, indent=4)
            logger.info(f"userInfo.json 已更新: {USER_INFO_PATH.resolve()}")
        except Exception as e:
            logger.error(f"写入 userInfo.json 失败: {e}")

    @classmethod
    def get(cls, *keys: str, default: Any = None) -> Any:
        """
        通用访问方法
        支持嵌套 key，例如：
            get("orgJson", "className") -> "物联网2121"
        """
        userinfo = cls.load()
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
