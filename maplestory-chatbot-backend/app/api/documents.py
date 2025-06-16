# app/api/documents.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.models.document import DocumentUploadResponse
from app.services.document_processor import DocumentProcessor
from app.services.langchain_service import LangChainService
import logging
import os
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

document_processor = DocumentProcessor()
langchain_service = LangChainService()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """문서 업로드 및 처리"""
    try:
        # 파일 유효성 검사
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")
        
        # 고유 파일명 생성
        document_id = str(uuid.uuid4())
        filename = f"{document_id}_{file.filename}"
        file_path = f"./data/pdfs/{filename}"
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 백그라운드 작업으로 문서 처리
        background_tasks.add_task(process_document_background, file_path, document_id)
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="processing",
            chunks_created=0,
            message="문서 업로드 완료. 처리 중입니다."
        )
        
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_document_background(file_path: str, document_id: str):
    """백그라운드에서 문서 처리"""
    try:
        # 문서 처리
        documents = await document_processor.process_pdf(file_path)
        
        # 벡터 스토어에 추가
        await langchain_service.add_documents(documents)
        
        logger.info(f"Document {document_id} processed: {len(documents)} chunks")
        
    except Exception as e:
        logger.error(f"Background processing error: {str(e)}")

@router.get("/")
async def list_documents():
    """업로드된 문서 목록"""
    try:
        pdf_dir = "./data/pdfs"
        if not os.path.exists(pdf_dir):
            return {"documents": []}
        
        documents = []
        for filename in os.listdir(pdf_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(pdf_dir, filename)
                stat = os.stat(file_path)
                documents.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime
                })
        
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"List documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 