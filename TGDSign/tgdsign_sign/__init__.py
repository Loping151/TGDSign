"""TGDSign 签到指令"""

from datetime import datetime, timedelta

from gsuid_core.aps import scheduler
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..tgdsign_config.tgdsign_config import TGDSignConfig
from ..utils.database.models import TGDSignRecord
from .sign_handler import tgd_auto_sign_task, tgd_sign_handler

sv_tgd_sign = SV("TGDSign-签到", priority=1)
sv_tgd_sign_all = SV("TGDSign-全部签到", pm=0)

SIGN_TIME = TGDSignConfig.get_config("SignTime").data


@sv_tgd_sign.on_fullmatch(
    ("签到", "qd", "每日签到", "sign"),
    block=True,
)
async def tgd_user_sign(bot: Bot, ev: Event):
    msg = await tgd_sign_handler(bot, ev)
    return await bot.send(msg)


@sv_tgd_sign_all.on_fullmatch(("全部签到", "qbqd"), block=True)
async def tgd_sign_all(bot: Bot, ev: Event):
    await bot.send("[TGDSign] [全部签到] 已开始执行!")
    msg = await tgd_auto_sign_task()
    await bot.send("[TGDSign] [全部签到] 执行完成!")
    await bot.send(msg)


# 定时签到任务
SIGN_TIME_HOUR = int(SIGN_TIME[0])
SIGN_TIME_MINUTE = SIGN_TIME[1]

scheduler.add_job(
    tgd_auto_sign_task,
    "cron",
    id="tgd_auto_sign",
    hour=SIGN_TIME_HOUR,
    minute=SIGN_TIME_MINUTE,
)
logger.info(
    f"[TGDSign] 定时签到已注册: 每天 {SIGN_TIME_HOUR}:{SIGN_TIME_MINUTE}"
)


# 每日清理2天前的签到记录
@scheduler.scheduled_job("cron", hour=0, minute=5, id="tgd_clear_sign")
async def clear_sign_record():
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    await TGDSignRecord.clear_sign_record(two_days_ago)
    logger.info("[TGDSign] 已清除2天前的签到记录")
