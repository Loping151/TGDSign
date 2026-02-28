"""TGDSign 帮助指令"""

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV, get_plugin_available_prefix

sv_tgd_help = SV("TGDSign-帮助", priority=1)

PREFIX = get_plugin_available_prefix("TGDSign")

HELP_TEXT = f"""[TGDSign] 塔吉多签到 帮助
指令前缀: {PREFIX}
=============================
玩家指令:
  登录 - 登录塔吉多账号
  签到 - 手动执行签到
  开启自动签到 - 开启每日自动签到
  关闭自动签到 - 关闭每日自动签到
  帮助 - 显示本帮助

主人指令:
  全部签到 - 为所有已登录用户执行签到
=============================
示例: {PREFIX}签到"""


@sv_tgd_help.on_fullmatch(("帮助", "help"), block=True)
async def tgd_help(bot: Bot, ev: Event):
    return await bot.send(HELP_TEXT)
