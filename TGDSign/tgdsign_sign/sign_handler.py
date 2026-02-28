"""TGDSign 签到核心逻辑"""

import asyncio
import random
from collections import defaultdict
from typing import Dict, List, Optional

from gsuid_core.bot import Bot
from gsuid_core.gss import gss
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from gsuid_core.subscribe import gs_subscribe

from ..tgdsign_config import SIGN_RESULT_TYPE
from ..tgdsign_config.tgdsign_config import TGDSignConfig
from ..utils.api.requests import tgd_api
from ..utils.database.models import (
    TGDBind,
    TGDSignData,
    TGDSignRecord,
    TGDUser,
)


async def _do_sign_for_account(
    tgd_users: List[TGDUser],
) -> str:
    """对同一账号的所有角色执行签到, 返回结果消息"""
    primary = tgd_users[0]
    tgd_uid = primary.tgd_uid

    # 刷新 token (一个账号只刷新一次)
    res = await tgd_api.refresh_token(
        refresh_token=primary.cookie,
        device_id=primary.device_id,
    )
    if not res["status"]:
        display = primary.role_name or tgd_uid
        return f"[{display}] Token已过期: {res['message']}，请重新登录"

    access_token = res["data"]["accessToken"]
    new_refresh_token = res["data"]["refreshToken"]

    # 更新同账号所有记录的 cookie
    await TGDUser.update_cookie_by_tgd_uid(
        tgd_uid=tgd_uid, cookie=new_refresh_token
    )
    logger.debug(
        f"[TGDSign] token已刷新 tgd_uid={tgd_uid} "
        f"new_token={new_refresh_token[:8]}..."
    )

    msg_parts: list[str] = []

    # APP签到 (一个账号只签一次, 用第一条记录追踪)
    uid = primary.uid
    sign_record = await TGDSignRecord.get_sign_data(uid)
    if not sign_record or sign_record.app_sign < 1:
        res = await tgd_api.app_signin(
            access_token=access_token,
            uid=tgd_uid,
            device_id=primary.device_id,
        )
        if res["status"]:
            exp = res["data"].get("exp", 0)
            gold_coin = res["data"].get("goldCoin", 0)
            msg_parts.append(f"APP签到成功，获得{exp}经验，{gold_coin}金币")
            await TGDSignRecord.upsert_sign(TGDSignData.build_app_sign(uid))
        else:
            msg = res["message"]
            if "已经签到" in msg or "签到过" in msg or "重复签到" in msg:
                msg_parts.append("APP今日已签到")
                await TGDSignRecord.upsert_sign(
                    TGDSignData.build_app_sign(uid)
                )
            else:
                msg_parts.append(f"APP签到失败: {msg}")
    else:
        msg_parts.append("APP今日已签到")

    # 游戏签到 (每个角色)
    role_users = [u for u in tgd_users if u.uid != u.tgd_uid]
    if role_users:
        await asyncio.sleep(random.uniform(0.5, 1.5))

        signin_state = await tgd_api.get_signin_state(
            access_token=access_token
        )
        signin_rewards = await tgd_api.get_signin_rewards(
            access_token=access_token
        )

        for user in role_users:
            role_sign = await TGDSignRecord.get_sign_data(user.uid)
            rname = user.role_name or user.uid

            if role_sign and role_sign.game_sign >= 1:
                msg_parts.append(f"{rname} 今日已签到")
                continue

            res = await tgd_api.game_signin(
                access_token=access_token, role_id=user.uid
            )
            if res["status"]:
                reward_msg = "游戏签到成功"
                if signin_state["status"] and signin_rewards["status"]:
                    try:
                        days = signin_state["data"]["days"]
                        reward = signin_rewards["data"][days]
                        reward_msg = (
                            f"获得{reward['name']}*{reward['num']}"
                        )
                    except (KeyError, IndexError, TypeError):
                        pass
                msg_parts.append(f"{rname} {reward_msg}")
                await TGDSignRecord.upsert_sign(
                    TGDSignData.build_game_sign(user.uid)
                )
            else:
                msg = res["message"]
                if "已经签到" in msg or "签到过" in msg or "重复签到" in msg:
                    msg_parts.append(f"{rname} 今日已签到")
                    await TGDSignRecord.upsert_sign(
                        TGDSignData.build_game_sign(user.uid)
                    )
                else:
                    msg_parts.append(f"{rname} 游戏签到失败: {msg}")

            if len(role_users) > 1:
                await asyncio.sleep(random.uniform(0.3, 0.8))

    return "\n".join(msg_parts)


async def tgd_sign_handler(bot: Bot, ev: Event) -> str:
    """处理用户手动签到"""
    tgd_users: list[TGDUser] = []
    bind_data = await TGDBind.select_data(ev.user_id, ev.bot_id)
    if bind_data and bind_data.uid:
        uid_list = [u for u in bind_data.uid.split("_") if u]
        for uid in uid_list:
            user = await TGDUser.select_tgd_user(uid, ev.user_id, ev.bot_id)
            if user and user.cookie:
                tgd_users.append(user)

    if not tgd_users:
        tgd_users = await TGDUser.get_users_by_user_id(ev.user_id, ev.bot_id)

    if not tgd_users:
        return "[TGDSign] 未登录，请先使用 登录 命令"

    # 按 tgd_uid 分组, 同账号一起处理
    groups: Dict[str, List[TGDUser]] = defaultdict(list)
    for u in tgd_users:
        groups[u.tgd_uid].append(u)

    msg_list = []
    for users in groups.values():
        result = await _do_sign_for_account(users)
        msg_list.append(result)

    return (
        "\n-----------------------------\n".join(msg_list)
        if msg_list
        else "[TGDSign] 签到失败"
    )


async def tgd_auto_sign_task() -> str:
    """全部签到任务"""
    signin_master = TGDSignConfig.get_config("SigninMaster").data
    sched_signin = TGDSignConfig.get_config("SchedSignin").data

    if signin_master:
        user_list: List[TGDUser] = await TGDUser.get_all_tgd_user()
    elif sched_signin:
        user_list: List[TGDUser] = await TGDUser.get_sign_switch_on_users()
    else:
        return "[TGDSign] 自动签到未开启"

    if not user_list:
        return "[TGDSign] 暂无需要签到的账号"

    # 按 tgd_uid 分组
    groups: Dict[str, List[TGDUser]] = defaultdict(list)
    for u in user_list:
        if u.cookie:
            groups[u.tgd_uid].append(u)

    max_concurrent: int = TGDSignConfig.get_config("SigninConcurrentNum").data
    if max_concurrent > 10:
        max_concurrent = 10
    semaphore = asyncio.Semaphore(max_concurrent)

    success_count = 0
    fail_count = 0
    private_msgs: Dict[str, List[str]] = {}
    group_msgs: Dict[str, Dict] = {}

    async def _process_group(users: List[TGDUser]):
        nonlocal success_count, fail_count
        async with semaphore:
            try:
                await asyncio.sleep(random.random() * 1.5)

                result = await _do_sign_for_account(users)
                logger.info(
                    f"[TGDSign] 自动签到 tgd_uid "
                    f"{users[0].tgd_uid}: {result}"
                )

                is_success = "失败" not in result and "过期" not in result
                if is_success:
                    success_count += 1
                else:
                    fail_count += 1

                # 收集消息 (用第一条记录的 sign_switch)
                primary = users[0]
                gid = primary.sign_switch
                qid = primary.user_id

                if gid == "on":
                    if qid not in private_msgs:
                        private_msgs[qid] = []
                    private_msgs[qid].append(result)
                elif gid != "off":
                    if gid not in group_msgs:
                        group_msgs[gid] = {
                            "bot_id": primary.bot_id,
                            "success": 0,
                            "failed": 0,
                            "push_message": [],
                        }
                    if is_success:
                        group_msgs[gid]["success"] += 1
                    else:
                        group_msgs[gid]["failed"] += 1
                        group_msgs[gid]["push_message"].extend(
                            [
                                MessageSegment.text("\n"),
                                MessageSegment.at(qid),
                                MessageSegment.text(result),
                            ]
                        )

            except asyncio.TimeoutError:
                fail_count += 1
                logger.warning(
                    f"[TGDSign] 自动签到 tgd_uid "
                    f"{users[0].tgd_uid} 超时"
                )
            except Exception as e:
                fail_count += 1
                logger.error(
                    f"[TGDSign] 自动签到 tgd_uid "
                    f"{users[0].tgd_uid} 异常: {e}"
                )

    tasks = [_process_group(users) for users in groups.values()]
    await asyncio.gather(*tasks, return_exceptions=True)

    # 推送签到结果
    private_report = TGDSignConfig.get_config("PrivateSignReport").data
    group_report = TGDSignConfig.get_config("GroupSignReport").data

    for bot_id in gss.active_bot:
        bot = gss.active_bot[bot_id]

        # 私聊推送
        if private_report and private_msgs:
            for qid, msgs in private_msgs.items():
                try:
                    await bot.target_send(
                        "\n".join(msgs),
                        "direct", qid, "", "", "",
                    )
                except Exception as e:
                    logger.error(f"[TGDSign] 私聊推送失败 {qid}: {e}")
                await asyncio.sleep(random.uniform(0.5, 1.5))

        # 群聊推送
        if group_report and group_msgs:
            for gid, data in group_msgs.items():
                try:
                    msg_content = (
                        f"[塔吉多] 自动签到完成\n"
                        f"成功 {data['success']}，"
                        f"失败 {data['failed']}"
                    )
                    await bot.target_send(
                        msg_content,
                        "group", gid, data["bot_id"], "", "",
                    )
                except Exception as e:
                    logger.error(f"[TGDSign] 群聊推送失败 {gid}: {e}")
                await asyncio.sleep(random.uniform(0.5, 1.5))

    msg = (
        f"[塔吉多] 自动签到完成\n"
        f"成功 {success_count} 个账号，失败 {fail_count} 个账号"
    )

    # 通过订阅系统推送签到结果
    try:
        subscribes = await gs_subscribe.get_subscribe(SIGN_RESULT_TYPE)
        if subscribes:
            for sub in subscribes:
                try:
                    await sub.send(msg)
                except Exception as e:
                    logger.error(f"[TGDSign] 订阅推送失败: {e}")
    except Exception as e:
        logger.error(f"[TGDSign] 获取订阅列表失败: {e}")

    return msg
