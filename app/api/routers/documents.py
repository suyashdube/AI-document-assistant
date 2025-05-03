from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Dict, Any, List, Optional
import uuid
from pypdf import PdfReader
import io

from ...models.documents import DocumentCreate, Document, DocumentSensitivity, DocumentType
from ...utils.ai_service import ai_service
from ..dependencies import get_permit_user, check_permission

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)

@router.post("/", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    sensitivity: DocumentSensitivity = Form(DocumentSensitivity.INTERNAL),
    user: Dict[str, Any] = Depends(get_permit_user)
):
    """
    Upload a new document for processing and indexing.
    
    - Supported formats: PDF, TXT
    - Document will be processed and indexed for AI operations
    """
    # Verify user has upload permission
    await check_permission(
        user=user,
        action="upload",
        resource={"type": "document", "attributes": {"sensitivity": sensitivity}}
    )
    
    # Extract file content based on file type
    content = ""
    file_type = DocumentType.TXT  # Default
    
    # Determine file type from extension
    if file.filename:
        if file.filename.lower().endswith(".pdf"):
            file_type = DocumentType.PDF
            # Read PDF content
            file_content = await file.read()
            pdf = PdfReader(io.BytesIO(file_content))
            content = ""
            for page in pdf.pages:
                content += page.extract_text() + "\n\n"
        elif file.filename.lower().endswith(".txt"):
            file_type = DocumentType.TXT
            file_content = await file.read()
            content = file_content.decode("utf-8")
        elif file.filename.lower().endswith(".docx"):
            file_type = DocumentType.DOCX
            # In a real app, we'd use a library to extract text from DOCX
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="DOCX files are not yet supported"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {file.filename}"
            )
    
    # Use filename if name not provided
    if not name and file.filename:
        name = file.filename
    elif not name:
        name = f"Document-{uuid.uuid4()}"
    
    # Process the document (index, embed, etc.)
    doc_id, metadata = await ai_service.process_document(
        user=user,
        document_content=content,
        document_name=name,
        document_type=file_type,
        sensitivity=sensitivity
    )
    
    return {
        "id": doc_id,
        "name": name,
        "type": file_type,
        "sensitivity": sensitivity,
        "metadata": metadata
    }


@router.get("/", response_model=List[Dict[str, Any]])
async def list_documents(user: Dict[str, Any] = Depends(get_permit_user)):
    """
    List all documents the user has access to.
    """
    # Get all document IDs
    doc_ids = ai_service.get_document_ids()
    
    # Filter for documents the user can access
    accessible_docs = []
    
    for doc_id in doc_ids:
        doc = ai_service.get_document(doc_id)
        if not doc:
            continue
            
        # Check if user has read permission for this document
        try:
            await check_permission(
                user=user,
                action="read",
                resource={"type": "document", "id": doc_id}
            )
            # If we get here, the user has permission
            # Remove the content for the listing
            doc_info = {k: v for k, v in doc.items() if k != "content"}
            accessible_docs.append(doc_info)
        except HTTPException:
            # User doesn't have permission, skip this document
            pass
    
    return accessible_docs


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document(
    document_id: str,
    include_content: bool = False,
    user: Dict[str, Any] = Depends(get_permit_user)
):
    """
    Get details about a specific document.
    
    - Set include_content=true to include the document text content
    """
    # Get the document
    doc = ai_service.get_document(document_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found"
        )
    
    # Check if user has read permission
    await check_permission(
        user=user,
        action="read",
        resource={"type": "document", "id": document_id}
    )
    
    # If content is requested, check content access permission
    if include_content:
        await check_permission(
            user=user,
            action="read_content",
            resource={
                "type": "document_content", 
                "attributes": {
                    "document_id": document_id,
                    "sensitivity": doc.get("sensitivity", "internal")
                }
            }
        )
    else:
        # Remove content if not requested or permitted
        doc = {k: v for k, v in doc.items() if k != "content"}
    
    return doc 