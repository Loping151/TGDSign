"""TGDSign - 塔吉多签到插件 for gsuid_core"""

from gsuid_core.sv import Plugins
from gsuid_core.logger import logger

from .tgdsign_config.tgdsign_config import TGDSignConfig  # noqa: F401  触发配置迁移

Plugins(
    name="TGDSign",
    force_prefix=["tgd", "yh", "ht"],
    allow_empty_prefix=False,
)

logger.info("[TGDSign] 塔吉多签到插件已加载")
