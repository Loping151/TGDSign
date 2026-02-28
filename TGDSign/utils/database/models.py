"""TGDSign 数据库模型"""

from typing import Any, Dict, List, Type, TypeVar, Optional
from datetime import datetime

from sqlmodel import Field, select
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel as PydanticBaseModel
from gsuid_core.utils.database.base_models import (
    Bind,
    User,
    BaseIDModel,
    with_session,
)
from gsuid_core.utils.database.startup import exec_list
from gsuid_core.webconsole.mount_app import PageSchema, GsAdminModel, site

exec_list.extend(
    [
        'ALTER TABLE TGDUser ADD COLUMN game_id TEXT DEFAULT "1256"',
    ]
)

T_TGDBind = TypeVar("T_TGDBind", bound="TGDBind")
T_TGDUser = TypeVar("T_TGDUser", bound="TGDUser")
T_TGDSignRecord = TypeVar("T_TGDSignRecord", bound="TGDSignRecord")


def get_today_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class TGDBind(Bind, table=True):
    __table_args__: Dict[str, Any] = {"extend_existing": True}
    uid: Optional[str] = Field(default=None, title="塔吉多角色ID")


class TGDUser(User, table=True):
    __table_args__: Dict[str, Any] = {"extend_existing": True}
    cookie: str = Field(default="", title="RefreshToken")
    uid: str = Field(default="", title="塔吉多角色ID")
    tgd_uid: str = Field(default="", title="塔吉多UID")
    device_id: str = Field(default="", title="设备ID")
    role_name: str = Field(default="", title="角色名")
    game_id: str = Field(default="1256", title="游戏ID")

    @classmethod
    @with_session
    async def select_tgd_user(
        cls: Type[T_TGDUser],
        session: AsyncSession,
        uid: str,
        user_id: str,
        bot_id: str,
    ) -> Optional[T_TGDUser]:
        sql = select(cls).where(
            cls.user_id == user_id,
            cls.uid == uid,
            cls.bot_id == bot_id,
        )
        result = await session.execute(sql)
        data = result.scalars().all()
        return data[0] if data else None

    @classmethod
    @with_session
    async def select_tgd_user_by_uid(
        cls: Type[T_TGDUser],
        session: AsyncSession,
        uid: str,
    ) -> Optional[T_TGDUser]:
        sql = select(cls).where(cls.uid == uid)
        result = await session.execute(sql)
        data = result.scalars().all()
        return data[0] if data else None

    @classmethod
    @with_session
    async def get_users_by_user_id(
        cls: Type[T_TGDUser],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
    ) -> List[T_TGDUser]:
        """通过 user_id 和 bot_id 获取所有 TGDUser"""
        sql = (
            select(cls)
            .where(cls.user_id == user_id)
            .where(cls.bot_id == bot_id)
            .where(cls.cookie != "")
        )
        result = await session.execute(sql)
        return list(result.scalars().all())

    @classmethod
    @with_session
    async def get_all_tgd_user(
        cls: Type[T_TGDUser],
        session: AsyncSession,
    ) -> List[T_TGDUser]:
        """获取所有有 refresh_token 的用户"""
        sql = (
            select(cls)
            .where(cls.cookie != "")
            .where(cls.user_id != "")
        )
        result = await session.execute(sql)
        return list(result.scalars().all())

    @classmethod
    @with_session
    async def get_sign_switch_on_users(
        cls: Type[T_TGDUser],
        session: AsyncSession,
    ) -> List[T_TGDUser]:
        """获取开启自动签到的用户"""
        sql = (
            select(cls)
            .where(cls.cookie != "")
            .where(cls.user_id != "")
            .where(cls.sign_switch != "off")
        )
        result = await session.execute(sql)
        return list(result.scalars().all())


class TGDSignData(PydanticBaseModel):
    uid: str
    date: Optional[str] = None
    app_sign: Optional[int] = None
    game_sign: Optional[int] = None

    @classmethod
    def build(cls, uid: str):
        return cls(uid=uid, date=get_today_date())

    @classmethod
    def build_app_sign(cls, uid: str):
        return cls(uid=uid, app_sign=1)

    @classmethod
    def build_game_sign(cls, uid: str):
        return cls(uid=uid, game_sign=1)

    @classmethod
    def build_all_sign(cls, uid: str):
        return cls(uid=uid, app_sign=1, game_sign=1)


class TGDSignRecord(BaseIDModel, table=True):
    __table_args__: Dict[str, Any] = {"extend_existing": True}
    uid: str = Field(title="塔吉多角色ID")
    app_sign: int = Field(default=0, title="APP签到")
    game_sign: int = Field(default=0, title="游戏签到")
    date: str = Field(default_factory=get_today_date, title="签到日期")

    @classmethod
    async def _find_sign_record(
        cls: Type[T_TGDSignRecord],
        session: AsyncSession,
        uid: str,
        date: str,
    ) -> Optional[T_TGDSignRecord]:
        query = select(cls).where(cls.uid == uid).where(cls.date == date)
        result = await session.execute(query)
        return result.scalars().first()

    @classmethod
    @with_session
    async def upsert_sign(
        cls: Type[T_TGDSignRecord],
        session: AsyncSession,
        sign_data: TGDSignData,
    ) -> Optional[T_TGDSignRecord]:
        if not sign_data.uid:
            return None

        sign_data.date = sign_data.date or get_today_date()

        record = await cls._find_sign_record(session, sign_data.uid, sign_data.date)

        if record:
            for field in ["app_sign", "game_sign"]:
                value = getattr(sign_data, field)
                if value is not None:
                    setattr(record, field, value)
            result = record
        else:
            result = cls(**sign_data.model_dump())
            session.add(result)

        return result

    @classmethod
    @with_session
    async def get_sign_data(
        cls: Type[T_TGDSignRecord],
        session: AsyncSession,
        uid: str,
        date: Optional[str] = None,
    ) -> Optional[T_TGDSignRecord]:
        date = date or get_today_date()
        return await cls._find_sign_record(session, uid, date)

    @classmethod
    @with_session
    async def get_all_sign_data_by_date(
        cls: Type[T_TGDSignRecord],
        session: AsyncSession,
        date: Optional[str] = None,
    ) -> List[T_TGDSignRecord]:
        actual_date = date or get_today_date()
        sql = select(cls).where(cls.date == actual_date)
        result = await session.execute(sql)
        return list(result.scalars().all())

    @classmethod
    @with_session
    async def clear_sign_record(
        cls: Type[T_TGDSignRecord],
        session: AsyncSession,
        date: str,
    ):
        sql = delete(cls).where(cls.date <= date)
        await session.execute(sql)

    @classmethod
    def is_all_complete(cls, record: Optional["TGDSignRecord"]) -> bool:
        if not record:
            return False
        return record.app_sign >= 1 and record.game_sign >= 1


@site.register_admin
class TGDBindAdmin(GsAdminModel):
    pk_name = "id"
    page_schema = PageSchema(
        label="塔吉多绑定管理",
        icon="fa fa-users",
    )
    model = TGDBind


@site.register_admin
class TGDUserAdmin(GsAdminModel):
    pk_name = "id"
    page_schema = PageSchema(
        label="塔吉多用户管理",
        icon="fa fa-user",
    )
    model = TGDUser
