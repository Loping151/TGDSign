"""TGDSign 默认配置"""

from typing import Dict

from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsBoolConfig,
    GsIntConfig,
    GsListStrConfig,
)

CONIFG_DEFAULT: Dict[str, GSC] = {
    "SchedSignin": GsBoolConfig(
        "定时签到",
        "是否开启定时自动签到",
        False,
    ),
    "SigninMaster": GsBoolConfig(
        "全员签到",
        "开启后自动帮所有已登录用户签到",
        False,
    ),
    "SignTime": GsListStrConfig(
        "签到时间",
        "自动签到时间 [小时, 分钟]",
        ["8", "30"],
    ),
    "SigninConcurrentNum": GsIntConfig(
        "并发数",
        "自动签到并发数量，最大10",
        1,
        max_value=10,
    ),
    "PrivateSignReport": GsBoolConfig(
        "私聊推送签到结果",
        "是否私聊推送签到结果",
        False,
    ),
    "GroupSignReport": GsBoolConfig(
        "群聊推送签到结果",
        "是否群聊推送签到结果",
        False,
    ),
}
