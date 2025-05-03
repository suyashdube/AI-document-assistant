from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class AIOperationType(str, Enum):
    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    ANALYZE = "analyze"
    TRANSLATE = "translate"
    ANSWER = "answer"

class PromptRequest(BaseModel):
    document_id: str
    operation_type: AIOperationType
    prompt: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
class PromptResponse(BaseModel):
    document_id: str
    operation_type: AIOperationType
    prompt: str
    response: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AIOperationLog(BaseModel):
    id: str
    user_id: str
    document_id: str
    operation_type: AIOperationType
    prompt: str
    response: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict) 