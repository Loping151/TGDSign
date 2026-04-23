"""塔吉多 API 常量"""

DEVICETYPE = "LGE-AN10"
TYPE = "16"
DEVICENAME = "LGE-AN10"
VERSIONCODE = "1"
AREACODEID = "1"
APPID = "10550"
USERCENTERAPPID = "10551"
DEVICESYS = "12"
DEVICEMODEL = "LGE-AN10"
SDKVERSION = "4.129.0"
BID = "com.pwrd.htassistant"
CHANNELID = "1"
GAMEID_HT = "1256"
GAMEID_NTE = "1257"
ALL_GAME_IDS = [GAMEID_HT, GAMEID_NTE]
COMMUNITYID = "1"
APPVERSION = "1.1.0"

# API 地址
SENDCAPTCHA = "https://user.laohu.com/m/newApi/sendPhoneCaptchaWithOutLogin"
CHECKCAPTCHA = "https://user.laohu.com/m/newApi/checkPhoneCaptchaWithOutLogin"
LOGIN = "https://user.laohu.com/openApi/sms/new/login"
USERCENTERLOGIN = "https://bbs-api.tajiduo.com/usercenter/api/login"
REFRESHTOKEN = "https://bbs-api.tajiduo.com/usercenter/api/refreshToken"
GETBINDROLE = "https://bbs-api.tajiduo.com/apihub/api/getGameBindRole"
APPSIGNIN = "https://bbs-api.tajiduo.com/apihub/api/signin"
GAMESIGNIN = "https://bbs-api.tajiduo.com/apihub/awapi/sign"
GETSIGNINSTATE = "https://bbs-api.tajiduo.com/apihub/awapi/signin/state"
GETSIGNINREWARDS = "https://bbs-api.tajiduo.com/apihub/awapi/sign/rewards"
GETGAMEROLES = "https://bbs-api.tajiduo.com/usercenter/api/v2/getGameRoles"

# 论坛公告接口（无需鉴权）
GETUSERPOSTLIST = "https://bbs-api.tajiduo.com/bbs/wapi/getUserPostList"
GETPOSTFULL = "https://bbs-api.tajiduo.com/bbs/wapi/getPostFull"

# 异环官方公告账号 UID
YIHUAN_OFFICIAL_UID = "10100006"

REQUEST_HEADERS_BASE = {
    "platform": "android",
    "Content-Type": "application/x-www-form-urlencoded",
}

WEB_HEADERS_BASE = {
    "referer": "https://www.tajiduo.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
}
