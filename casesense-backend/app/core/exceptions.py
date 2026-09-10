"""
Domain exception hierarchy for CaseSense.
Every HTTP error mapping lives in the exception handlers registered in main.py.
"""

from __future__ import annotations
from typing import Any


class CaseSenseError(Exception):
    """Base for all application errors."""

    message: str = "An unexpected error occurred."
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self, 
        message: str | None = None, 
        details: dict[str, Any] | None = None,
        code: str | None = None
    ) -> None:
        self.message = message or self.__class__.message
        self.details = details or {}
        self.code = code or self.__class__.code
        super().__init__(self.message)


# ── Auth / Identity ───────────────────────────────────────────────────────────

class InvalidCredentialsError(CaseSenseError):
    message = "Invalid credentials."
    status_code = 401
    code = "INVALID_CREDENTIALS"


class TokenExpiredError(CaseSenseError):
    message = "Token has expired."
    status_code = 401
    code = "TOKEN_EXPIRED"


class TokenInvalidError(CaseSenseError):
    message = "Token is invalid."
    status_code = 401
    code = "INVALID_TOKEN"


class AuthenticationRequiredError(CaseSenseError):
    message = "Authentication required."
    status_code = 401
    code = "UNAUTHENTICATED"


class PermissionDeniedError(CaseSenseError):
    message = "You do not have permission to perform this action."
    status_code = 403
    code = "FORBIDDEN"


# ── Resource ──────────────────────────────────────────────────────────────────

class NotFoundError(CaseSenseError):
    message = "Resource not found."
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, resource: str = "Resource", resource_id: str | None = None) -> None:
        detail = f"{resource} not found."
        if resource_id:
            detail = f"{resource} '{resource_id}' not found."
        super().__init__(message=detail)


class ConflictError(CaseSenseError):
    message = "Resource already exists."
    status_code = 409
    code = "CONFLICT"


class ValidationError(CaseSenseError):
    message = "Validation failed."
    status_code = 422
    code = "VALIDATION_ERROR"


# ── Business Logic ────────────────────────────────────────────────────────────

class MatterAccessDeniedError(PermissionDeniedError):
    message = "You do not have access to this matter."
    code = "MATTER_ACCESS_DENIED"


class DocumentProcessingError(CaseSenseError):
    message = "Document processing failed."
    status_code = 500
    code = "DOCUMENT_PROCESSING_ERROR"


class StorageError(CaseSenseError):
    message = "Storage operation failed."
    status_code = 500
    code = "STORAGE_ERROR"


class AIError(CaseSenseError):
    message = "AI operation failed."
    status_code = 500
    code = "AI_ERROR"


class LegalSourceError(CaseSenseError):
    message = "Legal source retrieval failed."
    status_code = 502
    code = "LEGAL_SOURCE_ERROR"


class CitationVerificationError(CaseSenseError):
    message = "Citation could not be verified against source text."
    status_code = 422
    code = "CITATION_VERIFICATION_ERROR"


class DraftNotFinalizedError(CaseSenseError):
    message = "Draft must be finalized before export."
    status_code = 409
    code = "DRAFT_NOT_FINALIZED"


class DraftAlreadyFinalizedError(CaseSenseError):
    message = "Finalized drafts cannot be modified."
    status_code = 409
    code = "DRAFT_ALREADY_FINALIZED"


class OptimisticLockError(CaseSenseError):
    message = "Resource was modified by another request. Please refresh and retry."
    status_code = 409
    code = "CONCURRENT_UPDATE"


class JobNotFoundError(NotFoundError):
    pass


class RateLimitError(CaseSenseError):
    message = "Rate limit exceeded. Please slow down."
    status_code = 429
    code = "RATE_LIMITED"


# ── Pipeline & Integration Additions (v2.1 Compatibility) ─────────────────────

class ValidationException(CaseSenseError):
    status_code = 422
    code = "INVALID_REQUEST"


class NotFoundException(CaseSenseError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictException(CaseSenseError):
    status_code = 409
    code = "CONFLICT"


class InternalServerException(CaseSenseError):
    status_code = 500
    code = "INTERNAL_ERROR"