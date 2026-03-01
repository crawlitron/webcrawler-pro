import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

try:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    _AUTH_AVAILABLE = True
except ImportError:
    _AUTH_AVAILABLE = False
    logger.warning("python-jose or passlib not installed")

from ..database import SessionLocal  # noqa: E402
from ..models import User  # noqa: E402

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-replace-with-openssl-rand-hex-32-xxxxxxxxxxxxxxxx")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") if _AUTH_AVAILABLE else None
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserRegister(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain: str, hashed: str) -> bool:
    if not _AUTH_AVAILABLE:
        return False
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    if not _AUTH_AVAILABLE:
        raise RuntimeError("passlib not installed")
    return pwd_context.hash(plain)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
    if not token or not _AUTH_AVAILABLE:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    return db.query(User).filter(User.id == int(user_id), User.is_active is True).first()


def require_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if not _AUTH_AVAILABLE:
        raise HTTPException(503, "Auth dependencies not installed")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    if len(data.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if not _AUTH_AVAILABLE:
        raise HTTPException(503, "Auth dependencies not installed")
    user = db.query(User).filter(User.email == form.username, User.is_active is True).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(require_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(data: UserUpdate, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.email is not None:
        if db.query(User).filter(User.email == data.email, User.id != current_user.id).first():
            raise HTTPException(400, "Email already in use")
        current_user.email = data.email
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(data: ChangePassword, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not _AUTH_AVAILABLE:
        raise HTTPException(503, "Auth dependencies not installed")
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    if len(data.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


# ── Google OAuth ──────────────────────────────────────────────────────────────

class GoogleCallbackParams(BaseModel):
    code: str
    state: Optional[str] = None


@router.get("/google")
def google_login():
    """Redirect user to Google OAuth consent screen."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(400, "Google OAuth not configured (GOOGLE_CLIENT_ID missing)")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI",
                             os.getenv("APP_URL", "http://localhost:44544") + "/api/auth/google/callback")
    import urllib.parse
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    })
    from fastapi.responses import RedirectResponse
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
def google_callback(code: str, state: Optional[str] = None, db: Session = Depends(get_db)):
    """Exchange Google auth code for tokens, create/login user."""
    import httpx
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise HTTPException(400, "Google OAuth not configured")

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI",
                             os.getenv("APP_URL", "http://localhost:44544") + "/api/auth/google/callback")
    frontend_url = os.getenv("APP_URL", "http://localhost:44544")

    # Exchange code for tokens
    try:
        resp = httpx.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
    except Exception:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"{frontend_url}/auth/login?error=google_token_failed")

    # Get user info
    try:
        userinfo = httpx.get("https://www.googleapis.com/oauth2/v2/userinfo",
                             headers={"Authorization": "Bearer " + token_data.get("access_token", "")},
                             timeout=10).json()
    except Exception:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"{frontend_url}/auth/login?error=google_userinfo_failed")

    google_email = userinfo.get("email", "")
    if not google_email:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"{frontend_url}/auth/login?error=no_email")

    # Find or create user
    user = db.query(User).filter(User.email == google_email).first()
    if not user:
        import secrets
        user = User(
            email=google_email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),  # random pw, can't login with pw
            full_name=userinfo.get("name", google_email.split("@")[0]),
            is_active=True,
            is_admin=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    user.last_login = datetime.utcnow()
    db.commit()

    # Create JWT and redirect to frontend
    jwt_token = create_access_token({"sub": str(user.id)})
    from fastapi.responses import RedirectResponse
    return RedirectResponse(
        f"{frontend_url}/auth/callback?token={jwt_token}&email={google_email}&name={userinfo.get('name', '')}"
    )
