"""塔吉多 API 请求封装"""

import time
import traceback
import urllib.parse as qs
from typing import Optional

import httpx
from gsuid_core.logger import logger

from .api import (
    APPID,
    APPVERSION,
    AREACODEID,
    BID,
    CHANNELID,
    COMMUNITYID,
    DEVICEMODEL,
    DEVICENAME,
    DEVICESYS,
    DEVICETYPE,
    GAMEID,
    REQUEST_HEADERS_BASE,
    SDKVERSION,
    TYPE,
    USERCENTERAPPID,
    VERSIONCODE,
    SENDCAPTCHA,
    CHECKCAPTCHA,
    LOGIN,
    USERCENTERLOGIN,
    REFRESHTOKEN,
    GETBINDROLE,
    APPSIGNIN,
    GAMESIGNIN,
    GETSIGNINSTATE,
    GETSIGNINREWARDS,
    GETGAMEROLES,
)
from .calculate import aes_base64_encode, generate_sign


def _get_proxy() -> Optional[str]:
    from ...tgdsign_config.tgdsign_config import TGDSignConfig

    proxy = TGDSignConfig.get_config("LocalProxyUrl").data
    return proxy if proxy else None


class TaygedoApi:
    def _get_client(self) -> httpx.AsyncClient:
        proxy = _get_proxy()
        return httpx.AsyncClient(timeout=200, proxy=proxy)

    async def send_captcha(self, phone: str, device_id: str):
        data = {
            "deviceType": DEVICETYPE,
            "type": TYPE,
            "deviceId": device_id,
            "deviceName": DEVICENAME,
            "versionCode": VERSIONCODE,
            "t": str(int(time.time())),
            "areaCodeId": AREACODEID,
            "appId": APPID,
            "deviceSys": DEVICESYS,
            "cellphone": phone,
            "deviceModel": DEVICEMODEL,
            "sdkVersion": SDKVERSION,
            "bid": BID,
            "channelId": CHANNELID,
        }
        data["sign"] = generate_sign(data)
        payload = qs.urlencode(data)
        headers = {**REQUEST_HEADERS_BASE}

        try:
            async with self._get_client() as client:
                response = await client.post(
                    SENDCAPTCHA, content=payload, headers=headers
                )
            resp = response.json()
            logger.debug(f"[TGDSign] 发送验证码响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("message") == "手机短信发送成功"
            ):
                return {"status": True, "message": resp["message"]}
            else:
                logger.error(f"[TGDSign] 发送验证码失败: {resp}")
                return {"status": False, "message": resp.get("message", "未知错误")}
        except Exception as e:
            logger.error(f"[TGDSign] 发送验证码异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "发送验证码失败，详情请查看日志"}

    async def check_captcha(self, phone: str, captcha: str, device_id: str):
        data = {
            "deviceType": DEVICETYPE,
            "deviceId": device_id,
            "deviceName": DEVICENAME,
            "versionCode": VERSIONCODE,
            "t": str(int(time.time())),
            "captcha": captcha,
            "appId": APPID,
            "deviceSys": DEVICESYS,
            "cellphone": phone,
            "deviceModel": DEVICEMODEL,
            "sdkVersion": SDKVERSION,
            "bid": BID,
            "channelId": CHANNELID,
        }
        data["sign"] = generate_sign(data)
        payload = qs.urlencode(data)
        headers = {**REQUEST_HEADERS_BASE}

        try:
            async with self._get_client() as client:
                response = await client.post(
                    CHECKCAPTCHA, content=payload, headers=headers
                )
            resp = response.json()
            logger.debug(f"[TGDSign] 验证验证码响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("message") == "手机验证码正确"
            ):
                return {"status": True, "message": resp["message"]}
            else:
                logger.error(f"[TGDSign] 验证验证码失败: {resp}")
                msg = resp.get("message", "未知错误")
                if "短信正在发送" in msg:
                    msg = "短信正在发送，请等待几分钟后再试"
                return {"status": False, "message": msg}
        except Exception as e:
            logger.error(f"[TGDSign] 验证验证码异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "验证验证码失败，详情请查看日志"}

    async def login(self, phone: str, captcha: str, device_id: str):
        enc_phone = aes_base64_encode(phone)
        enc_captcha = aes_base64_encode(captcha)
        data = {
            "deviceType": DEVICETYPE,
            "idfa": "",
            "sign": "",
            "adm": "",
            "type": TYPE,
            "deviceId": device_id,
            "version": VERSIONCODE,
            "deviceName": DEVICENAME,
            "mac": "",
            "t": str(int(time.time() * 1000)),
            "areaCodeId": AREACODEID,
            "captcha": enc_captcha,
            "appId": APPID,
            "deviceSys": DEVICESYS,
            "cellphone": enc_phone,
            "deviceModel": DEVICEMODEL,
            "sdkVersion": SDKVERSION,
            "bid": BID,
            "channelId": CHANNELID,
        }
        data["sign"] = generate_sign(data)
        payload = qs.urlencode(data)
        headers = {**REQUEST_HEADERS_BASE}

        try:
            async with self._get_client() as client:
                response = await client.post(
                    LOGIN, content=payload, headers=headers
                )
            resp = response.json()
            logger.debug(f"[TGDSign] 登录响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("message") == "登陆成功"
            ):
                return {
                    "status": True,
                    "message": resp["message"],
                    "result": resp["result"],
                }
            else:
                logger.error(f"[TGDSign] 登录失败: {resp}")
                return {"status": False, "message": resp.get("message", "登录失败")}
        except Exception as e:
            logger.error(f"[TGDSign] 登录异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "登录失败，详情请查看日志"}

    async def user_center_login(self, token: str, user_id: str, device_id: str):
        data = {
            "token": token,
            "userIdentity": user_id,
            "appId": USERCENTERAPPID,
        }
        payload = qs.urlencode(data)
        headers = {
            **REQUEST_HEADERS_BASE,
            "deviceid": device_id,
            "authorization": "",
            "appversion": APPVERSION,
            "uid": "10100300",
            "User-Agent": "okhttp/4.12.0",
        }

        try:
            async with self._get_client() as client:
                response = await client.post(
                    USERCENTERLOGIN, content=payload, headers=headers
                )
            resp = response.json()
            logger.debug(f"[TGDSign] 用户中心登录响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("msg") == "ok"
            ):
                return {
                    "status": True,
                    "message": resp["msg"],
                    "data": resp["data"],
                }
            else:
                logger.error(f"[TGDSign] 用户中心登录失败: {resp}")
                return {"status": False, "message": resp.get("msg", "用户中心登录失败")}
        except Exception as e:
            logger.error(f"[TGDSign] 用户中心登录异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "用户中心登录失败，详情请查看日志"}

    async def refresh_token(self, refresh_token: str, device_id: str):
        headers = {
            **REQUEST_HEADERS_BASE,
            "deviceid": device_id,
            "authorization": refresh_token,
            "appversion": APPVERSION,
            "uid": "10100300",
            "User-Agent": "okhttp/4.12.0",
        }

        try:
            async with self._get_client() as client:
                response = await client.post(REFRESHTOKEN, headers=headers)
            resp = response.json()
            logger.debug(f"[TGDSign] 刷新token响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("msg") == "ok"
            ):
                return {
                    "status": True,
                    "message": resp["msg"],
                    "data": resp["data"],
                }
            else:
                logger.error(f"[TGDSign] 刷新token失败: {resp}")
                return {"status": False, "message": resp.get("msg", "刷新token失败")}
        except Exception as e:
            logger.error(f"[TGDSign] 刷新token异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "刷新token失败，详情请查看日志"}

    async def get_bind_role(self, access_token: str, uid: str):
        headers = {"Authorization": access_token}

        try:
            async with self._get_client() as client:
                response = await client.get(
                    GETBINDROLE,
                    headers=headers,
                    params={"uid": uid, "gameId": GAMEID},
                )
            resp = response.json()
            logger.info(f"[TGDSign] 获取绑定角色响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("msg") == "ok"
            ):
                return {
                    "status": True,
                    "message": resp["msg"],
                    "data": resp.get("data") or {},
                }
            else:
                logger.error(f"[TGDSign] 获取绑定角色失败: {resp}")
                return {
                    "status": False,
                    "message": resp.get("msg", "获取绑定角色失败"),
                }
        except Exception as e:
            logger.error(f"[TGDSign] 获取绑定角色异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "获取绑定角色失败，详情请查看日志"}

    async def get_game_roles(self, access_token: str, uid: str, device_id: str):
        """获取用户所有游戏角色列表"""
        headers = {
            "platform": "android",
            "authorization": access_token,
            "uid": uid,
            "deviceid": device_id,
            "appversion": APPVERSION,
            "User-Agent": "okhttp/4.12.0",
        }

        try:
            async with self._get_client() as client:
                response = await client.post(
                    GETGAMEROLES,
                    headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                    content=qs.urlencode({"gameId": GAMEID}),
                )
            resp = response.json()
            logger.info(f"[TGDSign] 获取游戏角色列表响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
            ):
                return {
                    "status": True,
                    "message": resp.get("msg", "ok"),
                    "data": resp.get("data") or [],
                }
            else:
                logger.error(f"[TGDSign] 获取游戏角色列表失败: {resp}")
                return {
                    "status": False,
                    "message": resp.get("msg", "获取游戏角色列表失败"),
                }
        except Exception as e:
            logger.error(f"[TGDSign] 获取游戏角色列表异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "获取游戏角色列表失败，详情请查看日志"}

    async def app_signin(self, access_token: str, uid: str, device_id: str):
        data = {"communityId": COMMUNITYID}
        payload = qs.urlencode(data)
        headers = {
            **REQUEST_HEADERS_BASE,
            "authorization": access_token,
            "uid": uid,
            "deviceid": device_id,
            "appversion": APPVERSION,
            "User-Agent": "okhttp/4.12.0",
        }

        try:
            async with self._get_client() as client:
                response = await client.post(
                    APPSIGNIN, content=payload, headers=headers
                )
            resp = response.json()
            logger.debug(f"[TGDSign] APP签到响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("msg") == "ok"
            ):
                return {
                    "status": True,
                    "message": resp["msg"],
                    "data": resp["data"],
                }
            else:
                msg = resp.get("msg", "APP签到失败")
                if "签到" in msg:
                    logger.debug(f"[TGDSign] APP签到: {resp}")
                else:
                    logger.error(f"[TGDSign] APP签到失败: {resp}")
                return {"status": False, "message": msg}
        except Exception as e:
            logger.error(f"[TGDSign] APP签到异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "APP签到失败，详情请查看日志"}

    async def game_signin(self, access_token: str, role_id: str):
        data = {"roleId": role_id, "gameId": GAMEID}
        payload = qs.urlencode(data)
        headers = {**REQUEST_HEADERS_BASE, "authorization": access_token}

        try:
            async with self._get_client() as client:
                response = await client.post(
                    GAMESIGNIN, content=payload, headers=headers
                )
            resp = response.json()
            logger.debug(f"[TGDSign] 游戏签到响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("msg") == "ok"
            ):
                return {"status": True, "message": resp["msg"]}
            else:
                msg = resp.get("msg", "游戏签到失败")
                if "签到" in msg:
                    logger.debug(f"[TGDSign] 游戏签到: {resp}")
                else:
                    logger.error(f"[TGDSign] 游戏签到失败: {resp}")
                return {"status": False, "message": msg}
        except Exception as e:
            logger.error(f"[TGDSign] 游戏签到异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "游戏签到失败，详情请查看日志"}

    async def get_signin_state(self, access_token: str):
        headers = {"Authorization": access_token}

        try:
            async with self._get_client() as client:
                response = await client.get(
                    GETSIGNINSTATE,
                    headers=headers,
                    params={"gameId": GAMEID},
                )
            resp = response.json()
            logger.debug(f"[TGDSign] 获取签到状态响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("msg") == "ok"
            ):
                return {
                    "status": True,
                    "message": resp["msg"],
                    "data": resp["data"],
                }
            else:
                logger.error(f"[TGDSign] 获取签到状态失败: {resp}")
                return {
                    "status": False,
                    "message": resp.get("msg", "获取签到状态失败"),
                }
        except Exception as e:
            logger.error(f"[TGDSign] 获取签到状态异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "获取签到状态失败，详情请查看日志"}

    async def get_signin_rewards(self, access_token: str):
        headers = {"Authorization": access_token}

        try:
            async with self._get_client() as client:
                response = await client.get(
                    GETSIGNINREWARDS,
                    headers=headers,
                    params={"gameId": GAMEID},
                )
            resp = response.json()
            logger.debug(f"[TGDSign] 获取签到奖励响应: {resp}")
            if (
                response.status_code == 200
                and resp.get("code") == 0
                and resp.get("msg") == "ok"
            ):
                return {
                    "status": True,
                    "message": resp["msg"],
                    "data": resp["data"],
                }
            else:
                logger.error(f"[TGDSign] 获取签到奖励失败: {resp}")
                return {
                    "status": False,
                    "message": resp.get("msg", "获取签到奖励失败"),
                }
        except Exception as e:
            logger.error(f"[TGDSign] 获取签到奖励异常: {e}")
            logger.error(traceback.format_exc())
            return {"status": False, "message": "获取签到奖励失败，详情请查看日志"}


tgd_api = TaygedoApi()
