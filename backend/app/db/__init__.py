"""
Database exports. Ensures all models are imported so Alembic can discover them.
"""

from app.db.base import Base
from app.db.engine import engine, get_db

# We import the modules directly to ensure all models register with Base.metadata.
# This prevents ImportErrors if specific class names are refactored to match the Blueprint.
import app.modules.users.models
import app.modules.matters.models
import app.modules.documents.models
import app.modules.case_intelligence.models
import app.modules.research.models
import app.modules.judgements.models  # Corrected to match existing folder spelling
import app.modules.citations.models
import app.modules.authorities.models
import app.modules.drafting.models
import app.modules.audit.models

__all__ = ["Base", "engine", "get_db"]