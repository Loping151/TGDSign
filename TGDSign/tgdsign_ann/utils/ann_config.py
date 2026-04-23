"""公告推送 ID 持久化"""
import json
from pathlib import Path
from typing import List

from gsuid_core.logger import logger

from ...utils.path import MAIN_PATH

ANN_CONFIG_PATH = MAIN_PATH / "ann_config.json"


def _load_config() -> dict:
    if not ANN_CONFIG_PATH.exists():
        return {}
    try:
        with open(ANN_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[TGDSign] 加载公告配置失败: {e}")
        return {}


def _save_config(config: dict) -> None:
    try:
        ANN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ANN_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[TGDSign] 保存公告配置失败: {e}")


def get_ann_new_ids() -> List:
    config = _load_config()
    return config.get("ann_new_ids", [])


def set_ann_new_ids(ids: List) -> None:
    config = _load_config()
    config["ann_new_ids"] = ids
    _save_config(config)
