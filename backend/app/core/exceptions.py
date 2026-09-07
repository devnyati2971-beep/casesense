"""
Domain exception hierarchy for CaseSense.
Every HTTP error mapping lives in the exception handlers registered in main.py.
"""

from __future__ import annotations


class CaseSenseError(Exception):
    """Base for all application errors."""

    message: str = "An unexpected error occurred."
    status_code: int = 500

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


# ── Auth / Identity ───────────────────────────────────────────────────────────

class InvalidCredentialsError(CaseSenseError):
    message = "Invalid credentials."
    status_code = 401


class TokenExpiredError(CaseSenseError):
    message = "Token has expired."
    status_code = 401


class TokenInvalidError(CaseSenseError):
    message = "Token is invalid."
    status_code = 401


class AuthenticationRequiredError(CaseSenseError):
    message = "Authentication required."
    status_code = 401


class PermissionDeniedError(CaseSenseError):
    message = "You do not have permission to perform this action."
    status_code = 403


# ── Resource ──────────────────────────────────────────────────────────────────

class NotFoundError(CaseSenseError):
    message = "Resource not found."
    status_code = 404

    def __init__(self, resource: str = "Resource", resource_id: str | None = None) -> None:
        detail = f"{resource} not found."
        if resource_id:
            detail = f"{resource} '{resource_id}' not found."
        super().__init__(detail)


class ConflictError(CaseSenseError):
    message = "Resource already exists."
    status_code = 409


class ValidationError(CaseSenseError):
    message = "Validation failed."
    status_code = 422


# ── Business Logic ────────────────────────────────────────────────────────────

class MatterAccessDeniedError(PermissionDeniedError):
    message = "You do not have access to this matter."


class DocumentProcessingError(CaseSenseError):
    message = "Document processing failed."
    status_code = 500


class StorageError(CaseSenseError):
    message = "Storage operation failed."
    status_code = 500


class AIError(CaseSenseError):
    message = "AI operation failed."
    status_code = 500


class LegalSourceError(CaseSenseError):
    message = "Legal source retrieval failed."
    status_code = 502


class CitationVerificationError(CaseSenseError):
    message = "Citation could not be verified against source text."
    status_code = 422


class DraftNotFinalizedError(CaseSenseError):
    message = "Draft must be finalized before export."
    status_code = 409


class DraftAlreadyFinalizedError(CaseSenseError):
    message = "Finalized drafts cannot be modified."
    status_code = 409


class OptimisticLockError(CaseSenseError):
    message = "Resource was modified by another request. Please refresh and retry."
    status_code = 409


class JobNotFoundError(NotFoundError):
    pass


class RateLimitError(CaseSenseError):
    message = "Rate limit exceeded. Please slow down."
    status_code = 429