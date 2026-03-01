from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from cryptography.fernet import Fernet
from datetime import datetime
import os
from ..models import AppSettings
from ..database import SessionLocal
from ..schemas import SetupStatus, SetupCompleteRequest
from typing import Dict

router = APIRouter(prefix="/api/setup")

# Get encryption key from env
FERNET_KEY = os.getenv('FERNET_KEY')
if not FERNET_KEY:
    # Generate new key if none exists
    FERNET_KEY = Fernet.generate_key().decode()
    with open('/a0/usr/workdir/webcrawler-pro/.env', 'a') as f:
        f.write(f'\nFERNET_KEY={FERNET_KEY}\n')

fernet = Fernet(FERNET_KEY)

def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    return fernet.decrypt(encrypted_value.encode()).decode()

@router.get("/status", response_model=SetupStatus)
def get_setup_status():
    db = SessionLocal()
    try:
        # Check if admin user exists (basic setup completed)
        admin_exists = False  # TODO: Check user table
        
        settings = db.query(AppSettings).all()
        
        steps_completed = []
        if any(s.key == 'admin_email' for s in settings):
            steps_completed.append('admin')
        if any(s.key == 'smtp_host' for s in settings):
            steps_completed.append('email')
        if any(s.key == 'google_client_id' for s in settings):
            steps_completed.append('google')
        if any(s.key == 'app_url' for s in settings):
            steps_completed.append('general')
            
        return {
            "completed": admin_exists,
            "steps_done": steps_completed
        }
    finally:
        db.close()

@router.post("/complete")
def complete_setup(request: SetupCompleteRequest):
    db = SessionLocal()
    try:
        # Process admin user creation
        # TODO: Add user creation logic
        
        # Save all settings
        for key, value in request.settings.items():
            is_sensitive = key in ['admin_password', 'smtp_password', 'google_client_secret']
            
            setting = db.query(AppSettings).filter(AppSettings.key == key).first()
            if setting:
                setting.value = encrypt_value(value) if is_sensitive else value
                setting.is_sensitive = is_sensitive
            else:
                new_setting = AppSettings(
                    key=key,
                    value=encrypt_value(value) if is_sensitive else value,
                    is_sensitive=is_sensitive
                )
                db.add(new_setting)
        
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

@router.get("/settings")
def get_settings():
    db = SessionLocal()
    try:
        settings = db.query(AppSettings).all()
        return {
            s.key: decrypt_value(s.value) if s.is_sensitive else s.value
            for s in settings if not s.is_sensitive
        }
    finally:
        db.close()

@router.put("/settings")
def update_settings(updates: Dict[str, str]):
    db = SessionLocal()
    try:
        for key, value in updates.items():
            setting = db.query(AppSettings).filter(AppSettings.key == key).first()
            if not setting:
                raise HTTPException(status_code=404, detail=f"Setting {key} not found")
                
            is_sensitive = setting.is_sensitive
            if is_sensitive:
                # For sensitive fields, verify old value matches
                old_value = decrypt_value(setting.value)
                if old_value != updates.get(f"old_{key}"):
                    raise HTTPException(status_code=400, detail=f"Old {key} does not match")
                
            setting.value = encrypt_value(value) if is_sensitive else value
            
        db.commit()
        return {"status": "success"}
    finally:
        db.close()
