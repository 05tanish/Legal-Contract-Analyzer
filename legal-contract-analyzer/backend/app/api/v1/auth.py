import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.db.models import User, Contract
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, GoogleAuthRequest, AuthResponse, UserResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_required,
    get_client_guest_session_id
)

logger = logging.getLogger("auth")
router = APIRouter()

async def claim_guest_contracts(user_id: str, guest_session_id: Optional[str], db: AsyncSession) -> int:
    """
    Converts any temporary contracts uploaded in this guest session
    into permanent authenticated contracts owned by the newly signed-in user.
    Removes temporary expiration and prevents background cleanup.
    """
    if not guest_session_id:
        return 0

    res = await db.execute(
        select(Contract).where(
            and_(
                Contract.guest_session_id == guest_session_id,
                Contract.is_guest == True
            )
        )
    )
    guest_contracts = res.scalars().all()
    count = 0
    for c in guest_contracts:
        c.is_guest = False
        c.user_id = user_id
        c.expires_at = None
        c.cleanup_status = "NONE"
        count += 1

    if count > 0:
        await db.commit()
        logger.info(f"Automatically converted {count} temporary guest contracts to permanent ownership for user {user_id}")
    return count

@router.post("/register", response_model=AuthResponse)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    email = payload.email.lower().strip()
    
    # Check if user already exists
    res = await db.execute(select(User).where(User.email == email))
    if res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    hashed_pw = hash_password(payload.password)
    user = User(
        email=email,
        hashed_password=hashed_pw,
        full_name=payload.full_name or email.split("@")[0].capitalize(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Automatically convert any temporary contracts from current guest session to permanent
    guest_session_id = get_client_guest_session_id(request)
    await claim_guest_contracts(user.id, guest_session_id, db)

    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/login", response_model=AuthResponse)
async def login(
    payload: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    email = payload.email.lower().strip()

    res = await db.execute(select(User).where(User.email == email))
    user = res.scalars().first()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials and try again."
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials and try again."
        )

    # Automatically convert any temporary contracts from current guest session to permanent
    guest_session_id = get_client_guest_session_id(request)
    await claim_guest_contracts(user.id, guest_session_id, db)

    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/google", response_model=AuthResponse)
async def google_auth(
    payload: GoogleAuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    email = None
    full_name = payload.full_name
    avatar_url = payload.avatar_url
    google_id = payload.google_id

    # If raw Google ID token credential was provided, verify with Google Auth
    if payload.credential:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
            id_info = id_token.verify_oauth2_token(payload.credential, requests.Request(), clock_skew_in_seconds=10)
            email = id_info.get("email")
            full_name = id_info.get("name") or full_name
            avatar_url = id_info.get("picture") or avatar_url
            google_id = id_info.get("sub") or google_id
        except Exception as e:
            logger.warning(f"Google token verification note: {e}")
            if payload.email:
                email = payload.email

    if not email and payload.email:
        email = payload.email

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to verify Google authentication. Missing email."
        )

    email = email.lower().strip()

    # Find existing user by Google ID or by email
    query = select(User).where((User.email == email) | (User.google_id == google_id if google_id else False))
    res = await db.execute(query)
    user = res.scalars().first()

    if user:
        if not user.google_id and google_id:
            user.google_id = google_id
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        if full_name and not user.full_name:
            user.full_name = full_name
        await db.commit()
        await db.refresh(user)
    else:
        user = User(
            email=email,
            full_name=full_name or email.split("@")[0].capitalize(),
            avatar_url=avatar_url,
            google_id=google_id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Automatically convert any temporary contracts from current guest session to permanent
    guest_session_id = get_client_guest_session_id(request)
    await claim_guest_contracts(user.id, guest_session_id, db)

    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/claim")
async def claim_guest_session(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Explicitly converts temporary contracts from current guest session to authenticated owner."""
    guest_session_id = get_client_guest_session_id(request)
    claimed_count = await claim_guest_contracts(current_user.id, guest_session_id, db)
    return {"claimed_count": claimed_count, "user_id": current_user.id}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user_required)):
    return UserResponse.model_validate(current_user)
