import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException

# Ensure backend root on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.models import Contract, User
from app.core.security import validate_contract_access, require_authenticated_feature
from app.services.clause_detection.detector import clause_detector
from app.services.cleanup.guest_cleanup_service import GuestCleanupService

def test_clause_detection():
    print("[TEST 1] Testing Lightweight Clause Detection (CUAD ML + Heuristics)...")
    sample_chunks = [
        {
            "id": "c1",
            "page_number": 1,
            "section_title": "Section 9. Restraint of Trade",
            "content": "Employee covenants not to compete with the Company in India for three years post termination."
        },
        {
            "id": "c2",
            "page_number": 3,
            "section_title": "Section 14. Liability Cap",
            "content": "The maximum aggregate liability under this agreement shall be subject to a strict cap on liability."
        },
        {
            "id": "c3",
            "page_number": 5,
            "section_title": "Section 21. Confidentiality",
            "content": "Each party shall maintain all proprietary and confidential information in strict confidence."
        }
    ]
    detected = clause_detector.detect_clauses_in_chunks(sample_chunks)
    assert len(detected) >= 2, f"Expected >= 2 detected clauses, got {len(detected)}"
    categories = [d["category_id"] for d in detected]
    assert any("non_compete" in c for c in categories), "non_compete not detected"
    assert any("liability" in c for c in categories), "liability not detected"
    print(f"  -> PASSED: Successfully detected {len(detected)} clauses: {categories}")

def test_auth_and_idor():
    print("[TEST 2] Testing Ownership & IDOR Protection...")
    # Owner passes
    alice = User(id="user_alice", email="alice@lawfirm.in")
    contract_alice = Contract(id="c_1", user_id="user_alice", is_guest=False)
    validate_contract_access(contract_alice, user=alice, guest_session_id=None)
    print("  -> Authenticated owner access: PASSED")

    # Cross-user blocked
    bob = User(id="user_bob", email="bob@corporate.in")
    try:
        validate_contract_access(contract_alice, user=bob, guest_session_id=None)
        assert False, "Bob should not be able to access Alice's contract"
    except HTTPException as e:
        assert e.status_code == 403, f"Expected 403, got {e.status_code}"
    print("  -> Cross-user IDOR rejection: PASSED (403 Forbidden)")

    # Guest session matches
    guest_contract = Contract(
        id="cg_1",
        user_id=None,
        is_guest=True,
        guest_session_id="session_123",
        expires_at=datetime.utcnow() + timedelta(hours=2)
    )
    validate_contract_access(guest_contract, user=None, guest_session_id="session_123")
    print("  -> Guest session matching access: PASSED")

    # Cross-guest session blocked
    try:
        validate_contract_access(guest_contract, user=None, guest_session_id="session_456")
        assert False, "Guest 456 should not be able to access Guest 123 contract"
    except HTTPException as e:
        assert e.status_code == 403
    print("  -> Cross-guest session isolation: PASSED (403 Forbidden)")

    # Expired guest contract returns 410 Gone
    expired_contract = Contract(
        id="cg_old",
        user_id=None,
        is_guest=True,
        guest_session_id="session_123",
        expires_at=datetime.utcnow() - timedelta(minutes=5)
    )
    try:
        validate_contract_access(expired_contract, user=None, guest_session_id="session_123")
        assert False, "Expired guest contract should raise 410"
    except HTTPException as e:
        assert e.status_code == 410
    print("  -> Expired guest contract rejection: PASSED (410 Gone)")

    # Feature gating
    try:
        require_authenticated_feature(user=None)
        assert False, "Guest should not access authenticated features"
    except HTTPException as e:
        assert e.status_code == 403
        assert e.headers.get("X-Auth-Required") == "true"
    print("  -> Feature authorization restriction: PASSED (403 with X-Auth-Required)")

async def test_cleanup_service():
    print("[TEST 3] Testing Automatic Guest Cleanup Service...")
    cleanup = GuestCleanupService()
    now = datetime.utcnow()

    expired_guest = Contract(
        id="c_expired",
        filename="temp_nda.pdf",
        user_id=None,
        is_guest=True,
        guest_session_id="guest_old",
        expires_at=now - timedelta(hours=1),
        cloudinary_public_id="guest_contracts/c_expired_temp_nda",
        file_path="/tmp/test_nonexistent.pdf",
        cleanup_status="NONE",
        cleanup_retries=0
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [expired_guest]
    mock_db.execute.return_value = mock_res

    with patch("app.services.cleanup.guest_cleanup_service.qdrant_service.delete_contract_points", return_value=True) as mock_qdrant, \
         patch("app.services.cleanup.guest_cleanup_service.cloudinary_service.delete_file", new_callable=AsyncMock) as mock_cloud:
        
        mock_cloud.return_value = True

        report = await cleanup.run_cleanup(mock_db)
        assert report["expired_found"] == 1
        assert report["successfully_cleaned"] == 1
        assert report["failed_count"] == 0
        mock_qdrant.assert_called_once_with("c_expired")
        mock_cloud.assert_called_once_with(public_id="guest_contracts/c_expired_temp_nda", resource_type="raw")
        mock_db.delete.assert_called_once_with(expired_guest)
        assert mock_db.commit.called
        print("  -> Successful purge of Qdrant, Cloudinary & DB: PASSED")

    # Partial failure simulation
    failing_guest = Contract(
        id="c_fail",
        filename="fail.pdf",
        user_id=None,
        is_guest=True,
        guest_session_id="guest_fail",
        expires_at=now - timedelta(hours=1),
        cloudinary_public_id="guest_contracts/fail",
        file_path="/tmp/fail.pdf",
        cleanup_status="NONE",
        cleanup_retries=0
    )
    mock_db2 = AsyncMock()
    mock_res2 = MagicMock()
    mock_res2.scalars.return_value.all.return_value = [failing_guest]
    mock_db2.execute.return_value = mock_res2

    with patch("app.services.cleanup.guest_cleanup_service.qdrant_service.delete_contract_points", return_value=True), \
         patch("app.services.cleanup.guest_cleanup_service.cloudinary_service.delete_file", new_callable=AsyncMock) as mock_cloud2:
        
        mock_cloud2.return_value = False # Cloudinary deletion fails
        report2 = await cleanup.run_cleanup(mock_db2)
        assert report2["successfully_cleaned"] == 0
        assert report2["failed_count"] == 1
        assert failing_guest.cleanup_status == "FAILED_CLOUDINARY"
        assert failing_guest.cleanup_retries == 1
        mock_db2.delete.assert_not_called()
        print("  -> Partial failure resilience and retry tracking: PASSED")

async def test_claim_guest_contracts():
    print("[TEST 4] Testing Automatic Claiming of Guest Contracts on Signin/Signup...")
    from app.api.v1.auth import claim_guest_contracts

    now = datetime.utcnow()
    guest_contract = Contract(
        id="cg_claim_1",
        filename="guest_nda.pdf",
        user_id=None,
        is_guest=True,
        guest_session_id="session_guest_claim",
        expires_at=now + timedelta(hours=24),
        cleanup_status="NONE"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [guest_contract]
    mock_db.execute.return_value = mock_res

    claimed = await claim_guest_contracts("user_alice_id", "session_guest_claim", mock_db)
    assert claimed == 1, f"Expected 1 claimed contract, got {claimed}"
    assert guest_contract.is_guest is False, "Contract should no longer be marked as guest"
    assert guest_contract.user_id == "user_alice_id", "Contract user_id should be set to new owner"
    assert guest_contract.expires_at is None, "Contract expires_at should be cleared (permanent)"
    assert mock_db.commit.called
    print("  -> PASSED: Guest contract successfully converted to permanent user-owned contract on auth!")

async def test_iframe_pdf_access_with_query_params():
    print("[TEST 5] Testing Iframe PDF Access with Query Parameters (Token & Guest Session)...")
    from app.core.security import get_user_from_request_or_query, get_client_guest_session_id, create_access_token

    # 1. Test token in query param
    token = create_access_token({"sub": "user_123", "email": "test@domain.com"})
    mock_req_token = MagicMock()
    mock_req_token.headers.get.return_value = None
    mock_req_token.query_params.get.side_effect = lambda k: token if k == "token" else None
    mock_req_token.cookies.get.return_value = None

    mock_db = AsyncMock()
    mock_user = User(id="user_123", email="test@domain.com")
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_res

    resolved_user = await get_user_from_request_or_query(mock_req_token, mock_db)
    assert resolved_user is not None, "User should be resolved from token query param"
    assert resolved_user.id == "user_123"
    print("  -> PASSED: Authenticated user extracted from iframe '?token=...' parameter")

    # 2. Test guest_session_id in query param
    mock_req_guest = MagicMock()
    mock_req_guest.headers.get.return_value = None
    mock_req_guest.query_params.get.side_effect = lambda k: "session_query_999" if k == "guest_session_id" else None
    mock_req_guest.cookies.get.return_value = None

    resolved_session = get_client_guest_session_id(mock_req_guest)
    assert resolved_session == "session_query_999", f"Expected session_query_999, got {resolved_session}"
    print("  -> PASSED: Guest session extracted from iframe '?guest_session_id=...' parameter")

async def main():
    print("=" * 70)
    print("RUNNING CONTRACTIQ VERIFICATION TEST SUITE")
    print("=" * 70)
    test_clause_detection()
    test_auth_and_idor()
    await test_cleanup_service()
    await test_claim_guest_contracts()
    await test_iframe_pdf_access_with_query_params()
    print("=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

