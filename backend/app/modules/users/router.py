"""
Auth + User profile endpoints — /api/v1/auth/* and /api/v1/users/*
Blueprint §11, §14.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status, Response

from app.common.dependencies import CurrentUserId, DbSession
from app.common.schemas import SuccessResponse
from app.modules.users.schemas import (
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.modules.users.service import UserService

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _ua(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


# ── Auth endpoints ────────────────────────────────────────────────────────────

@auth_router.post(
    "/register",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: UserRegisterRequest,
    request: Request,
    db: DbSession,
) -> SuccessResponse[dict]:
    svc = UserService(db)
    user, tokens = await svc.register(body, _ua(request), _ip(request))
    return SuccessResponse(
        data={
            "user": UserResponse.model_validate(user).model_dump(),
            "tokens": tokens.model_dump(),
        },
        message="Registration successful.",
    )


@auth_router.post("/login", response_model=SuccessResponse[dict])
async def login(
    body: UserLoginRequest,
    request: Request,
    db: DbSession,
) -> SuccessResponse[dict]:
    svc = UserService(db)
    user, tokens = await svc.login(body.email, body.password, _ua(request), _ip(request))
    return SuccessResponse(
        data={
            "user": UserResponse.model_validate(user).model_dump(),
            "tokens": tokens.model_dump(),
        },
        message="Login successful.",
    )


@auth_router.post("/refresh", response_model=SuccessResponse[TokenPair])
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: DbSession,
) -> SuccessResponse[TokenPair]:
    svc = UserService(db)
    tokens = await svc.refresh_tokens(body.refresh_token, _ua(request), _ip(request))
    return SuccessResponse(data=tokens, message="Tokens refreshed.")


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def logout(body: LogoutRequest, db: DbSession) -> None:
    svc = UserService(db)
    await svc.logout(body.refresh_token)


# ── User profile endpoints ────────────────────────────────────────────────────

@users_router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(
    current_user_id: CurrentUserId,
    db: DbSession,
) -> SuccessResponse[UserResponse]:
    svc = UserService(db)
    user = await svc.get_profile(current_user_id)
    return SuccessResponse(data=UserResponse.model_validate(user))


@users_router.patch("/me", response_model=SuccessResponse[UserResponse])
async def update_me(
    body: UserUpdateRequest,
    current_user_id: CurrentUserId,
    db: DbSession,
) -> SuccessResponse[UserResponse]:
    svc = UserService(db)
    user = await svc.update_profile(
        current_user_id,
        full_name=body.full_name,
        bar_council_id=body.bar_council_id,
        phone=body.phone,
    )
    return SuccessResponse(data=UserResponse.model_validate(user))