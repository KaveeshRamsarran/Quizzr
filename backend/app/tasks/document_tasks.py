"""
Document Processing Tasks
PDF extraction, OCR, and chunking background tasks
"""

import re
from datetime import datetime
from typing import Optional, List
import structlog

try:
    from celery import shared_task
except ImportError:
    from app.celery_mock import shared_task

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.models.document import Document, DocumentPage, Chunk, ProcessingStatus, DocumentStyle
from app.models.job import ProcessingJob, JobStatus, JobType, JobLog

logger = structlog.get_logger()


def get_sync_session() -> Session:
    """Get a synchronous database session for Celery tasks"""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3
)
def process_document_task(self, job_id: int) -> dict:
    """
    Main document processing task
    Extracts text from PDF, runs OCR if needed, and creates chunks
    """
    session = get_sync_session()
    
    try:
        # Get job and document
        job = session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        ).scalar_one_or_none()
        
        if not job:
            return {"error": "Job not found"}
        
        document = session.execute(
            select(Document).where(Document.id == job.document_id)
        ).scalar_one_or_none()
        
        if not document:
            job.status = JobStatus.FAILED
            job.error_message = "Document not found"
            session.commit()
            return {"error": "Document not found"}
        
        # Update status
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.celery_task_id = self.request.id
        document.status = ProcessingStatus.EXTRACTING
        session.commit()
        
        _log_job(session, job.id, "info", "Starting document processing")
        
        # Step 1: Extract text from PDF
        job.current_step = "Extracting text"
        session.commit()
        
        pages_data = extract_pdf_text(document.file_path)
        
        if not pages_data:
            raise ValueError("Failed to extract any text from PDF")
        
        document.page_count = len(pages_data)
        
        # Step 2: Check for low-text pages and run OCR if needed
        ocr_pages = []
        ocr_threshold = job.parameters.get("ocr_threshold", 50) if job.parameters else 50
        
        for page_data in pages_data:
            text_length = len(page_data.get("text", ""))
            
            if text_length < ocr_threshold and job.parameters.get("ocr_enabled", True):
                # Run OCR on this page
                job.current_step = f"Running OCR on page {page_data['page_number']}"
                session.commit()
                
                ocr_text, confidence = run_ocr_on_page(
                    document.file_path,
                    page_data["page_number"]
                )
                
                if ocr_text and len(ocr_text) > text_length:
                    page_data["text"] = ocr_text
                    page_data["used_ocr"] = True
                    page_data["ocr_confidence"] = confidence
                    ocr_pages.append(page_data["page_number"])
        
        if ocr_pages:
            document.ocr_used = True
            document.ocr_pages = ocr_pages
            _log_job(session, job.id, "info", f"OCR used on {len(ocr_pages)} pages")
        
        # Step 3: Save pages to database
        job.current_step = "Saving pages"
        session.commit()
        
        for page_data in pages_data:
            page = DocumentPage(
                document_id=document.id,
                page_number=page_data["page_number"],
                text_content=page_data.get("text", ""),
                text_length=len(page_data.get("text", "")),
                used_ocr=page_data.get("used_ocr", False),
                ocr_confidence=page_data.get("ocr_confidence"),
                headings_on_page=page_data.get("headings"),
                has_tables=page_data.get("has_tables", False),
                has_images=page_data.get("has_images", False)
            )
            session.add(page)
        
        session.commit()
        
        # Step 4: Detect document style
        job.current_step = "Analyzing structure"
        session.commit()
        
        style, headings = analyze_document_structure(pages_data)
        document.style = style
        document.headings = headings
        
        # Step 5: Create chunks
        job.current_step = "Creating study chunks"
        document.status = ProcessingStatus.CHUNKING
        session.commit()
        
        chunks_data = create_chunks(pages_data, style)
        
        for idx, chunk_data in enumerate(chunks_data):
            chunk = Chunk(
                document_id=document.id,
                chunk_index=idx,
                start_page=chunk_data["start_page"],
                end_page=chunk_data["end_page"],
                content=chunk_data["content"],
                content_length=len(chunk_data["content"]),
                heading_context=chunk_data.get("heading_context"),
                parent_heading=chunk_data.get("parent_heading"),
                key_terms=chunk_data.get("key_terms"),
                content_type=chunk_data.get("content_type", "text")
            )
            session.add(chunk)
        
        # Finalize
        document.status = ProcessingStatus.COMPLETED
        document.processed_at = datetime.utcnow()
        
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.current_step = "Completed"
        job.progress = 100
        job.result = {
            "page_count": document.page_count,
            "chunk_count": len(chunks_data),
            "ocr_pages": len(ocr_pages),
            "style": style.value
        }
        
        session.commit()
        
        _log_job(
            session, job.id, "info",
            f"Document processed: {document.page_count} pages, {len(chunks_data)} chunks"
        )
        
        return {
            "success": True,
            "document_id": document.id,
            "page_count": document.page_count,
            "chunk_count": len(chunks_data)
        }
    
    except Exception as e:
        logger.error("Document processing failed", error=str(e), job_id=job_id)
        
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            _log_job(session, job.id, "error", f"Processing failed: {str(e)}")
        
        if document:
            document.status = ProcessingStatus.FAILED
            document.processing_error = str(e)
        
        session.commit()
        raise
    
    finally:
        session.close()


def extract_pdf_text(file_path: str) -> List[dict]:
    """Extract text from PDF file page by page"""
    import pdfplumber
    
    pages_data = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                
                # Detect headings (simple heuristic: lines that are short and don't end with period)
                headings = []
                for line in text.split("\n"):
                    line = line.strip()
                    if line and len(line) < 100 and not line.endswith(".") and line[0].isupper():
                        headings.append(line)
                
                # Check for tables
                tables = page.extract_tables()
                has_tables = len(tables) > 0
                
                # Check for images (approximate via page content)
                has_images = len(page.images) > 0 if hasattr(page, 'images') else False
                
                pages_data.append({
                    "page_number": page_num,
                    "text": text,
                    "headings": headings[:5],  # Limit to 5 headings per page
                    "has_tables": has_tables,
                    "has_images": has_images,
                    "used_ocr": False
                })
    
    except Exception as e:
        logger.error("PDF extraction failed", error=str(e))
        # Fallback to PyPDF2
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                pages_data.append({
                    "page_number": page_num,
                    "text": text,
                    "headings": [],
                    "has_tables": False,
                    "has_images": False,
                    "used_ocr": False
                })
        except Exception as e2:
            logger.error("PyPDF2 fallback failed", error=str(e2))
    
    return pages_data


def run_ocr_on_page(file_path: str, page_number: int) -> tuple:
    """Run OCR on a specific page"""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        
        # Convert page to image
        images = convert_from_path(
            file_path,
            first_page=page_number,
            last_page=page_number,
            dpi=300
        )
        
        if not images:
            return "", 0.0
        
        image = images[0]
        
        # Run OCR
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Extract text and calculate confidence
        text_parts = []
        confidences = []
        
        for i, word in enumerate(ocr_data["text"]):
            if word.strip():
                text_parts.append(word)
                conf = ocr_data["conf"][i]
                if conf > 0:
                    confidences.append(conf)
        
        text = " ".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return text, avg_confidence / 100  # Normalize to 0-1
    
    except Exception as e:
        logger.error("OCR failed", error=str(e), page=page_number)
        return "", 0.0


def analyze_document_structure(pages_data: List[dict]) -> tuple:
    """Analyze document structure and classify style"""
    total_pages = len(pages_data)
    total_text = sum(len(p.get("text", "")) for p in pages_data)
    avg_text_per_page = total_text / total_pages if total_pages > 0 else 0
    
    # Collect all headings
    all_headings = []
    for page in pages_data:
        all_headings.extend(page.get("headings", []))
    
    # Count bullet points and short paragraphs (slide indicators)
    bullet_count = 0
    short_para_count = 0
    
    for page in pages_data:
        text = page.get("text", "")
        bullet_count += text.count("•") + text.count("-") + text.count("*")
        paragraphs = text.split("\n\n")
        short_para_count += sum(1 for p in paragraphs if len(p) < 200)
    
    # Classify style
    if avg_text_per_page < 300 and bullet_count > total_pages:
        style = DocumentStyle.SLIDES
    elif avg_text_per_page > 1000:
        style = DocumentStyle.TEXTBOOK
    elif "lab" in " ".join(all_headings).lower() or "experiment" in " ".join(all_headings).lower():
        style = DocumentStyle.LAB
    else:
        style = DocumentStyle.NOTES
    
    # Build heading structure
    heading_structure = {}
    current_main = None
    
    for heading in all_headings:
        # Simple heuristic: shorter headings are main headings
        if len(heading) < 50:
            current_main = heading
            heading_structure[heading] = []
        elif current_main:
            heading_structure[current_main].append(heading)
    
    return style, heading_structure


def create_chunks(pages_data: List[dict], style: DocumentStyle) -> List[dict]:
    """Create study chunks from page data"""
    chunks = []
    
    if style == DocumentStyle.SLIDES:
        # For slides: each page is roughly a chunk
        for page in pages_data:
            text = page.get("text", "").strip()
            if len(text) > 50:  # Minimum content
                chunks.append({
                    "start_page": page["page_number"],
                    "end_page": page["page_number"],
                    "content": text,
                    "heading_context": page.get("headings", [""])[0] if page.get("headings") else None,
                    "content_type": "text"
                })
    else:
        # For notes/textbook: chunk by headings or ~500 words
        current_chunk = {
            "start_page": 1,
            "end_page": 1,
            "content": "",
            "heading_context": None
        }
        
        for page in pages_data:
            text = page.get("text", "")
            headings = page.get("headings", [])
            
            # If we hit a major heading or content is too long, start new chunk
            if headings and len(current_chunk["content"]) > 500:
                # Save current chunk
                if current_chunk["content"].strip():
                    chunks.append(current_chunk)
                
                # Start new chunk
                current_chunk = {
                    "start_page": page["page_number"],
                    "end_page": page["page_number"],
                    "content": text,
                    "heading_context": headings[0] if headings else None
                }
            else:
                # Add to current chunk
                current_chunk["content"] += "\n\n" + text
                current_chunk["end_page"] = page["page_number"]
        
        # Add final chunk
        if current_chunk["content"].strip():
            chunks.append(current_chunk)
    
    # Extract key terms from each chunk
    for chunk in chunks:
        chunk["key_terms"] = extract_key_terms(chunk["content"])
        chunk["content_type"] = detect_content_type(chunk["content"])
    
    return chunks


def extract_key_terms(text: str) -> List[str]:
    """Extract key terms from text using simple heuristics"""
    # Find capitalized terms (potential proper nouns/technical terms)
    words = text.split()
    terms = set()
    
    for word in words:
        # Clean word
        clean = re.sub(r'[^\w\s]', '', word)
        
        # Check if it's a potential term
        if clean and len(clean) > 3 and clean[0].isupper():
            terms.add(clean)
    
    # Look for terms in quotes
    quoted = re.findall(r'"([^"]+)"', text)
    terms.update(quoted)
    
    # Look for bold-style indicators (often key terms)
    bold_style = re.findall(r'\*\*([^*]+)\*\*', text)
    terms.update(bold_style)
    
    return list(terms)[:20]  # Limit to 20 terms


def detect_content_type(text: str) -> str:
    """Detect the type of content in text"""
    text_lower = text.lower()
    
    # Check for formulas
    if re.search(r'[=+\-*/^].*\d', text) or re.search(r'\d.*[=+\-*/^]', text):
        if any(char in text for char in ['∫', '∑', '√', 'Σ', 'π']):
            return "formula"
    
    # Check for definitions
    if re.search(r'\b(is defined as|refers to|means|is the)\b', text_lower):
        return "definition"
    
    # Check for processes/steps
    if re.search(r'\b(step \d|first|second|third|then|next|finally)\b', text_lower):
        return "process"
    
    return "text"


def _log_job(session: Session, job_id: int, level: str, message: str) -> None:
    """Add a log entry to a job"""
    log = JobLog(
        job_id=job_id,
        level=level,
        message=message
    )
    session.add(log)
    session.commit()
