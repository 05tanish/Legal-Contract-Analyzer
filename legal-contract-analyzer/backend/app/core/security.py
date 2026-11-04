import os
import hmac
import hashlib
import base64
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, Security, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User, Contract

# Secret key for JWT signing
JWT_SECRET = getattr(settings, "SECRET_KEY", "contractiq_enterprise_super_secret_legal_key_2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 14

security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = os.urandom(16)
    kdf = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{base64.b64encode(salt).decode('utf-8')}:{base64.b64encode(kdf).decode('utf-8')}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored salt and PBKDF2 hash."""
    try:
        salt_b64, hash_b64 = hashed_password.split(":")
        salt = base64.b64decode(salt_b64.encode('utf-8'))
        expected_hash = base64.b64decode(hash_b64.encode('utf-8'))
        kdf = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(kdf, expected_hash)
    except Exception:
        return False

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4)) if (len(data) % 4) != 0 else ''
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(payload: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed HMAC-SHA256 JWT token."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    header_b64 = _b64url_encode(header_json)

    to_encode = payload.copy()
    now = int(time.time())
    if expires_delta:
        exp = now + int(expires_delta.total_seconds())
    else:
        exp = now + (ACCESS_TOKEN_EXPIRE_DAYS * 86400)
    
    to_encode.update({"iat": now, "exp": exp})
    payload_json = json.dumps(to_encode, separators=(',', ':')).encode('utf-8')
    payload_b64 = _b64url_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"

def decode_access_token(token: str) -> Optional[dict]:
    """Verify and decode a signed HMAC-SHA256 JWT token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload = json.loads(_b64url_decode(payload_b64).decode('utf-8'))
        if payload.get("exp") and time.time() > payload["exp"]:
            return None # Expired

        return payload
    except Exception:
        return None

async def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Retrieve user if valid bearer token is present, else None."""
    if not auth or not auth.credentials:
        return None
    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        return None
    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def get_current_user_required(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Ensure user is logged in, or raise 401 Unauthorized."""
    user = await get_current_user_optional(auth, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to access this feature.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_client_guest_session_id(request: Request) -> Optional[str]:
    """Extract guest session identifier from HTTP headers, query params, or cookies."""
    header_val = request.headers.get("X-Guest-Session-ID") or request.headers.get("x-guest-session-id")
    if header_val and len(header_val.strip()) >= 8:
        return header_val.strip()
    
    query_val = request.query_params.get("guest_session_id") or request.query_params.get("session_id")
    if query_val and len(query_val.strip()) >= 8:
        return query_val.strip()

    cookie_val = request.cookies.get("contractiq_guest_session")
    if cookie_val and len(cookie_val.strip()) >= 8:
        return cookie_val.strip()
    return None

async def get_user_from_request_or_query(request: Request, db: AsyncSession) -> Optional[User]:
    """
    Retrieves user from Authorization header, query parameter ('token'), or cookie.
    Crucial for browser iframe requests where JavaScript cannot attach Authorization headers.
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    
    if not token:
        token = request.query_params.get("token")
        
    if not token:
        token = request.cookies.get("contractiq_auth_token")

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

def validate_contract_access(
    contract: Contract,
    user: Optional[User],
    guest_session_id: Optional[str]
) -> None:
    """
    Validates ownership and access rights for a contract.
    Protects against Insecure Direct Object References (IDOR).
    Prevents cross-guest and cross-user data leakage.
    Enforces TTL expiration for guest documents.
    """
    now = datetime.utcnow()

    # Check for expired guest contract
    if contract.is_guest and contract.expires_at and contract.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This temporary guest document has expired and was cleaned up. Please upload a new contract."
        )

    # If the contract is owned by an authenticated user
    if contract.user_id is not None:
        if user and user.id == contract.user_id:
            return
        # If user uploaded this in their current guest session before claiming
        if contract.guest_session_id and guest_session_id and contract.guest_session_id == guest_session_id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this contract."
        )

    # If the contract is a temporary guest document
    if contract.is_guest:
        # If guest session ID matches, allow access
        if contract.guest_session_id and guest_session_id and contract.guest_session_id == guest_session_id:
            return
        # If user is logged in and uploaded this contract in the current session
        if user and contract.guest_session_id and guest_session_id and contract.guest_session_id == guest_session_id:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to this temporary guest document."
        )

def require_authenticated_feature(user: Optional[User]):
    """
    Enforces that an authenticated user account is required for AI agents and full audits.
    Guests receive HTTP 403 Forbidden with prompt to sign in.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires an authenticated account. Please sign in or register to run complete LangGraph legal audits and access AI agents.",
            headers={"X-Auth-Required": "true"}
        )


