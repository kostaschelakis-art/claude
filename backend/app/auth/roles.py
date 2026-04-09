"""Role-based access control dependencies for FastAPI."""

from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.auth.middleware import get_current_user
from app.models import User, UserRole

# Ordered hierarchy – index determines rank.
_ROLE_HIERARCHY: list[UserRole] = [
    UserRole.VIEWER,
    UserRole.CREATOR,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
]


def _role_rank(role: UserRole) -> int:
    """Return the numeric rank for *role* (higher is more privileged)."""
    try:
        return _ROLE_HIERARCHY.index(role)
    except ValueError:
        return -1


def require_role(min_role: UserRole):
    """Return a FastAPI dependency that enforces a minimum role level.

    Usage::

        @router.post("/", dependencies=[Depends(require_role(UserRole.ADMIN))])
        async def admin_only_route(...): ...
    """

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if _role_rank(current_user.role) < _role_rank(min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions. Required role: {min_role.value}, "
                    f"your role: {current_user.role.value}"
                ),
            )
        return current_user

    return _check


def require_market_access(market_id: UUID):
    """Return a FastAPI dependency that verifies the current user belongs to
    the given *market_id*.

    ``SUPER_ADMIN`` users bypass this check and always have access.

    Usage::

        @router.get("/{market_id}/data")
        async def get_data(
            market_id: UUID,
            user: User = Depends(require_market_access(market_id)),
        ): ...

    .. note::

        For path-parameter driven checks, prefer using
        :func:`check_market_access` directly inside the route body.
    """

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user
        if current_user.market_id != market_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this market",
            )
        return current_user

    return _check


def check_market_access(user: User, market_id: UUID) -> None:
    """Inline helper to verify market access inside a route body.

    Raises :class:`HTTPException` (403) when the user does not belong to
    *market_id* and is not a ``SUPER_ADMIN``.
    """
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.market_id != market_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this market",
        )
