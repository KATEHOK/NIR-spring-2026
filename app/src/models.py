from datetime import datetime
from typing import Annotated
from sqlalchemy import ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


timezone_utc_now = text("TIMEZONE('utc', now())")

intpk = Annotated[int, mapped_column(primary_key=True)]

created_at = Annotated[
    datetime,
    mapped_column(server_default=timezone_utc_now)
]
updated_at = Annotated[
    datetime,
    mapped_column(
        server_default=timezone_utc_now,
        server_onupdate=timezone_utc_now
    )
]


class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[intpk]
    password: Mapped[bytes] = mapped_column(nullable=False)             # хэшируем на секретном ключе приложения

    challenge: Mapped[bytes | None] = mapped_column(nullable=True)      # шифруем секретным ключом приложения
    key: Mapped[bytes] = mapped_column(nullable=False)                  # шифруем секретным ключом приложения

    login_count: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_login_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_fault_at: Mapped[datetime | None] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(ForeignKey(UserModel.id, ondelete="CASCADE"), nullable=False, index=True)

    token: Mapped[str] = mapped_column(unique=True, nullable=False)
    accepted: Mapped[bool] = mapped_column(default=False, nullable=False)

    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]
