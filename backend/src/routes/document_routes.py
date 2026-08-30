from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from src.middleware.require_session import require_session
from src.config.rate_limiter import limiter
from src.services.rag_service import (
    process_and_ingest_pdf,
    get_user_docs,
    remove_user_doc,
)

document_router = APIRouter(prefix="/api/documents", tags=["documents"])

@document_router.get("")
async def list_documents_endpoint(auth=Depends(require_session)):
    try:
        docs = await get_user_docs(auth["oauth_user_id"])
        return {"documents": docs}
    except Exception as e:
        print(f"[GET /documents Error] {e}")
        raise HTTPException(status_code=500, detail="Could not load uploaded documents.")

@document_router.post("/upload")
@limiter.limit("10/minute")
async def upload_document_endpoint(
    request: Request,
    file: UploadFile = File(...),
    auth=Depends(require_session)
):
    filename = file.filename
    SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt")
    if not filename or not any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT documents are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    success, message, data = await process_and_ingest_pdf(
        oauth_user_id=auth["oauth_user_id"],
        filename=filename,
        file_bytes=file_bytes,
    )

    if not success:
        raise HTTPException(status_code=422, detail=message)

    return {"success": True, "message": message, "document": data}

@document_router.delete("/{doc_id}")
async def delete_document_endpoint(doc_id: str, auth=Depends(require_session)):
    try:
        deleted = await remove_user_doc(doc_id, auth["oauth_user_id"])
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DELETE /documents/{{id}} Error] {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document.")