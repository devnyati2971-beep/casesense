"""
Audit service — write audit log entries.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import AuditAction
from app.modules.audit.models import AuditLog


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        action: AuditAction | str,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        matter_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        extra_data: dict | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action if isinstance(action, str) else action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            matter_id=matter_id,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data,
            success=success,
            error_message=error_message,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry