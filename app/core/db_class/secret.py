"""Encrypted secrets (API keys, tokens, TOTP seed). Read and written only through `secret_core`."""

from __future__ import annotations

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_class.base import BaseEntity


class Secret(BaseEntity):
    __tablename__ = "secret"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary(12), nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    hint: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    key_version: Mapped[int] = mapped_column(default=1, nullable=False)
