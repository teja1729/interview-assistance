"""Environment configuration. Secrets never enter workspace settings or API responses."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'saas.db'}")
    # Hosted Postgres providers commonly supply postgres:// or postgresql:// URLs.
    # This project installs psycopg 3, so select that SQLAlchemy driver explicitly.
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str = _database_url()
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").rstrip("/")
    session_secret: str = os.getenv("SESSION_SECRET", "development-only-change-before-deploying")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    linkedin_client_id: str = os.getenv("LINKEDIN_CLIENT_ID", "")
    linkedin_client_secret: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    demo_login: bool = os.getenv("AUTH_DEMO_ENABLED", "false").lower() == "true"
    default_profile: str = os.getenv("AI_DEFAULT_PROFILE", "sarvam")
    models_file: Path = Path(os.getenv("AI_MODELS_FILE", str(ROOT / "config" / "models.toml")))
    audio_provider: str = os.getenv("AUDIO_PROVIDER", "sarvam")
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
    sarvam_stt_model: str = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
    sarvam_tts_model: str = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
    sarvam_tts_voice: str = os.getenv("SARVAM_TTS_VOICE", "ritu")
    stripe_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_pro_price: str = os.getenv("STRIPE_PRO_PRICE_ID", "")
    stripe_team_price: str = os.getenv("STRIPE_TEAM_PRICE_ID", "")
    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    razorpay_starter_monthly_amount_paise: int = int(os.getenv("RAZORPAY_STARTER_MONTHLY_AMOUNT_PAISE", "99900"))
    razorpay_starter_yearly_amount_paise: int = int(os.getenv("RAZORPAY_STARTER_YEARLY_AMOUNT_PAISE", "999900"))
    razorpay_pro_monthly_amount_paise: int = int(os.getenv("RAZORPAY_PRO_MONTHLY_AMOUNT_PAISE", "299900"))
    razorpay_pro_yearly_amount_paise: int = int(os.getenv("RAZORPAY_PRO_YEARLY_AMOUNT_PAISE", "2999900"))
    razorpay_senior_monthly_amount_paise: int = int(os.getenv("RAZORPAY_SENIOR_MONTHLY_AMOUNT_PAISE", "499900"))
    razorpay_senior_yearly_amount_paise: int = int(os.getenv("RAZORPAY_SENIOR_YEARLY_AMOUNT_PAISE", "4999900"))
    inline_worker: bool = os.getenv("INLINE_WORKER", "false").lower() == "true"
    local_usage_overrides: bool = os.getenv("LOCAL_USAGE_OVERRIDES", "false").lower() == "true"
    local_interview_limit: int = int(os.getenv("LOCAL_INTERVIEW_LIMIT", "100"))
    local_ai_call_limit: int = int(os.getenv("LOCAL_AI_CALL_LIMIT", "5000"))

    @property
    def production(self) -> bool:
        return self.environment == "production"

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def linkedin_enabled(self) -> bool:
        return bool(self.linkedin_client_id and self.linkedin_client_secret)

    def validate(self) -> None:
        if not self.production:
            return
        if len(self.session_secret) < 32 or self.session_secret.startswith("development"):
            raise RuntimeError("Production requires a random SESSION_SECRET of at least 32 characters")
        if self.demo_login or self.default_profile == "demo":
            raise RuntimeError("Disable AUTH_DEMO_ENABLED and select a live AI_DEFAULT_PROFILE in production")
        if not self.database_url.startswith("postgresql"):
            raise RuntimeError("Production requires a PostgreSQL DATABASE_URL")
        if not self.frontend_origin.startswith("https://") or not self.google_enabled:
            raise RuntimeError("Production requires HTTPS FRONTEND_ORIGIN and Google OAuth credentials")


settings = Settings()
