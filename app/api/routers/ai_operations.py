from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from ...models.ai_operations import AIOperationType, PromptRequest, PromptResponse
from ...utils.ai_service import ai_service
from ..dependencies import get_permit_user, check_permission
from ...ai_controls.external_access import external_access_control

router = APIRouter(
    prefix="/ai",
    tags=["ai_operations"]
)

@router.post("/prompt", response_model=Dict[str, Any])
async def execute_ai_prompt(
    request: PromptRequest,
    user: Dict[str, Any] = Depends(get_permit_user)
):
    """
    Execute an AI operation on a document with a specific prompt.
    
    This endpoint applies all four perimeters of the AI access control framework:
    1. Prompt Filtering - Validates and authorizes the prompt
    2. RAG Data Protection - Controls access to document data
    3. External Access Control - Manages API access for certain operations
    4. Response Enforcement - Filters and controls AI-generated output
    """
    # First, check basic permission for the operation type
    await check_permission(
        user=user,
        action="execute",
        resource={
            "type": "ai_operation",
            "attributes": {"operation_type": request.operation_type}
        }
    )
    
    # Execute the AI operation
    result = await ai_service.execute_ai_operation(
        user=user,
        operation_type=request.operation_type,
        document_ids=[request.document_id],
        prompt=request.prompt
    )
    
    # Check if the operation requires approval
    if "status" in result and result["status"] == "pending_approval":
        return {
            "status": "pending_approval",
            "message": result["message"],
            "operation_id": result["operation_id"]
        }
    
    # Check if there was an error
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "operation_id": result["operation_id"],
        "response": result["response"],
        "document_id": request.document_id,
        "operation_type": request.operation_type
    }

@router.get("/approvals", response_model=List[Dict[str, Any]])
async def list_pending_approvals(user: Dict[str, Any] = Depends(get_permit_user)):
    """
    List all pending approval requests the user can approve.
    
    For simplicity, this is a stub implementation. In a real application,
    this would query a database of pending approvals.
    """
    # For simplicity, stub implementation
    return []

@router.post("/approvals/{operation_id}/approve", response_model=Dict[str, Any])
async def approve_operation(
    operation_id: str,
    reason: str = "",
    user: Dict[str, Any] = Depends(get_permit_user)
):
    """
    Approve a pending AI operation.
    """
    # Process the approval
    result = await external_access_control.process_approval(
        operation_id=operation_id,
        approver=user,
        approved=True,
        reason=reason
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result

@router.post("/approvals/{operation_id}/reject", response_model=Dict[str, Any])
async def reject_operation(
    operation_id: str,
    reason: str = "",
    user: Dict[str, Any] = Depends(get_permit_user)
):
    """
    Reject a pending AI operation.
    """
    # Process the rejection
    result = await external_access_control.process_approval(
        operation_id=operation_id,
        approver=user,
        approved=False,
        reason=reason
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result 