from fastapi import APIRouter, Depends, HTTPException
from cryptography.fernet import Fernet
from datetime import datetime
from typing import Dict
import os

from ..models import AppSettings, User
from ..database import SessionLocal
from ..schemas import SetupStatus, SetupCompleteRequest

router = APIRouter(prefix="/api/setup", tags=["setup"])

# ── Fernet encryption ─────────────────────────────────────────────────────────
FERNET_KEY = os.getenv("FERNET_KEY", "")
if not FERNET_KEY:
    FERNET_KEY = Fernet.generate_key().decode()
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    env_path = os.path.abspath(env_path)
    try:
        with open(env_path, "a") as f:
            f.write("\nFERNET_KEY=" + FERNET_KEY + "\n")
    except Exception:
        pass

try:
    _fernet = Fernet(FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY)
except Exception:
    _fernet = Fernet(Fernet.generate_key())


def encrypt_value(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


SENSITIVE_KEYS = {"smtp_password", "google_client_secret", "admin_password"}


# ── DB helper ─────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/status", response_model=SetupStatus)
def get_setup_status():
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.is_admin == True).first() is not None
        settings = db.query(AppSettings).all()
        steps_done = []
        if admin_exists:
            steps_done.append("admin")
        if any(s.key == "smtp_host" for s in settings):
            steps_done.append("email")
        if any(s.key == "google_client_id" for s in settings):
            steps_done.append("google")
        if any(s.key == "app_url" for s in settings):
            steps_done.append("general")
        return {"completed": admin_exists, "steps_done": steps_done}
    finally:
        db.close()


@router.post("/complete")
def complete_setup(request: SetupCompleteRequest):
    db = SessionLocal()
    try:
        # Guard: only run once
        if db.query(User).filter(User.is_admin == True).first():
            raise HTTPException(400, "Setup already completed")

        # Import here to avoid circular deps
        from ..routers.auth import hash_password

        # Create admin user
        admin = User(
            email=request.admin.email,
            hashed_password=hash_password(request.admin.password),
            full_name=request.admin.full_name or "Administrator",
            is_admin=True,
            is_active=True,
        )
        db.add(admin)

        # Persist extra settings
        for key, value in request.settings.items():
            if not value:
                continue
            sensitive = key in SENSITIVE_KEYS
            stored = encrypt_value(value) if sensitive else value
            existing = db.query(AppSettings).filter(AppSettings.key == key).first()
            if existing:
                existing.value = stored
                existing.is_sensitive = sensitive
                existing.updated_at = datetime.utcnow()
            else:
                db.add(AppSettings(key=key, value=stored,
                                   is_sensitive=sensitive, updated_at=datetime.utcnow()))

        db.commit()
        return {"status": "success", "message": "Setup completed — please log in"}
    finally:
        db.close()


@router.get("/settings")
def get_settings():
    db = SessionLocal()
    try:
        settings = db.query(AppSettings).all()
        return {
            s.key: "***" if s.is_sensitive else s.value
            for s in settings
        }
    finally:
        db.close()


@router.put("/settings")
def update_settings(updates: Dict[str, str]):
    db = SessionLocal()
    try:
        for key, value in updates.items():
            if not value:
                continue
            sensitive = key in SENSITIVE_KEYS
            stored = encrypt_value(value) if sensitive else value
            existing = db.query(AppSettings).filter(AppSettings.key == key).first()
            if existing:
                existing.value = stored
                existing.updated_at = datetime.utcnow()
            else:
                db.add(AppSettings(key=key, value=stored,
                                   is_sensitive=sensitive, updated_at=datetime.utcnow()))
        db.commit()
        return {"status": "success"}
    finally:
        db.close()
