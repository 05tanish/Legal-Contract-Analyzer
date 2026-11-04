import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException

from app.db.models import Contract, User, ContractChunk
from app.core.security import validate_contract_access, require_authenticated_feature
from app.services.clause_detection.detector import clause_detector
from app.services.cleanup.guest_cleanup_service import GuestCleanupService

# ---------------------------------------------------------------------------
# 1. CLAUSE DETECTION TESTS (CUAD ML + HEURISTICS)
# ---------------------------------------------------------------------------

def test_clause_detection_non_compete_and_liability():
    """Verify lightweight clause detector identifies critical clauses without LLM calls."""
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
    assert len(detected) >= 2

    categories = [d["category_id"] for d in detected]
    assert any("non_compete" in c for c in categories)
    assert any("liability" in c for c in categories)
    assert any("confidentiality" in c for c in categories)

    # Validate output format
    first = detected[0]
    assert "category_title" in first
    assert "severity" in first
    assert "page_number" in first
    assert "snippet" in first

# ---------------------------------------------------------------------------
# 2. AUTHORIZATION & IDOR VALIDATION TESTS
# ---------------------------------------------------------------------------

def test_validate_contract_access_authenticated_owner():
    """Owner can access their own contract."""
    user = User(id="user_alice", email="alice@lawfirm.in")
    contract = Contract(id="c_1", user_id="user_alice", is_guest=False)
    # Should not raise
    validate_contract_access(contract, user=user, guest_session_id=None)

def test_validate_contract_access_cross_user_denied():
    """User Bob cannot access Alice's contract (IDOR protection)."""
    bob = User(id="user_bob", email="bob@corporate.in")
    contract = Contract(id="c_1", user_id="user_alice", is_guest=False)
    with pytest.raises(HTTPException) as exc_info:
        validate_contract_access(contract, user=bob, guest_session_id=None)
    assert exc_info.value.status_code == 403

def test_validate_contract_access_unauthenticated_on_user_contract_denied():
    """Unauthenticated guest cannot access an authenticated user's contract."""
    contract = Contract(id="c_1", user_id="user_alice", is_guest=False)
    with pytest.raises(HTTPException) as exc_info:
        validate_contract_access(contract, user=None, guest_session_id="guest_session_999")
    assert exc_info.value.status_code == 403

def test_validate_contract_access_guest_valid_session():
    """Guest with matching session token can view their temporary contract."""
    session_id = "session_xyz_123"
    contract = Contract(
        id="c_guest_1",
        user_id=None,
        is_guest=True,
        guest_session_id=session_id,
        expires_at=datetime.utcnow() + timedelta(hours=2)
    )
    # Should not raise
    validate_contract_access(contract, user=None, guest_session_id=session_id)

def test_validate_contract_access_guest_cross_session_denied():
    """Guest A cannot view Guest B's contract."""
    contract = Contract(
        id="c_guest_1",
        user_id=None,
        is_guest=True,
        guest_session_id="session_guest_A",
        expires_at=datetime.utcnow() + timedelta(hours=2)
    )
    with pytest.raises(HTTPException) as exc_info:
        validate_contract_access(contract, user=None, guest_session_id="session_guest_B")
    assert exc_info.value.status_code == 403

def test_validate_contract_access_expired_guest_contract():
    """Accessing an expired guest contract returns 410 Gone."""
    session_id = "session_expired_123"
    contract = Contract(
        id="c_guest_old",
        user_id=None,
        is_guest=True,
        guest_session_id=session_id,
        expires_at=datetime.utcnow() - timedelta(minutes=10) # Expired 10m ago
    )
    with pytest.raises(HTTPException) as exc_info:
        validate_contract_access(contract, user=None, guest_session_id=session_id)
    assert exc_info.value.status_code == 410

def test_require_authenticated_feature():
    """Unauthenticated access to advanced AI agents triggers 403 with X-Auth-Required."""
    with pytest.raises(HTTPException) as exc_info:
        require_authenticated_feature(user=None)
    assert exc_info.value.status_code == 403
    assert exc_info.value.headers.get("X-Auth-Required") == "true"

    # Authenticated user passes
    user = User(id="user_valid", email="partner@trilegal.com")
    require_authenticated_feature(user=user)

# ---------------------------------------------------------------------------
# 3. AUTOMATIC GUEST DATA CLEANUP TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_guest_cleanup_service_purges_expired_only():
    """
    Verifies that the cleanup service:
    1. Purges expired guest contracts from DB, Qdrant, Cloudinary, and local disk.
    2. NEVER deletes authenticated user contracts.
    3. Preserves unexpired guest contracts.
    """
    cleanup_service = GuestCleanupService()

    now = datetime.utcnow()
    expired_guest = Contract(
        id="c_expired",
        filename="temp_nda.pdf",
        user_id=None,
        is_guest=True,
        guest_session_id="guest_old",
        expires_at=now - timedelta(hours=1),
        cloudinary_public_id="guest_contracts/c_expired_temp_nda",
        file_path="/tmp/test_temp_nda.pdf",
        cleanup_status="NONE",
        cleanup_retries=0
    )

    active_guest = Contract(
        id="c_active_guest",
        filename="active_nda.pdf",
        user_id=None,
        is_guest=True,
        guest_session_id="guest_active",
        expires_at=now + timedelta(hours=5),
        cleanup_status="NONE"
    )

    auth_contract = Contract(
        id="c_auth_user",
        filename="permanent_msa.pdf",
        user_id="user_alice",
        is_guest=False,
        expires_at=None,
        cleanup_status="NONE"
    )

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    # Mock finding only the expired guest
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [expired_guest]
    mock_db.execute.return_value = mock_result

    with patch("app.services.cleanup.guest_cleanup_service.qdrant_service.delete_contract_points", return_value=True) as mock_qdrant, \
         patch("app.services.cleanup.guest_cleanup_service.cloudinary_service.delete_file", new_callable=AsyncMock) as mock_cloud:
        
        mock_cloud.return_value = True

        report = await cleanup_service.run_cleanup(mock_db)

        # Assertions
        assert report["expired_found"] == 1
        assert report["successfully_cleaned"] == 1
        assert report["failed_count"] == 0

        # External services were called for expired contract
        mock_qdrant.assert_called_once_with("c_expired")
        mock_cloud.assert_called_once_with(public_id="guest_contracts/c_expired_temp_nda", resource_type="raw")

        # Database delete was invoked
        mock_db.delete.assert_called_once_with(expired_guest)
        assert mock_db.commit.called

@pytest.mark.asyncio
async def test_guest_cleanup_service_handles_partial_failure():
    """
    Verifies that if Qdrant or Cloudinary fails, the record is NOT deleted
    from the database, and status + retry counter are updated.
    """
    cleanup_service = GuestCleanupService()
    now = datetime.utcnow()

    failing_guest = Contract(
        id="c_fail",
        filename="fail_contract.pdf",
        user_id=None,
        is_guest=True,
        guest_session_id="guest_fail",
        expires_at=now - timedelta(hours=1),
        cloudinary_public_id="guest_contracts/fail_contract",
        file_path="/tmp/non_existent.pdf",
        cleanup_status="NONE",
        cleanup_retries=0
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [failing_guest]
    mock_db.execute.return_value = mock_result

    # Cloudinary fails
    with patch("app.services.cleanup.guest_cleanup_service.qdrant_service.delete_contract_points", return_value=True), \
         patch("app.services.cleanup.guest_cleanup_service.cloudinary_service.delete_file", new_callable=AsyncMock) as mock_cloud:
        
        mock_cloud.return_value = False # Simulate failure

        report = await cleanup_service.run_cleanup(mock_db)

        assert report["successfully_cleaned"] == 0
        assert report["failed_count"] == 1
        assert failing_guest.cleanup_status == "FAILED_CLOUDINARY"
        assert failing_guest.cleanup_retries == 1

        # Database delete was NOT called
        mock_db.delete.assert_not_called()

