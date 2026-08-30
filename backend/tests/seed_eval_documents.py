"""
One-time setup for the RAG eval suite: ingests the 4 sample PDFs into pgvector
under a dedicated test user, so RAGAS has a real indexed document store to
query against without touching your actual account's documents.

Run once before test_rag_retrieval_eval.py, and again any time you want a
clean slate:
    python tests/seed_eval_documents.py
"""
import asyncio
import sys
import os

# Must be set before any event loop is created — psycopg's async driver is
# incompatible with Windows' default ProactorEventLoop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from src.services.rag_service import process_and_ingest_pdf, remove_all_documents

EVAL_USER_ID = "eval_test_user_do_not_use_for_real_data"
PDF_DIR = os.path.join(os.path.dirname(__file__), "data", "pdfs")

PDF_FILES = [
    "Q3_Product_Sync_Agenda.pdf",
    "Sprint_14_Planning_Brief.pdf",
    "Client_Onboarding_Meeting_Notes.pdf",
    "DevSummit_2026_Travel_Itinerary.pdf",
]


async def seed():
    print(f"Clearing any existing documents for {EVAL_USER_ID}...")
    await remove_all_documents(EVAL_USER_ID)

    for filename in PDF_FILES:
        path = os.path.join(PDF_DIR, filename)
        if not os.path.exists(path):
            print(f"  ✗ MISSING: {path} — place the sample PDF here first.")
            continue
        with open(path, "rb") as f:
            file_bytes = f.read()
        success, message, data = await process_and_ingest_pdf(
            oauth_user_id=EVAL_USER_ID, filename=filename, file_bytes=file_bytes
        )
        status = "✓" if success else "✗"
        print(f"  {status} {filename}: {message}")

    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())