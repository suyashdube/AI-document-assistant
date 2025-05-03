import re
from typing import Dict, Any, Tuple, Optional
from .permit_client import permit_client

class PromptFiltering:
    """
    First perimeter of defense: Prompt Filtering
    
    This class validates and authorizes prompts before they reach the AI model.
    - Checks for harmful inputs (injections, etc.)
    - Verifies user permissions for prompt operations
    - Enforces rate limits and other restrictions
    """
    
    # Basic patterns to check for potentially harmful content
    HARMFUL_PATTERNS = [
        r"(DROP|DELETE|UPDATE|INSERT).*TABLE",  # SQL injections
        r"<script.*?>.*?</script>",              # XSS attempts
        r"system\.([a-zA-Z0-9_]+\()",           # System calls
        r"exec\s*\(",                           # Code execution attempts
        r"eval\s*\(",                           # Eval attempts
    ]
    
    async def filter_prompt(
        self, 
        user: Dict[str, Any], 
        prompt: str, 
        operation_type: str, 
        document_type: str,
        document_sensitivity: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Filter and authorize a prompt before it reaches the AI model.
        
        Args:
            user: User making the request
            prompt: The raw prompt text
            operation_type: Type of operation (summarize, extract, etc.)
            document_type: Type of document being processed
            document_sensitivity: Sensitivity level of the document
            
        Returns:
            Tuple of (is_permitted, filtered_prompt, context)
        """
        # Step 1: Check for harmful content patterns
        for pattern in self.HARMFUL_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return False, "Prompt contains potentially harmful content", None
        
        # Step 2: Check length limits based on user subscription
        if len(prompt) > self._get_max_prompt_length(user):
            return False, f"Prompt exceeds maximum length for your subscription tier", None
        
        # Step 3: Check permissions with Permit.io
        resource = {
            "type": "ai_prompt",
            "attributes": {
                "operation_type": operation_type,
                "document_type": document_type,
                "document_sensitivity": document_sensitivity,
                "prompt_length": len(prompt)
            }
        }
        
        permitted = await permit_client.check_permission(
            user=user,
            action="execute",
            resource=resource
        )
        
        if not permitted:
            return False, "You don't have permission to execute this type of prompt", None
        
        # Step 4: Apply any prompt transformations or augmentations
        filtered_prompt = self._sanitize_prompt(prompt)
        
        # Return the filtered prompt and context for the AI
        return True, filtered_prompt, {
            "prompt_filtered": True,
            "original_length": len(prompt),
            "filtered_length": len(filtered_prompt)
        }
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize a prompt by removing potentially harmful elements."""
        # For now, just basic cleaning
        return prompt.strip()
    
    def _get_max_prompt_length(self, user: Dict[str, Any]) -> int:
        """Get maximum prompt length based on user subscription."""
        # Default limits based on subscription tier
        tier_limits = {
            "free": 500,
            "standard": 1500,
            "premium": 4000,
            "enterprise": 8000
        }
        
        # Get user's subscription tier, default to lowest if not found
        tier = user.get("subscription_tier", "free").lower()
        return tier_limits.get(tier, 500)

# Export singleton instance
prompt_filtering = PromptFiltering() 