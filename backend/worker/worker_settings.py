from arq.connections import RedisSettings
from app.core.config import settings
from app.jobs.tasks.document import process_document
from app.jobs.tasks.intelligence import analyze_case
from app.jobs.tasks.research import execute_research
from app.jobs.tasks.drafting import generate_draft, export_draft

class WorkerSettings:
    """Arq worker configuration entrypoint per Blueprint §30."""

    functions = [
        process_document,
        analyze_case,
        execute_research,
        generate_draft,
        export_draft,
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    queue_name = "docs" # Note: Arq will listen to this default queue
    max_jobs = 10
    job_timeout = 600  # 10 minutes per document processing cap