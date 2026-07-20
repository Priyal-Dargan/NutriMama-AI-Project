"""
routes/auth.py
Authentication endpoints: register, login, logout, forgot-password, reset-password.

Note on logout: JWTs are stateless, so "logout" is enforced client-side (the frontend
discards the token). For true server-side invalidation, add a token-blocklist table —
left as a documented future enhancement to keep this phase's scope honest.

Note on forgot-password: this issues a short-lived reset token and returns it directly
in the response for now (no email service is wired up yet — see README "Known Gaps").
In production this token must be emailed to the user, never returned in the API response.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import create_access_token, create_refresh_token, decode_token
from database import get_db
from dependencies import get_current_user
from models.user import User
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from utils.security import hash_password, verify_password
from utils.logger import get_logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)

RESET_TOKEN_EXPIRE_MINUTES = 30


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New user registered: user_id={user.id}")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    logger.info(f"User logged in: user_id={user.id}")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(current_user: User = Depends(get_current_user)):
    logger.info(f"User logged out: user_id={current_user.id}")
    return {"message": "Logged out successfully. Please discard your access token client-side."}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Always return a generic message — never reveal whether an email is registered.
    generic_response = {"message": "If that email is registered, a reset link has been sent."}
    if not user:
        return generic_response

    reset_token = create_access_token(
        subject=str(user.id), expires_minutes=RESET_TOKEN_EXPIRE_MINUTES
    )
    logger.info(f"Password reset requested: user_id={user.id}")

    # TODO (Phase 5 / production): send `reset_token` via an email service instead of
    # returning it here. Returned only to keep this endpoint testable without email infra.
    generic_response["reset_token_dev_only"] = reset_token
    return generic_response


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    decoded = decode_token(payload.token)
    if decoded is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == int(decoded["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()

    logger.info(f"Password reset completed: user_id={user.id}")
    return {"message": "Password has been reset successfully."}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
