"""
Auth + User profile endpoints — /api/v1/auth/* and /api/v1/users/*
Blueprint §11, §14, §75.1 (rate limits), §14.6/§73 (OAuth).
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status, Response

from app.common.dependencies import CurrentUserId, DbSession
from app.common.rate_limit_deps import RateLimitDep
from app.common.schemas import SuccessResponse
from app.core.exceptions import ValidationException
from app.modules.users.schemas import (
    ChangePasswordRequest,
    EmailRequest,
    LogoutAllRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
    VerifyEmailRequest,
)
from app.modules.users.service import UserService

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])
oauth_router = APIRouter(prefix="/auth/oauth", tags=["auth-oauth"])


# ── OAuth endpoints (§14.6, §73) ──────────────────────────────────────────────

@oauth_router.get("/authorize")
async def oauth_authorize():
    """Start the OIDC Authorization Code + PKCE flow — returns the provider URL."""
    from app.modules.users import oauth

    if not oauth.oauth_enabled():
        from app.core.exceptions import NotFoundException
        raise NotFoundException("OAuth is not configured on this deployment.")
    from fastapi.responses import RedirectResponse
    result = oauth.create_authorization_request()
    return RedirectResponse(url=result["authorization_url"])


@oauth_router.post("/callback")
async def oauth_callback(
    body: dict,
    request: Request,
    db: DbSession,
    _rl: None = RateLimitDep("auth_oauth_callback"),
):
    """Exchange the provider code (with PKCE verifier) for a CaseSense token pair.

    Body: {code, state, code_verifier?} — verifier is resolved server-side from
    state when the client did not hold it.
    """
    from app.modules.users import oauth

    code = (body or {}).get("code")
    state = (body or {}).get("state")
    if not code or not state:
        from app.core.exceptions import ValidationException
        raise ValidationException("code and state are required.")

    code_verifier = oauth.pop_state(state)
    if code_verifier is None:
        raise ValidationException("Invalid or expired OAuth state.")

    profile = await oauth.exchange_code_for_profile(code, code_verifier)
    user = await oauth.resolve_and_link(db, profile)

    svc = UserService(db)
    tokens = await svc._issue_tokens(user, _ua(request), _ip(request))
    return SuccessResponse(
        data={
            "user": UserResponse.model_validate(user).model_dump(),
            "tokens": tokens.model_dump(),
        },
        message="OAuth callback successful.",
    )


@oauth_router.get("/status")
async def oauth_status():
    """Whether OAuth is configured — the login screen checks this."""
    from app.modules.users import oauth

    return {"enabled": oauth.oauth_enabled(), "provider": "google"}


def _ua(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


# ── Auth endpoints (§75.1 rate limits on credential + mail endpoints) ─────────

@auth_router.post(
    "/register",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: UserRegisterRequest,
    request: Request,
    db: DbSession,
    _rl: None = RateLimitDep("auth_register"),
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
    _rl: None = RateLimitDep("auth_login"),
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


# ── v2.1 auth lifecycle ────────────────────────────────────────────────────────

@auth_router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(
    current_user_id: CurrentUserId,
    db: DbSession,
) -> SuccessResponse[UserResponse]:
    svc = UserService(db)
    user = await svc.get_me(current_user_id)
    return SuccessResponse(data=UserResponse.model_validate(user))


@auth_router.post("/verify-email", response_model=SuccessResponse[dict])
async def verify_email(body: VerifyEmailRequest, db: DbSession) -> SuccessResponse[dict]:
    svc = UserService(db)
    await svc.verify_email(body.token)
    return SuccessResponse(data={"email_verified": True}, message="Email verified.")


@auth_router.post(
    "/resend-verification",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def resend_verification(
    body: EmailRequest,
    db: DbSession,
    _rl: None = RateLimitDep("auth_resend_verification"),
) -> None:
    """OTP/verification mail — 1 per minute per IP+email (§75.1, email exhaustion guard)."""
    svc = UserService(db)
    await svc.resend_verification(body.email)


@auth_router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def forgot_password(
    body: EmailRequest,
    db: DbSession,
    _rl: None = RateLimitDep("auth_forgot_password"),
) -> None:
    """Reset/OTP mail — 1 per minute per IP+email (§75.1, email exhaustion guard)."""
    svc = UserService(db)
    await svc.forgot_password(body.email)


@auth_router.post("/reset-password", response_model=SuccessResponse[dict])
async def reset_password(body: ResetPasswordRequest, db: DbSession) -> SuccessResponse[dict]:
    svc = UserService(db)
    await svc.reset_password(body.token, body.new_password)
    return SuccessResponse(data={"success": True}, message="Password reset.")


@auth_router.post("/change-password", response_model=SuccessResponse[dict])
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user_id: CurrentUserId,
    db: DbSession,
) -> SuccessResponse[dict]:
    svc = UserService(db)
    user, tokens = await svc.change_password(
        current_user_id,
        current_password=body.current_password,
        new_password=body.new_password,
        user_agent=_ua(request),
        ip_address=_ip(request),
    )
    data: dict = {"success": True}
    if tokens is not None:
        data["tokens"] = tokens.model_dump()
    return SuccessResponse(data=data, message="Password changed.")


@auth_router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def logout_all(
    body: LogoutAllRequest,
    current_user_id: CurrentUserId,
    db: DbSession,
) -> None:
    svc = UserService(db)
    await svc.logout_all(current_user_id, body.refresh_token)


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
