from typing import Dict, Any, Optional, Tuple
import uuid
from enum import Enum
from .permit_client import permit_client

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ExternalAccessControl:
    """
    Third perimeter of defense: Secure External Access
    
    Manages AI agent access to external systems:
    - Controls which external tools/APIs can be accessed
    - Enforces human-in-the-loop approvals for sensitive operations
    - Tracks actions performed by AI on behalf of users
    """
    
    # In-memory store of operation approvals (would be a database in production)
    _approval_requests = {}
    
    async def check_external_access(
        self,
        user: Dict[str, Any],
        ai_agent: Dict[str, Any],
        external_system: str,
        operation: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check if an AI agent can access an external system on behalf of a user.
        
        Args:
            user: The user the AI is acting on behalf of
            ai_agent: The AI agent's identity
            external_system: The system to be accessed (API, database, etc.)
            operation: The operation to perform
            context: Additional operation context
            
        Returns:
            Tuple of (is_permitted, operation_id, result_context)
        """
        # Step 1: Check if the AI agent itself has permission to access this system
        agent_resource = {
            "type": "external_system",
            "attributes": {
                "system_name": external_system,
                "operation": operation
            }
        }
        
        agent_permitted = await permit_client.check_permission(
            user=ai_agent,
            action="access",
            resource=agent_resource
        )
        
        if not agent_permitted:
            return False, None, {"reason": "AI agent lacks permission to access this system"}
        
        # Step 2: Check if the user has permission to perform this operation
        user_resource = {
            "type": "external_operation",
            "attributes": {
                "system_name": external_system,
                "operation": operation,
                "via_ai_agent": True,
                **context
            }
        }
        
        user_permitted = await permit_client.check_permission(
            user=user,
            action="execute",
            resource=user_resource
        )
        
        if not user_permitted:
            return False, None, {"reason": "User lacks permission for this operation"}
        
        # Step 3: Check if this operation requires approval
        requires_approval = await self._check_if_requires_approval(
            user, ai_agent, external_system, operation, context
        )
        
        if requires_approval:
            # Create an approval request ID
            operation_id = str(uuid.uuid4())
            
            # Store the approval request for later reference
            self._approval_requests[operation_id] = {
                "status": ApprovalStatus.PENDING,
                "user": user,
                "ai_agent": ai_agent,
                "external_system": external_system,
                "operation": operation,
                "context": context,
                "created_at": self._get_current_timestamp()
            }
            
            return False, operation_id, {
                "reason": "Operation requires approval",
                "approval_status": ApprovalStatus.PENDING,
                "operation_id": operation_id
            }
        
        # If no approval needed, operation is permitted
        return True, None, {"reason": "Operation permitted without approval"}
    
    async def get_approval_status(self, operation_id: str) -> Dict[str, Any]:
        """Get the current status of an approval request."""
        if operation_id not in self._approval_requests:
            return {
                "status": "not_found",
                "message": "Approval request not found"
            }
        
        request = self._approval_requests[operation_id]
        return {
            "status": request["status"],
            "operation": request["operation"],
            "external_system": request["external_system"],
            "created_at": request["created_at"]
        }
    
    async def process_approval(
        self,
        operation_id: str,
        approver: Dict[str, Any],
        approved: bool,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an approval request for an operation.
        
        Args:
            operation_id: The ID of the operation to approve/reject
            approver: The user approving/rejecting the request
            approved: Whether the operation is approved
            reason: Optional reason for approval/rejection
            
        Returns:
            Dict with approval result
        """
        if operation_id not in self._approval_requests:
            return {
                "status": "error",
                "message": "Approval request not found"
            }
        
        request = self._approval_requests[operation_id]
        
        # Check if approver has permission to approve this request
        resource = {
            "type": "approval_request",
            "attributes": {
                "external_system": request["external_system"],
                "operation": request["operation"],
                "user_id": request["user"].get("id", "unknown"),
                "ai_agent_id": request["ai_agent"].get("id", "unknown")
            }
        }
        
        can_approve = await permit_client.check_permission(
            user=approver,
            action="approve",
            resource=resource
        )
        
        if not can_approve:
            return {
                "status": "error",
                "message": "You don't have permission to approve this request"
            }
        
        # Update approval status
        new_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request["status"] = new_status
        request["approver"] = approver
        request["approved_at"] = self._get_current_timestamp()
        request["reason"] = reason
        
        self._approval_requests[operation_id] = request
        
        return {
            "status": "success",
            "approval_status": new_status,
            "message": f"Operation {new_status}",
            "operation_id": operation_id
        }
    
    async def _check_if_requires_approval(
        self,
        user: Dict[str, Any],
        ai_agent: Dict[str, Any],
        external_system: str,
        operation: str,
        context: Dict[str, Any]
    ) -> bool:
        """Check if an operation requires human approval."""
        # High-risk operations always require approval
        high_risk_operations = ["payment", "delete", "user_creation", "data_export"]
        if any(risk_op in operation.lower() for risk_op in high_risk_operations):
            return True
            
        # Check based on operation context (e.g., amount for payment operations)
        if "amount" in context and float(context["amount"]) > 100:
            return True
            
        # For non-admin users, certain systems always require approval
        sensitive_systems = ["payment_gateway", "user_management", "admin_console"]
        if external_system in sensitive_systems and user.get("role") != "admin":
            return True
            
        # Default to no approval required
        return False
    
    def _get_current_timestamp(self) -> int:
        """Get current timestamp in seconds."""
        import time
        return int(time.time())

# Export singleton instance
external_access_control = ExternalAccessControl() 