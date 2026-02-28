"""TGDSign 签到核心逻辑"""

import asyncio
import random
from typing import Dict, List, Optional

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment

from ..tgdsign_config.tgdsign_config import TGDSignConfig
from ..utils.api.requests import tgd_api
from ..utils.database.models import (
    TGDBind,
    TGDSignData,
    TGDSignRecord,
    TGDUser,
)


async def _do_sign_single(
    tgd_user: TGDUser,
) -> str:
    """对单个用户执行签到, 返回结果消息"""
    uid = tgd_user.uid
    tgd_uid = tgd_user.tgd_uid
    role_name = tgd_user.role_name
    display_name = role_name or tgd_uid

    # 检查本地签到状态 (用 uid 查)
    sign_record = await TGDSignRecord.get_sign_data(uid)
    if sign_record and sign_record.app_sign >= 1 and sign_record.game_sign >= 1:
        return f"[{display_name}] 今日已签到，请勿重复签到"

    # 刷新 token
    res = await tgd_api.refresh_token(
        refresh_token=tgd_user.cookie,
        device_id=tgd_user.device_id,
    )
    if not res["status"]:
        return f"[{display_name}] Token已过期: {res['message']}，请重新登录"

    access_token = res["data"]["accessToken"]
    new_refresh_token = res["data"]["refreshToken"]

    # 更新 refresh_token
    await TGDUser.update_data_by_uid(
        uid=uid,
        bot_id=tgd_user.bot_id,
        cookie=new_refresh_token,
    )

    msg_parts = [f"[{display_name}] 签到结果"]

    # APP签到
    if not sign_record or sign_record.app_sign < 1:
        res = await tgd_api.app_signin(
            access_token=access_token,
            uid=tgd_uid,
            device_id=tgd_user.device_id,
        )
        if res["status"]:
            exp = res["data"].get("exp", 0)
            gold_coin = res["data"].get("goldCoin", 0)
            msg_parts.append(f"APP签到成功，获得{exp}经验，{gold_coin}金币")
            await TGDSignRecord.upsert_sign(TGDSignData.build_app_sign(uid))
        else:
            msg = res["message"]
            if "已经签到" in msg or "签到过" in msg:
                msg_parts.append("APP今日已签到")
                await TGDSignRecord.upsert_sign(TGDSignData.build_app_sign(uid))
            else:
                msg_parts.append(f"APP签到失败: {msg}")
    else:
        msg_parts.append("APP今日已签到")

    # 游戏签到（使用登录时存储的 role_id）
    has_role = bool(uid) and uid != tgd_uid
    if has_role:
        await asyncio.sleep(random.uniform(0.5, 1.5))

        signin_state = await tgd_api.get_signin_state(
            access_token=access_token
        )
        signin_rewards = await tgd_api.get_signin_rewards(
            access_token=access_token
        )

        if not sign_record or sign_record.game_sign < 1:
            res = await tgd_api.game_signin(
                access_token=access_token, role_id=uid
            )
            if res["status"]:
                reward_msg = "游戏签到成功"
                if (
                    signin_state["status"]
                    and signin_rewards["status"]
                ):
                    try:
                        days = signin_state["data"]["days"]
                        reward = signin_rewards["data"][days]
                        reward_msg = (
                            f"游戏签到成功，"
                            f"获得{reward['name']}*{reward['num']}"
                        )
                    except (KeyError, IndexError, TypeError):
                        pass
                msg_parts.append(reward_msg)
                await TGDSignRecord.upsert_sign(
                    TGDSignData.build_game_sign(uid)
                )
            else:
                msg = res["message"]
                if "已经签到" in msg or "签到过" in msg:
                    msg_parts.append("游戏今日已签到")
                    await TGDSignRecord.upsert_sign(
                        TGDSignData.build_game_sign(uid)
                    )
                else:
                    msg_parts.append(f"游戏签到失败: {msg}")
        else:
            msg_parts.append("游戏今日已签到")

    return "\n".join(msg_parts)


async def tgd_sign_handler(bot: Bot, ev: Event) -> str:
    """处理用户手动签到"""
    # 先尝试通过绑定数据查找
    tgd_users = []
    bind_data = await TGDBind.select_data(ev.user_id, ev.bot_id)
    if bind_data and bind_data.uid:
        uid_list = [u for u in bind_data.uid.split("_") if u]
        for uid in uid_list:
            user = await TGDUser.select_tgd_user(uid, ev.user_id, ev.bot_id)
            if user and user.cookie:
                tgd_users.append(user)

    # 没有绑定角色的用户，直接通过 user_id 查找
    if not tgd_users:
        tgd_users = await TGDUser.get_users_by_user_id(ev.user_id, ev.bot_id)

    if not tgd_users:
        return "[TGDSign] 未登录，请先使用 登录 命令"

    msg_list = []
    for tgd_user in tgd_users:
        result = await _do_sign_single(tgd_user)
        msg_list.append(result)

        if len(tgd_users) > 1:
            await asyncio.sleep(random.uniform(1, 2))

    return "\n-----------------------------\n".join(msg_list) if msg_list else "[TGDSign] 签到失败"


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

    max_concurrent: int = TGDSignConfig.get_config("SigninConcurrentNum").data
    if max_concurrent > 10:
        max_concurrent = 10
    semaphore = asyncio.Semaphore(max_concurrent)

    success_count = 0
    fail_count = 0
    private_msgs: Dict[str, List[str]] = {}
    group_msgs: Dict[str, Dict] = {}

    async def _process_user(user: TGDUser):
        nonlocal success_count, fail_count
        async with semaphore:
            try:
                await asyncio.sleep(random.random() * 1.5)

                if not user.cookie:
                    return

                result = await _do_sign_single(user)
                logger.info(f"[TGDSign] 自动签到 UID {user.uid}: {result}")

                is_success = "失败" not in result and "过期" not in result
                if is_success:
                    success_count += 1
                else:
                    fail_count += 1

                # 收集消息
                gid = user.sign_switch
                qid = user.user_id

                if gid == "on":
                    if qid not in private_msgs:
                        private_msgs[qid] = []
                    private_msgs[qid].append(result)
                elif gid != "off":
                    if gid not in group_msgs:
                        group_msgs[gid] = {
                            "bot_id": user.bot_id,
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
                    f"[TGDSign] 自动签到 UID {user.uid} 超时"
                )
            except Exception as e:
                fail_count += 1
                logger.error(
                    f"[TGDSign] 自动签到 UID {user.uid} 异常: {e}"
                )

    tasks = [_process_user(user) for user in user_list]
    await asyncio.gather(*tasks, return_exceptions=True)

    msg = f"[塔吉多] 自动签到完成\n成功 {success_count} 个账号，失败 {fail_count} 个账号"
    return msg
