"""TGDSign 配置管理"""

from pathlib import Path

from gsuid_core.utils.plugins_config.gs_config import StringConfig

from .config_default import CONIFG_DEFAULT

CONFIG_PATH = Path(__file__).parent / "config.json"

TGDSignConfig = StringConfig("TGDSign", CONFIG_PATH, CONIFG_DEFAULT)
