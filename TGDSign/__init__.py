"""TGDSign - 塔吉多签到插件 for gsuid_core"""

from gsuid_core.sv import Plugins
from gsuid_core.logger import logger

Plugins(
    name="TGDSign",
    force_prefix=["tgd", "yh", "ht"],
    allow_empty_prefix=False,
)

logger.info("[TGDSign] 塔吉多签到插件已加载")
