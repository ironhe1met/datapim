"""Auth endpoints: login, refresh, logout, me (GET/PATCH).

Stateless JWT: logout is a no-op server-side (no token blacklist in v1.0).
Clients discard tokens on logout; short-lived access tokens limit exposure.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeUpdate,
    RefreshRequest,
    TokenPair,
    UserPublic,
)
from app.security.jwt import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.security.passwords import hash_password, verify_password
from app.services.auth_service import get_user_by_email, get_user_by_id

router = APIRouter()


def _user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        theme=user.theme,
        created_at=user.created_at,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_session),
) -> LoginResponse:
    user = await get_user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        logger.info("auth_login_failed", email=body.email, reason="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Невірний email або пароль", "code": "INVALID_CREDENTIALS"},
        )

    if not user.is_active:
        logger.info("auth_login_failed", email=body.email, reason="account_disabled")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Акаунт деактивовано", "code": "ACCOUNT_DISABLED"},
        )

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    logger.info("auth_login_success", email=user.email, user_id=str(user.id))
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        user=_user_public(user),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_session),
) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token)
    except JWTError as exc:
        # Differentiate expired vs other invalid tokens via message.
        message = str(exc).lower()
        if "expire" in message:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Token expired", "code": "TOKEN_EXPIRED"},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid token", "code": "INVALID_TOKEN"},
        ) from exc

    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid token", "code": "INVALID_TOKEN"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid token", "code": "INVALID_TOKEN"},
        )

    try:
        user_id = UUID(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid token", "code": "INVALID_TOKEN"},
        ) from exc

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid token", "code": "INVALID_TOKEN"},
        )

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
    )


@router.post("/logout")
async def logout(_user: User = Depends(get_current_user)) -> dict[str, str]:
    # Stateless JWT — server has no session to invalidate. Client discards tokens.
    # Future: token blacklist / short-lived access + rotating refresh with jti revocation.
    return {"message": "ok"}


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)) -> UserPublic:
    return _user_public(user)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: MeUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> UserPublic:
    changed = False

    if body.name is not None and body.name != user.name:
        user.name = body.name
        changed = True

    if body.theme is not None and body.theme != user.theme:
        user.theme = body.theme
        changed = True

    if body.password is not None:
        # validator guarantees current_password is set
        if not body.current_password or not verify_password(
            body.current_password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Поточний пароль невірний", "code": "INVALID_PASSWORD"},
            )
        user.password_hash = hash_password(body.password)
        changed = True

    if changed:
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return _user_public(user)
