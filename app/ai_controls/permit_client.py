import os
from dotenv import load_dotenv
from permit import Permit, PermitConfig

load_dotenv()

class PermitClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PermitClient, cls).__new__(cls)
            cls._instance._init_permit()
        return cls._instance
    
    def _init_permit(self):
        api_key = os.getenv("PERMIT_API_KEY")
        pdp_url = os.getenv("PERMIT_PDP_URL", "http://localhost:7766")
        
        try:
            # Initialize permit client with local PDP for ABAC support
            # In newer versions, token cannot be None
            if not api_key:
                print("WARNING: PERMIT_API_KEY not set in environment variables")
                api_key = "dummy_key_for_development"
                
            # Initialize permit with the new SDK version format
            self.permit = Permit(
                pdp=pdp_url,
                token=api_key
            )
            print("Permit.io client initialized successfully")
        except Exception as e:
            print(f"Error initializing Permit.io client: {e}")
            # Initialize with a stub for development if permit is not available
            self.permit = None
    
    async def check_permission(self, user, action, resource, context=None):
        """
        Check if a user has permission to perform an action on a resource.
        
        Args:
            user (dict): User object with at least a "key" field
            action (str): The action to perform (e.g., "read", "write", "analyze")
            resource (dict): Resource object with at least "type" field
            context (dict, optional): Additional context for ABAC
            
        Returns:
            bool: True if permitted, False otherwise
        """
        # For development/testing mode - implement role-based permissions
        
        # Admin users can do everything except operations that need external access
        if user.get("role") == "admin":
            # Block admin users from specific operations that require external access
            if action == "execute" and resource.get("type") == "ai_operation":
                operation_type = resource.get("attributes", {}).get("operation_type")
                if operation_type in ["analyze", "translate"]:
                    print(f"Development mode: External access required for {operation_type} - denied even for admin")
                    return False
            
            print(f"Development mode: Allowing admin user {user.get('email')} to perform {action} on {resource.get('type')}")
            return True
            
        # Premium users can read documents and perform basic AI operations, but not upload
        elif user.get("role") == "premium":
            # Allow document access
            if resource.get("type") == "document" and action == "read":
                print(f"Development mode: Allowing premium user {user.get('email')} to read document")
                return True
                
            # Allow document content access for RAG
            if resource.get("type") == "document_content" and action == "read_content":
                print(f"Development mode: Allowing premium user {user.get('email')} to read document content")
                return True
                
            # Allow basic AI operations (summarize, extract, answer) but not analyze or translate
            if resource.get("type") == "ai_operation" and action == "execute":
                operation_type = resource.get("attributes", {}).get("operation_type")
                if operation_type in ["summarize", "extract", "answer"]:
                    print(f"Development mode: Allowing premium user {user.get('email')} to perform {operation_type}")
                    return True
                else:
                    print(f"Development mode: Denying premium user access to advanced operation: {operation_type}")
                    return False
            
            # Block uploads and other operations
            print(f"Development mode: Denying premium user {user.get('email')} to perform {action} on {resource.get('type')}")
            return False
            
        # Basic users can only read their own documents and use the 'answer' AI operation
        elif user.get("role") == "basic":
            # Only allow read access to documents they own
            if resource.get("type") == "document" and action == "read":
                doc_id = resource.get("id")
                if doc_id and doc_id.startswith(user.get("id", "")):
                    print(f"Development mode: Allowing basic user {user.get('email')} to read their own document")
                    return True
                return False
                
            # Only allow 'answer' AI operation
            if resource.get("type") == "ai_operation" and action == "execute":
                operation_type = resource.get("attributes", {}).get("operation_type")
                if operation_type == "answer":
                    print(f"Development mode: Allowing basic user {user.get('email')} to perform basic question answering")
                    return True
                else:
                    print(f"Development mode: Denying basic user access to advanced operation: {operation_type}")
                    return False
            
            # Block all other operations
            print(f"Development mode: Denying basic user {user.get('email')} to perform {action} on {resource.get('type')}")
            return False
            
        if not self.permit:
            # Default to permissive mode if permit client is not available
            print("WARNING: Permit client not available, defaulting to permissive mode")
            return True
            
        try:
            # Add any attributes from context to the resource
            if context and isinstance(resource, dict) and "attributes" not in resource:
                resource["attributes"] = context
                
            # Execute the permission check
            permitted = await self.permit.check(
                user=user,
                action=action,
                resource=resource
            )
            return permitted
        except Exception as e:
            print(f"Error checking permission: {e}")
            # Fail closed if there's an error
            return False

# Export singleton instance
permit_client = PermitClient() 