from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class DocumentType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    CSV = "csv"

class DocumentSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class Document(BaseModel):
    id: str
    name: str
    type: DocumentType
    owner_id: str
    content: Optional[str] = None
    sensitivity: DocumentSensitivity = DocumentSensitivity.INTERNAL
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentCreate(BaseModel):
    name: str
    type: DocumentType
    sensitivity: DocumentSensitivity = DocumentSensitivity.INTERNAL
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    sensitivity: Optional[DocumentSensitivity] = None
    metadata: Optional[Dict[str, Any]] = None 