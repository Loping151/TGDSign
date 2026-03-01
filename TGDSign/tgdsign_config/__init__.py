"""TGDSign 配置"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.subscribe import gs_subscribe

from .tgdsign_config import TGDSignConfig
from ..utils.database.models import TGDBind, TGDUser

SIGN_RESULT_TYPE = "订阅塔吉多签到结果"

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


@sv_tgd_config.on_regex(r"^(订阅|取消订阅)签到结果$", block=True)
async def tgd_subscribe_sign_result(bot: Bot, ev: Event):
    if "取消" in ev.raw_text:
        await gs_subscribe.delete_subscribe(
            "single", SIGN_RESULT_TYPE, ev
        )
        await bot.send("[TGDSign] 已取消订阅签到结果")
    else:
        await gs_subscribe.add_subscribe(
            "single", SIGN_RESULT_TYPE, ev
        )
        await bot.send("[TGDSign] 已订阅签到结果，自动签到完成后将推送结果")
