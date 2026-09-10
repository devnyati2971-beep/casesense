from arq.connections import RedisSettings
from app.core.config import settings
from app.jobs.tasks.document import process_document
from app.jobs.tasks.intelligence import analyze_case
from app.jobs.tasks.research import execute_research
from app.jobs.tasks.drafting import generate_draft, export_draft

class WorkerSettings:
    """Arq worker configuration entrypoint per Blueprint §30.

    NOTE (deviation register, §71): the blueprint names three queues
    (docs/research/ai). For the MVP a single default queue is used so one
    worker process serves every job type; arq 0.26 workers listen on one
    queue per process. Split queues = run one worker per queue in compose.
    """

    functions = [
        process_document,
        analyze_case,
        execute_research,
        generate_draft,
        export_draft,
    ]
    max_jobs = 10
    job_timeout = 600  # 10 minutes per document processing cap