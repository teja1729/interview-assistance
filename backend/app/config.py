"""Environment configuration. Secrets never enter workspace settings or API responses."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'saas.db'}")
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
    speech_language: str = os.getenv("SPEECH_LANGUAGE", "en-IN")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    company_research_enabled: bool = os.getenv("COMPANY_RESEARCH_ENABLED", "true").lower() == "true"
    transcription_model: str = os.getenv("TRANSCRIPTION_MODEL", "gemini-3.5-flash")
    tts_model: str = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
    tts_voice: str = os.getenv("GEMINI_TTS_VOICE", "Kore")
    stripe_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_pro_price: str = os.getenv("STRIPE_PRO_PRICE_ID", "")
    stripe_team_price: str = os.getenv("STRIPE_TEAM_PRICE_ID", "")
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
