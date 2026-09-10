"""
Shared FastAPI dependencies — authentication, pagination, DB session.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationRequiredError, TokenInvalidError
from app.core.security import decode_access_token
from app.db.engine import get_db

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> uuid.UUID:
    """Extract and validate the Bearer JWT; return the user UUID."""
    if credentials is None:
        raise AuthenticationRequiredError()
    payload = decode_access_token(credentials.credentials)
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise TokenInvalidError()


async def get_current_user_role(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """Return the role claim from the access token."""
    if credentials is None:
        raise AuthenticationRequiredError()
    payload = decode_access_token(credentials.credentials)
    return payload.get("role", "advocate")


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


# Convenience type aliases
CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
CurrentUserRole = Annotated[str, Depends(get_current_user_role)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
PaginationDep = Annotated[Pagination, Depends()]