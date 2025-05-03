from typing import Dict, Any, List, Tuple, Optional
from .permit_client import permit_client

class RAGProtection:
    """
    Second perimeter of defense: RAG Data Protection
    
    Controls access to retrieval-augmented generation (RAG) systems:
    - Pre-query filtering: Controls which data sources can be queried
    - Post-query filtering: Sanitizes results before model access
    - Enforces document-level access control
    """
    
    async def pre_query_filter(
        self, 
        user: Dict[str, Any],
        document_ids: List[str],
        operation_type: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Filter documents before retrieval based on user permissions.
        
        Args:
            user: User making the request
            document_ids: List of document IDs to be accessed
            operation_type: Type of operation being performed
            
        Returns:
            Tuple of (filtered_document_ids, context)
        """
        filtered_ids = []
        denied_ids = []
        
        # Check each document against user permissions
        for doc_id in document_ids:
            resource = {
                "type": "document",
                "id": doc_id
            }
            
            permitted = await permit_client.check_permission(
                user=user,
                action="read",  # For RAG, we need at least read permission
                resource=resource
            )
            
            if permitted:
                filtered_ids.append(doc_id)
            else:
                denied_ids.append(doc_id)
        
        # Return context for logging and auditing
        context = {
            "original_count": len(document_ids),
            "permitted_count": len(filtered_ids),
            "denied_count": len(denied_ids),
            "operation_type": operation_type
        }
        
        return filtered_ids, context
    
    async def post_query_filter(
        self,
        user: Dict[str, Any],
        query_results: List[Dict[str, Any]],
        operation_type: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter query results after retrieval but before AI processing.
        
        Args:
            user: User making the request
            query_results: List of results from the knowledge base
            operation_type: Type of operation being performed
            
        Returns:
            Tuple of (filtered_results, context)
        """
        filtered_results = []
        
        # Default to most restrictive filtering for lower tiers
        sensitive_fields = self._get_sensitive_fields_for_user(user)
        
        for result in query_results:
            # Check if this specific result requires additional permission
            if result.get("sensitivity") == "restricted":
                # Special check for restricted content
                resource = {
                    "type": "document_content",
                    "attributes": {
                        "document_id": result.get("id", "unknown"),
                        "sensitivity": result.get("sensitivity", "internal")
                    }
                }
                
                permitted = await permit_client.check_permission(
                    user=user,
                    action="access_sensitive_data",
                    resource=resource
                )
                
                if not permitted:
                    # Redact sensitive content
                    for field in sensitive_fields:
                        if field in result:
                            result[field] = "[REDACTED DUE TO PERMISSION RESTRICTIONS]"
            
            # Add the filtered result
            filtered_results.append(result)
        
        context = {
            "original_count": len(query_results),
            "filtered_count": len(filtered_results),
            "sensitive_fields_filtered": sensitive_fields
        }
        
        return filtered_results, context
    
    def _get_sensitive_fields_for_user(self, user: Dict[str, Any]) -> List[str]:
        """Determine which fields should be redacted based on user permissions."""
        tier = user.get("subscription_tier", "free").lower()
        role = user.get("role", "basic").lower()
        
        # Default sensitive fields to redact
        sensitive_fields = ["personal_data", "financial_details", "contact_info"]
        
        # Premium users can see more data
        if tier in ["premium", "enterprise"]:
            sensitive_fields.remove("contact_info")
            
        # Admins can see everything
        if role == "admin":
            return []
            
        return sensitive_fields

# Export singleton instance
rag_protection = RAGProtection() 