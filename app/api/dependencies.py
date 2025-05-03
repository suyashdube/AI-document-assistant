from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Dict, Any, Optional

from ..models.users import User, TokenData
from ..auth.token import decode_token
from ..ai_controls.permit_client import permit_client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Mock user database (in production, this would be a real database)
USERS_DB = {
    "user1": {
        "id": "user1",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "role": "admin",
        "subscription_tier": "enterprise",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
    },
    "user2": {
        "id": "user2",
        "email": "premium@example.com",
        "full_name": "Premium User",
        "role": "premium",
        "subscription_tier": "premium",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
    },
    "user3": {
        "id": "user3",
        "email": "basic@example.com",
        "full_name": "Basic User",
        "role": "basic",
        "subscription_tier": "free",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
    }
}

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get the current user from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the token
        payload = decode_token(token)
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
        
    # Get the user from the database
    user = USERS_DB.get(token_data.username)
    
    if user is None:
        raise credentials_exception
        
    # Remove the hashed password from the user data
    user_dict = {k: v for k, v in user.items() if k != "hashed_password"}
    
    # Add the key field for permit.io
    user_dict["key"] = user_dict["id"]
    
    return user_dict

async def get_permit_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Wrapper around get_current_user that ensures the user has proper format for Permit.io.
    """
    # Ensure the user has the required fields for Permit.io
    if "key" not in user:
        user["key"] = user["id"]
        
    return user

async def check_permission(
    user: Dict[str, Any] = Depends(get_permit_user),
    action: Optional[str] = None,
    resource: Optional[Dict[str, Any]] = None
):
    """
    Check if the user has permission to perform an action on a resource.
    
    This is a reusable dependency that can be parameterized in route definitions.
    """
    if action is None or resource is None:
        # Cannot check permissions without action and resource
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing action or resource for permission check"
        )
    
    # Check the permission
    permitted = await permit_client.check_permission(user, action, resource)
    
    if not permitted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied to {action} on {resource.get('type')}"
        )
        
    return True 