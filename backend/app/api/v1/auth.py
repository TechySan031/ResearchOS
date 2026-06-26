"""Authentication API endpoints.

Provides REST endpoints for user registration, login, token refresh,
logout, and retrieving the current user profile.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import get_settings
from app.core.exceptions import ValidationError
from app.core.security import CurrentUser, get_current_user
from app.models.schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.utils.logging import get_logger
from pydantic import BaseModel, EmailStr, Field

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(
        min_length=8,
        max_length=128,
    )


def _client_ip(request: Request) -> str:
    """Extract the client IP from the request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(data: UserRegisterRequest, request: Request) -> UserResponse:
    """Create a new user account.

    Args:
        data: Registration payload with email, password, name.
        request: The incoming request.

    Returns:
        The created user.
    """
    logger.info("api.auth.register", email=data.email)

    try:
        user = await AuthService.register(
            email=data.email,
            password=data.password,
            name=data.name,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    await AuditService.log(
        action="user_registered",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return UserResponse.model_validate(user, from_attributes=True)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive tokens",
)
async def login(data: UserLoginRequest, request: Request) -> TokenResponse:
    """Authenticate a user and return JWT tokens.

    Args:
        data: Login payload with email and password.
        request: The incoming request.

    Returns:
        Access and refresh tokens.
    """
    logger.info("api.auth.login", email=data.email)

    try:
        user, access_token, refresh_token = await AuthService.login(
            email=data.email,
            password=data.password,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    settings = get_settings()

    await AuditService.log(
        action="user_login",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh(data: RefreshTokenRequest, request: Request) -> TokenResponse:
    """Exchange a refresh token for a new token pair.

    Args:
        data: Refresh token payload.
        request: The incoming request.

    Returns:
        New access and refresh tokens.
    """
    logger.info("api.auth.refresh")

    try:
        access_token, refresh_token = await AuthService.refresh(data.refresh_token)
    except ValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    settings = get_settings()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout (client-side token invalidation)",
)
async def logout(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """Logout the current user.

    This endpoint is a server-side acknowledgement.  The client is
    responsible for discarding the tokens.

    Args:
        request: The incoming request.
        user: The authenticated user.
    """
    await AuditService.log(
        action="user_logout",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {"detail": "Logged out successfully"}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
)

async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
):
    """
    Generate a password reset token and send a reset email.

    Always returns HTTP 200 to avoid revealing whether
    the email exists.
    """

    email = data.email.strip().lower()

    logger.info(
        "api.auth.forgot_password.start",
        email=email,
    )

    # ── Step 1: Look up user ──
    try:
        user = await AuthService.get_user_by_email(email)
    except Exception as exc:
        logger.exception("api.auth.forgot_password.user_lookup_failed", error=str(exc))
        return {
            "detail": "If an account exists with that email, reset instructions have been sent.",
            "_debug_error": f"user_lookup_failed: {type(exc).__name__}: {exc}",
        }

    if not user:
        logger.info("api.auth.forgot_password.user_not_found", email=email)
        return {
            "detail": "If an account exists with that email, reset instructions have been sent.",
        }

    logger.info("api.auth.forgot_password.user_found", user_id=user.id)

    # ── Step 2: Create reset token ──
    try:
        token = await AuthService.create_password_reset_token(user)
    except Exception as exc:
        logger.exception("api.auth.forgot_password.token_creation_failed", error=str(exc))
        return {
            "detail": "If an account exists with that email, reset instructions have been sent.",
            "_debug_error": f"token_creation_failed: {type(exc).__name__}: {exc}",
        }

    logger.info("api.auth.forgot_password.token_created", user_id=user.id)

    # ── Step 3: Build reset URL ──
    settings = get_settings()
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"

    logger.info(
        "api.auth.forgot_password.sending_email",
        user_id=user.id,
        email=user.email,
        frontend_url=settings.frontend_url,
        email_from=settings.email_from,
        has_resend_key=bool(settings.resend_api_key),
        resend_key_prefix=settings.resend_api_key[:8] + "..." if settings.resend_api_key else "EMPTY",
    )

    # ── Step 4: Send email ──
    try:
        email_sent = await EmailService.send_password_reset_email(
            email=user.email,
            name=user.name,
            reset_url=reset_url,
        )
    except Exception as exc:
        logger.exception("api.auth.forgot_password.email_send_exception", error=str(exc))
        return {
            "detail": "If an account exists with that email, reset instructions have been sent.",
            "_debug_error": f"email_send_exception: {type(exc).__name__}: {exc}",
        }

    if not email_sent:
        logger.error("api.auth.forgot_password.email_send_returned_false", user_id=user.id)
        return {
            "detail": "If an account exists with that email, reset instructions have been sent.",
            "_debug_error": "email_service_returned_false — check RESEND_API_KEY and EMAIL_FROM config",
        }

    logger.info("api.auth.forgot_password.email_sent_successfully", user_id=user.id)

    # ── Step 5: Audit log ──
    try:
        await AuditService.log(
            action="password_reset_requested",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as exc:
        logger.exception("api.auth.forgot_password.audit_log_failed", error=str(exc))

    return {
        "detail": "If an account exists with that email, reset instructions have been sent.",
    }

@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password",
)
async def reset_password(
    data: ResetPasswordRequest,
):
    """
    Reset the user's password using a valid reset token.
    """

    try:
        await AuthService.reset_password(
            token=data.token,
            new_password=data.password,
        )

    except ValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc

    return {
        "detail": "Password reset successful."
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(user: CurrentUser = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the currently authenticated user.

    Args:
        user: The authenticated user (injected via dependency).

    Returns:
        The user profile.
    """
    from app.services.auth_service import AuthService

    db_user = await AuthService.get_user_by_id(user.id)
    return UserResponse.model_validate(db_user, from_attributes=True)
