from typing import Optional
from fastapi import Header, HTTPException
from src.config.descope_config import descope_client
from src.repositories.user_repository import ensure_user

async def require_session(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing Bearer token.")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized: Empty token provided.")

    if not descope_client:
        raise HTTPException(status_code=500, detail="Descope client is not configured.")

    try:
        auth_info = descope_client.validate_session(session_token=token)
        
        # Descope Python SDK returns the claims dict directly at top level
        claims = auth_info if isinstance(auth_info, dict) else {}
        if "token" in claims and isinstance(claims["token"], dict):
            claims = claims["token"]
        elif "jwt" in claims and isinstance(claims["jwt"], dict):
            claims = claims["jwt"]

        oauth_user_id = str(
            claims.get("sub")
            or claims.get("userId")
            or (auth_info.get("sub") if isinstance(auth_info, dict) else "")
            or ""
        )

        if not oauth_user_id:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid sub claim.")

        email = claims.get("email") or (auth_info.get("email") if isinstance(auth_info, dict) else None)
        name = claims.get("name") or (auth_info.get("name") if isinstance(auth_info, dict) else None)
        
        user_row = ensure_user(oauth_user_id=oauth_user_id, email=email)

        return {
            "oauth_user_id": oauth_user_id,
            "email": email,
            "name": name,
            "user_id": str(user_row.get("id", "")),
            "token": claims
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: Session invalid or expired. {str(e)}")