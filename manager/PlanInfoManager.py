import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ======================
# 根目录 & planInfo 路径
# ======================
if getattr(sys, 'frozen', False):
    # 打包 exe 后
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # 源码运行
    BASE_DIR = Path(__file__).resolve().parent.parent

USER_DIR = BASE_DIR / "user"
USER_DIR.mkdir(parents=True, exist_ok=True)  # 不存在则自动创建

PLAN_INFO_PATH = USER_DIR / "planInfo.json"


class PlanInfoManager:
    """
    管理 planInfo.json：
    - 加载到缓存
    - 提供任意字段访问（大小写不敏感）
    - 更新缓存并写回文件
    """
    _planinfo_cache: dict | None = None

    @classmethod
    def _load_from_file(cls) -> Optional[dict]:
        """从文件读取 planInfo"""
        if not PLAN_INFO_PATH.exists():
            logger.warning(f"planInfo.json 不存在: {PLAN_INFO_PATH.resolve()}")
            return None
        try:
            with open(PLAN_INFO_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            planinfo = data.get("planInfo")
            if planinfo:
                # 将键全部转换为小写，方便大小写不敏感访问
                planinfo = cls._lower_keys(planinfo)
            return planinfo
        except Exception as e:
            logger.error(f"读取 planInfo.json 失败: {e}")
            return None

    @classmethod
    def _lower_keys(cls, d: dict) -> dict:
        """递归将字典键转换为小写"""
        new_d = {}
        for k, v in d.items():
            if isinstance(v, dict):
                v = cls._lower_keys(v)
            new_d[k.lower()] = v
        return new_d

    @classmethod
    def load(cls) -> Optional[dict]:
        """获取缓存中的 planInfo，如果没有缓存则从文件加载"""
        if cls._planinfo_cache is not None:
            return cls._planinfo_cache
        cls._planinfo_cache = cls._load_from_file()
        return cls._planinfo_cache

    @classmethod
    def set_planinfo(cls, planinfo: dict):
        """更新缓存并写回文件"""
        cls._planinfo_cache = cls._lower_keys(planinfo)  # 保持缓存键为小写
        try:
            PLAN_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(PLAN_INFO_PATH, "w", encoding="utf-8") as f:
                json.dump({"planInfo": planinfo}, f, ensure_ascii=False, indent=4)
            logger.info(f"planInfo.json 已更新: {PLAN_INFO_PATH.resolve()}")
        except Exception as e:
            logger.error(f"写入 planInfo.json 失败: {e}")

    @classmethod
    def get(cls, *keys: str, default: Any = None) -> Any:
        """
        通用访问方法，大小写不敏感
        支持嵌套 key，例如：
            get("planPaper", "dayPaperNum") -> 5
        """
        planinfo = cls.load()
        if not planinfo:
            return default
        data = planinfo
        for key in keys:
            key_lower = key.lower()
            if isinstance(data, dict) and key_lower in data:
                data = data[key_lower]
            else:
                return default
        return data

    @classmethod
    def get_plan_id(cls) -> Optional[str]:
        """获取 planId"""
        return cls.get("planId")
