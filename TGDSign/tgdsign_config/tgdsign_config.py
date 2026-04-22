"""TGDSign 配置管理"""

import shutil
from pathlib import Path

from gsuid_core.data_store import get_res_path
from gsuid_core.logger import logger
from gsuid_core.utils.plugins_config.gs_config import StringConfig

from .config_default import CONIFG_DEFAULT

MAIN_PATH = get_res_path() / "TGDSign"
MAIN_PATH.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = MAIN_PATH / "config.json"

# 从旧路径迁移到标准存储路径
_OLD_CONFIG_PATH = Path(__file__).parent / "config.json"
if _OLD_CONFIG_PATH.exists():
    if not CONFIG_PATH.exists():
        shutil.move(str(_OLD_CONFIG_PATH), str(CONFIG_PATH))
        logger.info(f"[TGDSign] 配置已迁移至 {CONFIG_PATH}")
    else:
        _OLD_CONFIG_PATH.unlink()
        logger.info(f"[TGDSign] 检测到新旧配置并存，已删除旧配置 {_OLD_CONFIG_PATH}")

TGDSignConfig = StringConfig("TGDSign", CONFIG_PATH, CONIFG_DEFAULT)
