"""Configuration module for Kinguin Telegram Bot."""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # Telegram
    telegram_token: str
    telegram_allowed_users: list[int]

    # Kinguin API
    kinguin_api_key: str
    kinguin_api_secret: Optional[str]
    kinguin_base_url: str = "https://gateway.kinguin.net/esa/api/v1"

    # Database
    database_path: str = "data/purchases.db"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        kinguin_api_key = os.getenv("KINGUIN_API_KEY")
        if not kinguin_api_key:
            raise ValueError("KINGUIN_API_KEY is required")

        allowed_users_str = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        allowed_users = [
            int(uid.strip())
            for uid in allowed_users_str.split(",")
            if uid.strip()
        ]

        return cls(
            telegram_token=telegram_token,
            telegram_allowed_users=allowed_users,
            kinguin_api_key=kinguin_api_key,
            kinguin_api_secret=os.getenv("KINGUIN_API_SECRET"),
            database_path=os.getenv("DATABASE_PATH", "data/purchases.db"),
        )

    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot."""
        if not self.telegram_allowed_users:
            return True
        return user_id in self.telegram_allowed_users
