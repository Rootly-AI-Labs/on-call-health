"""Legacy preview receipt security and provenance, without database or providers."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from jose import jwt

from app.services import retention_legacy as legacy


NOW = datetime(2026, 10, 5, 10, tzinfo=timezone.utc)
REVISION = NOW - timedelta(days=1)
REQUEST_ID = "a" * 32
FINGERPRINT = "b" * 64


@pytest.fixture(autouse=True)
def test_signing_secret(monkeypatch):
    monkeypatch.setattr(legacy.settings, "JWT_SECRET_KEY", "retention-unit-test-secret")
    monkeypatch.setattr(legacy.settings, "JWT_ALGORITHM", "HS256")


def organization(**settings):
    return SimpleNamespace(id=123, settings=settings)


def entry(analysis_id=1, fingerprint=FINGERPRINT):
    return legacy.LegacyAnalysisEntry(analysis_id=analysis_id, result_fingerprint=fingerprint)


def receipt(org=None, *, days=90, revision=REVISION, entries=None):
    return legacy.create_legacy_preview_receipt(
        org or organization(), days, revision,
        [entry()] if entries is None else entries, now=NOW,
    )[0]


def validate(token, org=None, *, days=90, revision=REVISION, now=NOW):
    return legacy.validate_legacy_preview_receipt(
        token, org or organization(), days, revision, now=now,
    )


def resign(token, *, algorithm="HS256", **changes):
    payload = jwt.get_unverified_claims(token)
    payload.update(changes)
    return jwt.encode(payload, legacy._signing_key(), algorithm=algorithm)


def authorization(**changes):
    data = {
        "state": "pending", "request_id": REQUEST_ID, "approved_at": NOW,
        "approved_by_user_id": 45, "requested_count": 1, "entries": [entry()],
    }
    data.update(changes)
    return legacy.LegacyCleanupAuthorization(**data)


def test_round_trip_contains_only_scope_counts_and_aggregate_fingerprint():
    token = receipt()
    claims = jwt.get_unverified_claims(token)
    verified = validate(token)
    assert verified.organization_id == 123
    assert verified.analysis_count == 1
    assert verified.snapshot_fingerprint == legacy.snapshot_fingerprint([entry()])
    assert verified.expires_at == NOW + legacy.PREVIEW_LIFETIME
    assert "results" not in claims and "entries" not in claims and "analysis_id" not in claims
    assert "sub" not in claims


def test_authentication_jwt_cannot_authorize_legacy_deletion():
    from app.auth.jwt import create_access_token, decode_access_token

    auth_token = create_access_token({"sub": "45"})
    assert decode_access_token(auth_token)["sub"] == "45"
    with pytest.raises(HTTPException) as error:
        validate(auth_token)
    assert error.value.status_code == 409
    assert error.value.detail["code"] == "legacy_preview_invalid"


def test_preview_receipt_cannot_authenticate_a_user():
    from app.auth.jwt import decode_access_token, get_user_id_from_token

    token = receipt()
    assert decode_access_token(token) is None
    assert get_user_id_from_token(token) is None


def test_auth_key_cannot_sign_even_a_well_formed_preview_payload():
    token = jwt.encode(jwt.get_unverified_claims(receipt()), legacy.settings.JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(HTTPException) as error:
        validate(token)
    assert error.value.detail["code"] == "legacy_preview_invalid"


def test_pre_generation_preview_receipt_cannot_authorize_the_new_retention_basis():
    old_key = hmac.new(
        legacy.settings.JWT_SECRET_KEY.encode("utf-8"),
        b"on-call-health:organization-retention-legacy-preview",
        hashlib.sha256,
    ).hexdigest()
    token = jwt.encode(jwt.get_unverified_claims(receipt()), old_key, algorithm="HS256")
    with pytest.raises(HTTPException) as error:
        validate(token)
    assert error.value.detail["code"] == "legacy_preview_invalid"


def test_signature_tampering_is_rejected():
    token = receipt()
    header, payload, signature = token.split(".")
    replacement = ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(HTTPException) as error:
        validate(".".join([header, payload, replacement]))
    assert error.value.detail["code"] == "legacy_preview_invalid"


def test_different_deployment_secret_invalidates_receipt(monkeypatch):
    token = receipt()
    monkeypatch.setattr(legacy.settings, "JWT_SECRET_KEY", "different-retention-test-secret")
    with pytest.raises(HTTPException) as error:
        validate(token)
    assert error.value.detail["code"] == "legacy_preview_invalid"


@pytest.mark.parametrize("now", [
    NOW - timedelta(microseconds=1), NOW + legacy.PREVIEW_LIFETIME,
    NOW + legacy.PREVIEW_LIFETIME + timedelta(seconds=1),
])
def test_receipt_expiry_and_future_clock_are_rejected(now):
    with pytest.raises(HTTPException) as error:
        validate(receipt(), now=now)
    assert error.value.detail["code"] == "legacy_preview_expired"


def test_receipt_valid_until_exact_expiry_boundary():
    assert validate(receipt(), now=NOW + legacy.PREVIEW_LIFETIME - timedelta(microseconds=1)).analysis_count == 1


@pytest.mark.parametrize("changes", [
    {"expires_at": (NOW + timedelta(minutes=30)).isoformat()},
    {"expires_at": (NOW + timedelta(minutes=1)).isoformat()},
])
def test_signed_receipt_cannot_extend_or_change_its_lifetime(changes):
    with pytest.raises(HTTPException) as error:
        validate(resign(receipt(), **changes))
    assert error.value.detail["code"] == "legacy_preview_expired"


@pytest.mark.parametrize("changes", [
    {"purpose": "access_token"}, {"analysis_count": True},
    {"analysis_count": -1}, {"organization_id": True},
    {"request_id": "malformed"}, {"snapshot_fingerprint": "malformed"},
    {"evaluated_at": NOW.replace(tzinfo=None).isoformat()},
    {"expires_at": (NOW + legacy.PREVIEW_LIFETIME).replace(tzinfo=None).isoformat()},
    {"unexpected": "field"},
])
def test_signed_malformed_claims_fail_closed(changes):
    with pytest.raises(HTTPException) as error:
        validate(resign(receipt(), **changes))
    assert error.value.detail["code"] == "legacy_preview_invalid"


def test_receipt_algorithm_is_explicitly_restricted():
    with pytest.raises(HTTPException) as error:
        validate(resign(receipt(), algorithm="HS384"))
    assert error.value.detail["code"] == "legacy_preview_invalid"


@pytest.mark.parametrize("org,days,revision", [
    (SimpleNamespace(id=124, settings={}), 90, REVISION),
    (organization(), 30, REVISION),
    (organization(), 90, REVISION + timedelta(microseconds=1)),
    (organization(), 90, None),
])
def test_receipt_is_bound_to_organization_days_and_policy_revision(org, days, revision):
    with pytest.raises(HTTPException) as error:
        validate(receipt(), org, days=days, revision=revision)
    assert error.value.detail["code"] == "legacy_preview_stale"


def test_same_policy_in_different_timezone_representation_is_unchanged():
    local_revision = REVISION.astimezone(timezone(timedelta(hours=-4)))
    assert validate(receipt(), revision=local_revision).policy_updated_at == REVISION.isoformat()


@pytest.mark.parametrize("state", ["pending", "completed", "cancelled"])
def test_current_receipt_nonce_cannot_be_replayed(state):
    token = receipt()
    nonce = jwt.get_unverified_claims(token)["request_id"]
    changes = {"state": state, "request_id": nonce}
    if state != "pending":
        changes.update(entries=[], finished_at=NOW, skipped_count=1)
    org = organization(**{legacy.LEGACY_SETTINGS_KEY: authorization(**changes).model_dump(mode="json")})
    with pytest.raises(HTTPException) as error:
        validate(token, org)
    assert error.value.detail["code"] == "legacy_preview_already_used"


def test_generation_dates_and_result_changes_invalidate_approval_but_status_does_not():
    analysis = SimpleNamespace(
        results={"metrics": {"count": 7}}, error_message=None,
        created_at=NOW - timedelta(days=3), completed_at=NOW,
        results_generated_at=None,
        status="completed", config={"time_range": 90},
    )
    original = legacy.fingerprint_analysis_result(analysis)
    analysis.status = "running"
    analysis.config = {"time_range": 30, "is_auto_refresh": True}
    assert legacy.fingerprint_analysis_result(analysis) == original
    analysis.results_generated_at = NOW
    assert legacy.fingerprint_analysis_result(analysis) != original
    analysis.results_generated_at = None
    analysis.completed_at = NOW + timedelta(microseconds=1)
    assert legacy.fingerprint_analysis_result(analysis) != original
    analysis.completed_at = NOW
    analysis.created_at += timedelta(microseconds=1)
    assert legacy.fingerprint_analysis_result(analysis) != original
    analysis.created_at -= timedelta(microseconds=1)
    analysis.results["metrics"]["count"] = 8
    assert legacy.fingerprint_analysis_result(analysis) != original


def test_fingerprint_is_canonical_for_json_key_order_and_aware_timezones():
    first = SimpleNamespace(results={"a": 1, "b": 2}, error_message=None, created_at=NOW, completed_at=NOW, results_generated_at=NOW)
    local_time = NOW.astimezone(timezone(timedelta(hours=2)))
    second = SimpleNamespace(results={"b": 2, "a": 1}, error_message=None, created_at=local_time, completed_at=local_time, results_generated_at=local_time)
    assert legacy.fingerprint_analysis_result(first) == legacy.fingerprint_analysis_result(second)
    second.error_message = "Different historical error"
    assert legacy.fingerprint_analysis_result(first) != legacy.fingerprint_analysis_result(second)


def test_snapshot_fingerprint_changes_for_selected_id_or_generation():
    one, two = entry(1), entry(2)
    assert legacy.snapshot_fingerprint([one, two]) == legacy.snapshot_fingerprint([two, one])
    assert legacy.snapshot_fingerprint([one, two]) != legacy.snapshot_fingerprint([one, entry(3)])
    assert legacy.snapshot_fingerprint([one, two]) != legacy.snapshot_fingerprint([one, entry(2, "c" * 64)])


@pytest.mark.parametrize("changes", [
    {"entries": [entry(), entry()], "requested_count": 2},
    {"requested_count": True}, {"cleared_count": -1}, {"skipped_count": -1},
    {"cleared_count": 1}, {"requested_count": 2},
    {"finished_at": NOW}, {"approved_at": NOW.replace(tzinfo=None)},
    {"approved_by_user_id": True}, {"approved_by_user_id": 0},
    {"state": "completed", "entries": []},
    {"state": "completed", "entries": [], "finished_at": NOW},
    {"unexpected": "field"},
])
def test_malformed_stored_authorization_fails_closed(changes):
    data = authorization().model_dump(mode="json")
    data.update(changes)
    org = organization(**{legacy.LEGACY_SETTINGS_KEY: data})
    with pytest.raises(ValueError):
        legacy.read_legacy_authorization(org)
    with pytest.raises(ValueError):
        legacy.pending_legacy_entries(org)


def test_partial_consumption_preserves_only_remaining_approved_entries():
    org = organization(data_retention={"retention_days": 90}, unrelated={"keep": True})
    legacy.save_legacy_authorization(org, authorization(requested_count=2, entries=[entry(1), entry(2)]))
    legacy.finish_legacy_cleanup(org, remaining_entries=[entry(2)], cleared_count=1, skipped_count=0, now=NOW)
    saved = legacy.read_legacy_authorization(org)
    assert saved.state == "pending" and saved.cleared_count == 1
    assert list(legacy.pending_legacy_entries(org)) == [2]
    assert org.settings["data_retention"] == {"retention_days": 90}
    assert org.settings["unrelated"] == {"keep": True}

    legacy.finish_legacy_cleanup(org, remaining_entries=[], cleared_count=0, skipped_count=1, now=NOW + timedelta(minutes=1))
    saved = legacy.read_legacy_authorization(org)
    assert saved.state == "completed" and saved.cleared_count == saved.skipped_count == 1
    assert legacy.pending_legacy_entries(org) == {}


def test_invalid_consumption_does_not_mutate_stored_approval():
    org = organization()
    legacy.save_legacy_authorization(org, authorization())
    before = deepcopy(org.settings)
    with pytest.raises(ValueError):
        legacy.finish_legacy_cleanup(org, remaining_entries=[], cleared_count=0, skipped_count=0, now=NOW)
    assert org.settings == before


@pytest.mark.parametrize("state", ["completed", "cancelled"])
def test_finished_approval_cannot_be_consumed_again(state):
    org = organization()
    legacy.save_legacy_authorization(org, authorization(state=state, entries=[], finished_at=NOW, skipped_count=1))
    before = deepcopy(org.settings)
    legacy.finish_legacy_cleanup(org, remaining_entries=[], cleared_count=1, skipped_count=0, now=NOW)
    assert org.settings == before


@pytest.mark.parametrize("remaining", [
    [entry(3)], [entry(2, "c" * 64)], [entry(1), entry(1)],
])
def test_cleanup_cannot_add_replace_or_duplicate_an_approved_entry(remaining):
    org = organization()
    legacy.save_legacy_authorization(org, authorization(requested_count=2, entries=[entry(1), entry(2)]))
    before = deepcopy(org.settings)
    with pytest.raises(ValueError):
        legacy.finish_legacy_cleanup(
            org, remaining_entries=remaining, cleared_count=2 - len(remaining), skipped_count=0, now=NOW,
        )
    assert org.settings == before


@pytest.mark.parametrize("cleared,skipped", [
    (-1, 1), (1, -1), (False, 0), (0, True), (0.0, 0), (0, 0.0),
])
def test_progress_deltas_remain_strict_even_when_previous_totals_mask_them(cleared, skipped):
    org = organization()
    legacy.save_legacy_authorization(org, authorization(requested_count=2, cleared_count=1))
    before = deepcopy(org.settings)
    with pytest.raises(ValueError):
        legacy.finish_legacy_cleanup(
            org, remaining_entries=[entry()], cleared_count=cleared, skipped_count=skipped, now=NOW,
        )
    assert org.settings == before


def test_progress_cannot_claim_more_or_fewer_consumed_entries_than_the_snapshot():
    org = organization()
    legacy.save_legacy_authorization(org, authorization(requested_count=2, entries=[entry(1), entry(2)]))
    before = deepcopy(org.settings)
    with pytest.raises(ValueError):
        legacy.finish_legacy_cleanup(org, remaining_entries=[entry(2)], cleared_count=1, skipped_count=1, now=NOW)
    assert org.settings == before


def test_cancellation_accounts_for_each_remaining_entry_without_clearing_history():
    org = organization(data_retention={"retention_days": 90}, unrelated={"keep": True})
    legacy.save_legacy_authorization(org, authorization(
        requested_count=4, cleared_count=1, skipped_count=1, entries=[entry(1), entry(2)],
        used_preview_receipts=[legacy.LegacyReceiptUse(request_id=REQUEST_ID, expires_at=NOW + legacy.PREVIEW_LIFETIME)],
    ))
    assert legacy.cancel_legacy_authorization(org, now=NOW + timedelta(minutes=1)) is True
    saved = legacy.read_legacy_authorization(org)
    status = legacy.legacy_cleanup_status(org)
    assert saved.state == status.state == "cancelled"
    assert saved.entries == []
    assert saved.cleared_count == status.cleared_count == 1
    assert saved.skipped_count == status.skipped_count == 1
    assert saved.cancelled_count == status.cancelled_count == 2
    assert status.requested_count == status.cleared_count + status.skipped_count + status.cancelled_count
    assert saved.used_preview_receipts[0].request_id == REQUEST_ID
    assert org.settings["data_retention"] == {"retention_days": 90}
    assert org.settings["unrelated"] == {"keep": True}
    before = deepcopy(org.settings)
    assert legacy.cancel_legacy_authorization(org, now=NOW + timedelta(minutes=2)) is False
    assert org.settings == before


@pytest.mark.parametrize("changes", [
    {"state": "cancelled", "entries": [], "finished_at": NOW},
    {"state": "completed", "entries": [], "finished_at": NOW, "cancelled_count": 1},
    {"cancelled_count": 1},
    {"cancelled_count": -1},
    {"used_preview_receipts": [
        {"request_id": REQUEST_ID, "expires_at": NOW + legacy.PREVIEW_LIFETIME},
        {"request_id": REQUEST_ID, "expires_at": NOW + legacy.PREVIEW_LIFETIME},
    ]},
    {"used_preview_receipts": [{"request_id": REQUEST_ID, "expires_at": NOW.replace(tzinfo=None)}]},
    {"used_preview_receipts": [{"request_id": "malformed", "expires_at": NOW}]},
])
def test_malformed_cancellation_or_nonce_history_fails_closed(changes):
    data = authorization().model_dump(mode="json")
    data.update(changes)
    org = organization(**{legacy.LEGACY_SETTINGS_KEY: data})
    with pytest.raises(ValueError):
        legacy.read_legacy_authorization(org)


@pytest.mark.parametrize("empty_snapshot", [False, True])
def test_older_receipt_still_cannot_replay_after_a_new_approval(empty_snapshot):
    token = receipt(entries=[] if empty_snapshot else [entry()])
    nonce = jwt.get_unverified_claims(token)["request_id"]
    org = organization()
    legacy.save_legacy_authorization(org, authorization(
        state="completed", requested_count=0, entries=[], finished_at=NOW,
        used_preview_receipts=[legacy.LegacyReceiptUse(request_id=nonce, expires_at=NOW + legacy.PREVIEW_LIFETIME)],
    ))
    assert legacy.read_legacy_authorization(org).request_id != nonce
    with pytest.raises(HTTPException) as error:
        validate(token, org)
    assert error.value.detail["code"] == "legacy_preview_already_used"


def test_unused_receipt_with_current_scope_is_not_blocked_by_other_nonce_history():
    org = organization()
    legacy.save_legacy_authorization(org, authorization(
        state="completed", requested_count=0, entries=[], finished_at=NOW,
        used_preview_receipts=[legacy.LegacyReceiptUse(request_id=REQUEST_ID, expires_at=NOW + legacy.PREVIEW_LIFETIME)],
    ))
    token = receipt(org)
    assert validate(token, org).analysis_count == 1
