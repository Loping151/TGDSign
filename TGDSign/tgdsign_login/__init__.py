"""TGDSign 网页登录"""

import asyncio
import hashlib
from pathlib import Path

from pydantic import BaseModel
from starlette.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from gsuid_core.bot import Bot
from gsuid_core.config import core_config
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV
from gsuid_core.web_app import app

from ..tgdsign_config.tgdsign_config import TGDSignConfig
from ..utils.cache import TimedCache
from ..utils.api.api import GAMEID
from ..utils.api.calculate import get_random_device_id
from ..utils.api.requests import tgd_api
from ..utils.database.models import TGDBind, TGDUser

sv_tgd_login = SV("TGDSign-登录", priority=1)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

cache = TimedCache(timeout=180, maxsize=10)


def _get_token(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:8]


async def _get_server_url() -> tuple[str, bool]:
    url = TGDSignConfig.get_config("LoginUrl").data
    if url:
        if not url.startswith("http"):
            url = f"https://{url}"
        return url, TGDSignConfig.get_config("LoginUrlSelf").data
    HOST = core_config.get_config("HOST")
    PORT = core_config.get_config("PORT")
    if HOST == "localhost" or HOST == "127.0.0.1":
        _host = "localhost"
    else:
        _host = HOST
    return f"http://{_host}:{PORT}", True


@sv_tgd_login.on_fullmatch(("登录", "登陆", "login"), block=True)
async def tgd_login(bot: Bot, ev: Event):
    await page_login(bot, ev)


async def page_login(bot: Bot, ev: Event):
    at_sender = True if ev.group_id else False
    user_token = _get_token(ev.user_id)
    url, _ = await _get_server_url()

    # 检查是否已有登录进行中
    existing = cache.get(user_token)
    if isinstance(existing, dict):
        await bot.send(
            f"[TGDSign] 登录链接已发送，请在浏览器中完成操作\n{url}/tgd/i/{user_token}",
            at_sender=at_sender,
        )
        return

    # 初始化缓存
    data = {"mobile": -1, "code": -1, "user_id": ev.user_id}
    cache.set(user_token, data)

    login_url = f"{url}/tgd/i/{user_token}"
    await bot.send(
        f"[TGDSign] 请在浏览器中打开以下链接完成登录\n{login_url}\n3分钟内有效",
        at_sender=at_sender,
    )

    # 轮询等待用户在网页完成登录
    try:
        for _ in range(180):
            result = cache.get(user_token)
            if result is None:
                return await bot.send(
                    "[TGDSign] 登录超时！",
                    at_sender=at_sender,
                )
            if result.get("mobile") != -1 and result.get("code") != -1:
                cache.delete(user_token)
                break
            await asyncio.sleep(1)
        else:
            cache.delete(user_token)
            return await bot.send(
                "[TGDSign] 登录超时！",
                at_sender=at_sender,
            )
    except Exception as e:
        logger.error(f"[TGDSign] 登录轮询异常: {e}")
        cache.delete(user_token)
        return await bot.send(
            "[TGDSign] 登录异常，请重新发送登录指令",
            at_sender=at_sender,
        )

    # 执行登录流程
    phone = result["mobile"]
    code = result["code"]
    device_id = result.get("device_id", get_random_device_id())

    # 验证验证码
    res = await tgd_api.check_captcha(
        phone=phone, captcha=code, device_id=device_id
    )
    if not res["status"]:
        return await bot.send(
            f"[TGDSign] 验证码验证失败: {res['message']}，请重新登录",
            at_sender=at_sender,
        )

    # 登录
    res = await tgd_api.login(phone=phone, captcha=code, device_id=device_id)
    if not res["status"]:
        return await bot.send(
            f"[TGDSign] 登录失败: {res['message']}，请重新登录",
            at_sender=at_sender,
        )

    token = res["result"]["token"]
    user_id_str = str(res["result"]["userId"])

    # 用户中心登录
    res = await tgd_api.user_center_login(
        token=token, user_id=user_id_str, device_id=device_id
    )
    if not res["status"]:
        return await bot.send(
            f"[TGDSign] 用户中心登录失败: {res['message']}，请重新登录",
            at_sender=at_sender,
        )

    access_token = res["data"]["accessToken"]
    refresh_token = res["data"]["refreshToken"]
    tgd_uid = str(res["data"]["uid"])

    # 获取绑定角色（可选）
    role_id = ""
    role_name = ""
    game_id = GAMEID
    res = await tgd_api.get_bind_role(access_token=access_token, uid=tgd_uid)
    if res["status"] and "roleId" in res.get("data", {}):
        role_id = str(res["data"]["roleId"])
        role_name = res["data"].get("roleName", role_id)
        game_id = str(res["data"].get("gameId", GAMEID))
    else:
        # getGameBindRole 未返回角色，尝试 getGameRoles
        roles_res = await tgd_api.get_game_roles(
            access_token=access_token, uid=tgd_uid, device_id=device_id
        )
        if roles_res["status"] and roles_res.get("data"):
            roles = roles_res["data"].get("roles", []) if isinstance(roles_res["data"], dict) else []
            for r in roles:
                if str(r.get("gameId", "")) == GAMEID:
                    role_id = str(r.get("roleId", ""))
                    role_name = r.get("roleName", role_id)
                    game_id = str(r.get("gameId", GAMEID))
                    break
            if not role_id and roles:
                r = roles[0]
                role_id = str(r.get("roleId", ""))
                role_name = r.get("roleName", role_id)
                game_id = str(r.get("gameId", GAMEID))

    # 没有绑定角色时用 tgd_uid 作为 uid
    store_uid = role_id if role_id else tgd_uid

    # 保存绑定数据
    await TGDBind.insert_uid(
        ev.user_id, ev.bot_id, store_uid, ev.group_id, is_digit=False
    )

    # 保存用户数据
    await TGDUser.insert_data(
        ev.user_id,
        ev.bot_id,
        cookie=refresh_token,
        uid=store_uid,
        tgd_uid=tgd_uid,
        device_id=device_id,
        role_name=role_name,
        game_id=game_id,
        sign_switch="off",
    )

    display_name = role_name or tgd_uid
    logger.info(
        f"[TGDSign] 用户 {ev.user_id} 登录成功: "
        f"tgd_uid={tgd_uid}, role_name={role_name}, role_id={role_id}"
    )

    # 登录后立即签到
    from ..utils.database.models import TGDSignData, TGDSignRecord

    sign_msgs = [f"[TGDSign] {display_name} 登录成功"]

    # APP签到
    res = await tgd_api.app_signin(
        access_token=access_token, uid=tgd_uid, device_id=device_id
    )
    if res["status"]:
        exp = res["data"].get("exp", 0)
        gold_coin = res["data"].get("goldCoin", 0)
        sign_msgs.append(f"APP签到成功，获得{exp}经验，{gold_coin}金币")
        await TGDSignRecord.upsert_sign(TGDSignData.build_app_sign(store_uid))
    else:
        msg = res["message"]
        if "已经签到" in msg or "签到过" in msg:
            sign_msgs.append("APP今日已签到")
            await TGDSignRecord.upsert_sign(TGDSignData.build_app_sign(store_uid))
        else:
            sign_msgs.append(f"APP签到失败: {msg}")

    # 游戏签到（仅在绑定角色时）
    if role_id:
        signin_state = await tgd_api.get_signin_state(access_token=access_token)
        signin_rewards = await tgd_api.get_signin_rewards(
            access_token=access_token
        )

        res = await tgd_api.game_signin(
            access_token=access_token, role_id=role_id
        )
        if res["status"]:
            reward_msg = "游戏签到成功"
            if signin_state["status"] and signin_rewards["status"]:
                try:
                    days = signin_state["data"]["days"]
                    reward = signin_rewards["data"][days]
                    reward_msg = (
                        f"游戏签到成功，获得{reward['name']}*{reward['num']}"
                    )
                except (KeyError, IndexError, TypeError):
                    pass
            sign_msgs.append(reward_msg)
            await TGDSignRecord.upsert_sign(
                TGDSignData.build_game_sign(role_id)
            )
        else:
            msg = res["message"]
            if "已经签到" in msg or "签到过" in msg:
                sign_msgs.append("游戏今日已签到")
                await TGDSignRecord.upsert_sign(
                    TGDSignData.build_game_sign(role_id)
                )
            else:
                sign_msgs.append(f"游戏签到失败: {msg}")

    sign_msgs.append("发 tgd开启自动签到 以开启每日自动签到")
    return await bot.send("\n".join(sign_msgs), at_sender=at_sender)


# ===== FastAPI 路由 =====


@app.get("/tgd/i/{auth}")
async def tgd_login_page(auth: str):
    temp = cache.get(auth)
    if temp is None:
        template = _jinja_env.get_template("404.html")
        return HTMLResponse(template.render())

    url, _ = await _get_server_url()
    template = _jinja_env.get_template("index.html")
    return HTMLResponse(
        template.render(
            server_url=url,
            auth=auth,
            userId=temp.get("user_id", ""),
        )
    )


class SendCodeModel(BaseModel):
    auth: str
    phone: str


@app.post("/tgd/sendcode")
async def tgd_sendcode(data: SendCodeModel):
    temp = cache.get(data.auth)
    if temp is None:
        return {"success": False, "msg": "链接已过期，请重新发送登录指令"}

    device_id = temp.get("device_id")
    if not device_id:
        device_id = get_random_device_id()
        temp["device_id"] = device_id
        cache.set(data.auth, temp)

    res = await tgd_api.send_captcha(phone=data.phone, device_id=device_id)
    if res["status"]:
        return {"success": True, "msg": "验证码已发送"}
    else:
        return {"success": False, "msg": res["message"]}


class LoginModel(BaseModel):
    auth: str
    mobile: str
    code: str


@app.post("/tgd/login")
async def tgd_web_login(data: LoginModel):
    temp = cache.get(data.auth)
    if temp is None:
        return {"success": False, "msg": "链接已过期，请重新发送登录指令"}

    temp["mobile"] = data.mobile
    temp["code"] = data.code
    cache.set(data.auth, temp)
    return {"success": True, "msg": "登录中，请返回聊天查看结果"}
