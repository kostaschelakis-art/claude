"""Authentication routes: dev login, OAuth SSO, logout, and current user."""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import create_access_token, get_current_user
from app.auth.oauth import oauth_client
from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.schemas.user import TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# ------------------------------------------------------------------ #
# Dev-mode login (email only, no password required)
# ------------------------------------------------------------------ #


class _DevLoginBody:
    """Minimal body for dev login – just an email."""

    from pydantic import BaseModel, EmailStr

    class Schema(BaseModel):
        email: EmailStr
        full_name: str | None = None


@router.post("/login", response_model=TokenResponse)
async def dev_login(
    body: _DevLoginBody.Schema,
    db: AsyncSession = Depends(get_db),
):
    """Dev-mode login.  Creates the user on the fly if it does not exist,
    then returns a signed JWT.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Ensure every account is associated with a market so that
    # /images/generate (which requires market_id) works out of the box.
    from app.models import Market

    gm_result = await db.execute(select(Market).where(Market.code == "GLOBAL"))
    global_market = gm_result.scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=body.email,
            full_name=body.full_name or body.email.split("@")[0],
            role=UserRole.CREATOR,
            is_active=True,
            market_id=global_market.id if global_market else None,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    elif user.market_id is None and global_market is not None:
        # Backfill market_id for accounts created before the seed.
        user.market_id = global_market.id
        await db.flush()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "market_id": str(user.market_id) if user.market_id else None,
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


# ------------------------------------------------------------------ #
# OAuth / SSO
# ------------------------------------------------------------------ #


@router.get("/oauth/login")
async def oauth_login(request: Request):
    """Redirect the user to Google's authorization page."""
    callback_url = settings.oauth_redirect_uri or str(request.url_for("oauth_callback"))
    state = secrets.token_urlsafe(32)
    auth_url = await oauth_client.get_authorization_url(
        redirect_uri=callback_url,
        state=state,
    )
    return RedirectResponse(url=auth_url)


@router.get("/oauth/callback", name="oauth_callback")
async def oauth_callback(
    code: str,
    state: str | None = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback: exchange code -> fetch profile -> issue JWT.

    Redirects to the frontend with the token in the URL fragment so the
    React app can pick it up.
    """
    callback_url = settings.oauth_redirect_uri or str(request.url_for("oauth_callback"))

    # Exchange code for tokens
    tokens = await oauth_client.exchange_code(code=code, redirect_uri=callback_url)
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an access token",
        )

    # Fetch user profile from Google
    user_info = await oauth_client.get_user_info(access_token)
    oauth_sub: str = user_info.get("sub", "")
    email: str = user_info.get("email", "")
    full_name: str = user_info.get("name", email.split("@")[0])
    picture: str = user_info.get("picture", "")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an email address",
        )

    # Upsert user
    result = await db.execute(
        select(User).where(
            (User.oauth_provider_id == oauth_sub) | (User.email == email)
        )
    )
    user = result.scalar_one_or_none()

    from app.models import Market

    gm_result = await db.execute(select(Market).where(Market.code == "GLOBAL"))
    global_market = gm_result.scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            role=UserRole.CREATOR,
            is_active=True,
            oauth_provider_id=oauth_sub,
            market_id=global_market.id if global_market else None,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        # Update provider id and name if not yet linked
        if not user.oauth_provider_id:
            user.oauth_provider_id = oauth_sub
        if full_name and user.full_name != full_name:
            user.full_name = full_name
        if user.market_id is None and global_market is not None:
            user.market_id = global_market.id
        await db.flush()

    if not user.is_active:
        return RedirectResponse(url="http://localhost:3000/login?error=inactive")

    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "market_id": str(user.market_id) if user.market_id else None,
        }
    )

    # Redirect to frontend with token — the React app reads it from the URL
    frontend_url = f"http://localhost:3000/oauth/callback?token={token}"
    return RedirectResponse(url=frontend_url)


# ------------------------------------------------------------------ #
# Logout
# ------------------------------------------------------------------ #


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User = Depends(get_current_user)):
    """Log out the current user.

    In a stateless JWT setup, the client simply discards the token.
    A production system would blacklist the token or delete the session
    record.  This endpoint exists for API symmetry and future expansion.
    """
    return None


# ------------------------------------------------------------------ #
# Current user
# ------------------------------------------------------------------ #


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)
