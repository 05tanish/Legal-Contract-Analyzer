"""
LexAI – Legal Contract Intelligence Platform Launcher
======================================================
Usage:
  python run.py             # Starts FastAPI backend (port 8000)
  python run.py --seed      # Seeds Indian Bare Acts & Supreme Court Precedents
  python run.py --ingest    # Ingests Constitution PDF into Qdrant Cloud
  python run.py --worker    # Starts Celery async processing worker
"""

import os
import sys
import argparse

# Put backend on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

_user_site = os.path.expanduser("~/Library/Python/3.12/lib/python/site-packages")
if os.path.exists(_user_site) and _user_site not in sys.path:
    sys.path.append(_user_site)

# Polyfill 'packaging' for langchain_core/langgraph if not installed as standalone top-level package
if 'packaging' not in sys.modules:
    try:
        import packaging
    except ImportError:
        for vendor_prefix in ['setuptools._vendor.packaging', 'pip._vendor.packaging']:
            try:
                base = __import__(vendor_prefix, fromlist=['packaging'])
                sys.modules['packaging'] = base
                for sub in ['version', 'specifiers', 'requirements', 'markers', 'tags', 'utils']:
                    try:
                        smod = __import__(f'{vendor_prefix}.{sub}', fromlist=[sub])
                        sys.modules[f'packaging.{sub}'] = smod
                    except Exception:
                        pass
                break
            except Exception:
                pass

def start_backend(host="127.0.0.1", port=8000, reload=True):
    import uvicorn
    print("=" * 60)
    print("  LexAI Backend Starting...")
    print(f"  API Documentation:  http://localhost:{port}/docs")
    print(f"  Health Check:       http://localhost:{port}/health")
    print("=" * 60)
    uvicorn.run("app.main:app", host=host, port=port, reload=reload, app_dir=BACKEND_DIR)

def run_seed():
    import asyncio
    from scripts.seed_indian_law import seed_indian_legal_corpus
    print("Seeding Indian Legal Knowledge Base into PostgreSQL and Qdrant Cloud...")
    asyncio.run(seed_indian_legal_corpus())

def run_ingest(pdf_path=None):
    import asyncio
    from scripts.ingest_indian_law_pdf import ingest_constitution_pdf
    print("Ingesting Constitution PDF into PostgreSQL and Qdrant Cloud...")
    asyncio.run(ingest_constitution_pdf(pdf_path))

def start_worker():
    from workers.celery_app import celery
    print("Starting Celery Worker...")
    celery.worker_main(["worker", "--loglevel=info", "--concurrency=2"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LexAI Platform Launcher")
    parser.add_argument("--seed", action="store_true", help="Seed Indian legal knowledge base")
    parser.add_argument("--ingest", action="store_true", help="Ingest official Constitution PDF")
    parser.add_argument("--pdf", type=str, default=None, help="Custom PDF path for ingestion")
    parser.add_argument("--worker", action="store_true", help="Start Celery worker")
    parser.add_argument("--port", type=int, default=8000, help="Port for FastAPI backend")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for FastAPI backend")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")

    args = parser.parse_args()

    if args.seed:
        run_seed()
    elif args.ingest:
        run_ingest(args.pdf)
    elif args.worker:
        start_worker()
    else:
        start_backend(host=args.host, port=args.port, reload=not args.no_reload)

