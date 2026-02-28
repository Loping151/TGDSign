"""TGDSign 配置"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger

from .tgdsign_config import TGDSignConfig
from ..utils.database.models import TGDBind, TGDUser

sv_tgd_config = SV("TGDSign-配置")


@sv_tgd_config.on_fullmatch(
    ("开启自动签到", "关闭自动签到"),
    block=True,
)
async def tgd_switch_auto_sign(bot: Bot, ev: Event):
    uid_list = await TGDBind.get_uid_list_by_game(ev.user_id, ev.bot_id)
    if not uid_list:
        return await bot.send("[TGDSign] 未绑定账号，请先登录")

    on_off = "on" if "开启" in ev.raw_text else "off"
    text = "开启" if on_off == "on" else "关闭"

    for uid in uid_list:
        await TGDUser.update_data_by_uid(
            uid=uid,
            bot_id=ev.bot_id,
            sign_switch=on_off,
        )

    await bot.send(f"[TGDSign] 已{text}自动签到")
