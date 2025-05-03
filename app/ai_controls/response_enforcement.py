from typing import Dict, Any, Optional, Tuple, List
import re
from .permit_client import permit_client

class ResponseEnforcement:
    """
    Fourth perimeter of defense: Response Enforcement
    
    Controls AI-generated outputs:
    - Applies content moderation to responses
    - Enforces role-based content visibility
    - Ensures compliance with legal and organizational policies
    """
    
    # Define patterns to detect sensitive information
    SENSITIVE_PATTERNS = {
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "api_key": r"\b(?:sk|pk|api[_-]key)_[a-zA-Z0-9]{20,}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"
    }
    
    # Response categories for content moderation
    RESPONSE_CATEGORIES = [
        "contains_pii",
        "contains_financial_data",
        "contains_legal_advice",
        "contains_medical_info",
        "contains_offensive_content"
    ]
    
    async def filter_response(
        self,
        user: Dict[str, Any],
        original_response: str,
        operation_type: str,
        document_ids: List[str],
        context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Filter and control AI-generated responses before sending them to users.
        
        Args:
            user: User receiving the response
            original_response: The raw AI-generated response
            operation_type: Type of operation that was performed
            document_ids: IDs of documents used to generate response
            context: Additional context about the operation
            
        Returns:
            Tuple of (filtered_response, result_context)
        """
        # Step 1: Detect sensitive information in the response
        detected_patterns = self._detect_sensitive_information(original_response)
        
        # Step 2: Categorize the response content
        categories = self._categorize_response(original_response)
        
        # Step 3: Check user's permission to view each category of content
        filtered_response = original_response
        redactions = []
        
        for category in categories:
            # Skip empty categories
            if not categories[category]:
                continue
                
            resource = {
                "type": "ai_response",
                "attributes": {
                    "operation_type": operation_type,
                    "document_ids": document_ids,
                    "content_category": category
                }
            }
            
            permitted = await permit_client.check_permission(
                user=user,
                action="view",
                resource=resource
            )
            
            if not permitted:
                # If not permitted, we need to redact this content
                redactions.append({
                    "category": category,
                    "reason": "Permission denied for this content category"
                })
                
                # Perform the redaction
                filtered_response = self._redact_content_category(
                    filtered_response, 
                    category, 
                    categories[category]
                )
        
        # Step 4: Redact any detected sensitive information based on user's permissions
        for pattern_type, matches in detected_patterns.items():
            if not matches:
                continue
                
            # Check permission for this specific type of sensitive data
            resource = {
                "type": "sensitive_data",
                "attributes": {
                    "data_type": pattern_type,
                    "operation_type": operation_type
                }
            }
            
            permitted = await permit_client.check_permission(
                user=user,
                action="access_sensitive_data",
                resource=resource
            )
            
            if not permitted:
                # Redact this sensitive information
                redactions.append({
                    "category": f"sensitive_{pattern_type}",
                    "reason": f"Permission denied for {pattern_type} data"
                })
                
                # Apply pattern-specific redaction
                for match in matches:
                    filtered_response = filtered_response.replace(
                        match, 
                        f"[REDACTED {pattern_type.upper()}]"
                    )
        
        # Return the filtered response and context
        result_context = {
            "original_length": len(original_response),
            "filtered_length": len(filtered_response),
            "categories_detected": categories,
            "sensitive_data_detected": {k: bool(v) for k, v in detected_patterns.items()},
            "redactions_applied": redactions
        }
        
        return filtered_response, result_context
    
    def _detect_sensitive_information(self, text: str) -> Dict[str, List[str]]:
        """Detect patterns of sensitive information in text."""
        results = {}
        
        for pattern_type, pattern in self.SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, text)
            results[pattern_type] = matches
            
        return results
    
    def _categorize_response(self, text: str) -> Dict[str, List[str]]:
        """
        Categorize response content based on its characteristics.
        
        In a production system, this would use more sophisticated NLP/ML techniques.
        This simplified version just uses basic keyword matching.
        """
        categories = {category: [] for category in self.RESPONSE_CATEGORIES}
        
        # Very simplified categorization based on keywords
        if re.search(r"(?:SSN|social security|address|phone|email|date of birth)", text, re.IGNORECASE):
            categories["contains_pii"].append("Detected PII keywords")
            
        if re.search(r"(?:account|payment|credit card|bank|invoice|tax)", text, re.IGNORECASE):
            categories["contains_financial_data"].append("Detected financial keywords")
            
        if re.search(r"(?:legal advice|lawsuit|court|lawyer|attorney|law requires)", text, re.IGNORECASE):
            categories["contains_legal_advice"].append("Detected legal advice")
            
        if re.search(r"(?:medical|diagnosis|treatment|patient|doctor|health condition)", text, re.IGNORECASE):
            categories["contains_medical_info"].append("Detected medical information")
            
        if re.search(r"(?:offensive|explicit|violent|inappropriate)", text, re.IGNORECASE):
            categories["contains_offensive_content"].append("Detected potentially offensive content")
            
        return categories
    
    def _redact_content_category(self, text: str, category: str, reasons: List[str]) -> str:
        """
        Redact content of a specific category from the text.
        
        In a real implementation, this would use more sophisticated NLP techniques
        to identify and redact specific sections. This simplified version uses
        a disclaimer approach.
        """
        # Add a disclaimer about redacted content
        disclaimer = f"\n\n[SOME CONTENT HAS BEEN REDACTED: {category}]\n"
        
        if category == "contains_pii":
            # Use regex to redact patterns that look like PII
            text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED EMAIL]", text)
            text = re.sub(r"\b(?:\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b", "[REDACTED PHONE]", text)
            
        elif category == "contains_financial_data":
            # Redact financial information
            text = re.sub(r"\$\d+(,\d{3})*(\.\d{2})?", "[REDACTED AMOUNT]", text)
            text = re.sub(r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED CARD NUMBER]", text)
            
        elif category == "contains_legal_advice":
            # Add disclaimer that this isn't legal advice
            disclaimer += "Note: This AI cannot provide legal advice. Please consult a qualified attorney.\n"
            
        elif category == "contains_medical_info":
            # Add disclaimer about medical information
            disclaimer += "Note: This AI cannot provide medical advice. Please consult a healthcare provider.\n"
            
        elif category == "contains_offensive_content":
            # For offensive content, we would use content moderation tools
            # This is a simplified approach
            text = re.sub(r"(?i)(?:offensive|explicit|violent|inappropriate)", "[REDACTED]", text)
        
        return text + disclaimer

# Export singleton instance
response_enforcement = ResponseEnforcement() 