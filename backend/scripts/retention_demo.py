"""Create and restore an inert retention sandbox in the local Compose database.

Run from the backend container, for example:
  python scripts/retention_demo.py seed --local-compose --email you@example.com
  python scripts/retention_demo.py status --local-compose

There is no web endpoint or automatic cleanup. The CLI refuses remote databases,
and reset/cleanup refuse data that was not recorded in the fixture manifest.
"""
import argparse
import json
import os
import secrets
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import MetaData, Table, bindparam, func, inspect, or_, select, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DEMO_SLUG = "local-retention-demo"
MARKER_KEY = "local_retention_demo"
DEMO_DOMAIN = "retention-demo.local.invalid"
MOCK_MEMBERS = (("alex", "Alex Morgan"), ("priya", "Priya Shah"), ("noah", "Noah Chen"))


def guard_local_database(url, confirmed: bool):
    """Reject routing overrides as well as an accidentally selected remote DB."""
    if not confirmed:
        raise ValueError("This command requires --local-compose.")
    try:
        parsed = make_url(url)
    except Exception as exc:
        raise ValueError("A valid local Compose database URL is required.") from exc
    if (
        parsed.get_backend_name() != "postgresql" or parsed.host not in {"postgres", "localhost", "127.0.0.1"}
        or parsed.database != "burnout_detector" or parsed.port not in {None, 5432}
        or parsed.username != "postgres" or parsed.query
    ):
        raise ValueError("Only the local Compose PostgreSQL burnout_detector database is allowed.")


def _utc(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Use a timezone-aware clock for demo fixtures.")
    return value.astimezone(timezone.utc)


def _now(value=None):
    return _utc(value or datetime.now(timezone.utc))


def _iso(value):
    return _utc(value).isoformat() if value else None


def _demo(db, *, lock=False):
    from app.models import Organization
    query = db.query(Organization).filter_by(slug=DEMO_SLUG)
    if lock:
        query = query.populate_existing().with_for_update()
    org = query.one_or_none()
    if org is None:
        raise ValueError("No retention demo exists. Run the seed command first.")
    marker = (org.settings or {}).get(MARKER_KEY)
    if (
        not isinstance(marker, dict) or marker.get("version") != 1
        or not isinstance(marker.get("instance"), str) or len(marker["instance"]) != 32
        or org.domain != DEMO_DOMAIN or not isinstance(marker.get("owner_user_id"), int)
    ):
        raise ValueError("This organization is not a recognized local retention fixture.")
    return org, marker


def _save_marker(org, marker):
    org.settings = {**(org.settings or {}), MARKER_KEY: marker}


def seed_demo(db, email, *, now=None):
    from app.models import Analysis, OAuthProvider, Organization, User
    from scripts.retention_demo_fixtures import create_fixture_data

    now = _now(now)
    try:
        owner = db.query(User).filter(func.lower(User.email) == email.lower()).with_for_update().one_or_none()
        if owner is None or owner.status != "active":
            raise ValueError("Select an existing active local account with --email.")
        existing = db.query(Organization).filter_by(slug=DEMO_SLUG).one_or_none()
        if existing is not None:
            org, marker = _demo(db)
            if marker["owner_user_id"] != owner.id or owner.organization_id != org.id:
                raise ValueError("A demo already exists for another or restored account. Restore/reset it first.")
            return demo_status(db)
        if db.query(Analysis.id).filter(Analysis.user_id == owner.id, or_(
            Analysis.is_auto_refresh.is_(True), Analysis.status.in_(["pending", "running"]),
        )).first() is not None:
            raise ValueError("This account has active or auto-refresh analyses. Finish them before moving its local membership.")
        original = {
            "organization_id": owner.organization_id, "role": owner.role,
            "joined_org_at": _iso(owner.joined_org_at),
            "weekly_digest_enabled": owner.weekly_digest_enabled,
        }
        instance = uuid4().hex
        org = Organization(name="Retention Demo", domain=DEMO_DOMAIN, slug=DEMO_SLUG,
                           status="active", settings={}, max_users=50)
        db.add(org)
        db.flush()
        owner.organization_id = org.id
        owner.role = "admin"
        owner.joined_org_at = now
        owner.weekly_digest_enabled = False
        mock_users = []
        provider_ids = []
        for key, name in MOCK_MEMBERS:
            address = f"{key}@{DEMO_DOMAIN}"
            if db.query(User.id).filter(func.lower(User.email) == address).first() is not None:
                raise ValueError("A fixture email is already in use. No account was replaced.")
            member = User(email=address, name=name, email_domain=DEMO_DOMAIN,
                          organization_id=org.id, role="member", status="active",
                          joined_org_at=now, is_verified=True, weekly_digest_enabled=False)
            db.add(member)
            db.flush()
            # An inert local provider marker makes fictional accounts visible in
            # Team Roles; it contains no real OAuth identity or provider token.
            provider = OAuthProvider(user_id=member.id, provider="local_demo",
                                     provider_user_id=f"retention-demo-{instance}-{key}", is_primary=True)
            db.add(provider)
            db.flush()
            provider_ids.append(provider.id)
            mock_users.append(member)
        fixtures = create_fixture_data(db, org, owner, mock_users, now=now, instance=instance)
        marker = {
            "version": 1, "instance": instance, "created_at": now.isoformat(),
            "result_age_fixture_version": 2,
            "owner_user_id": owner.id, "original_membership": original,
            "demo_joined_org_at": now.isoformat(),
            "mock_user_ids": [user.id for user in mock_users], "provider_ids": provider_ids,
            **fixtures,
        }
        _save_marker(org, marker)
        db.commit()
        return demo_status(db)
    except Exception:
        db.rollback()
        raise


def demo_status(db):
    from app.models import Analysis, User, UserBurnoutReport
    from app.services.retention_preview import RetentionPreviewRequest, build_retention_preview
    from app.services.data_retention import retention_policy_response

    org, marker = _demo(db)
    owner = db.get(User, marker["owner_user_id"])
    preview = build_retention_preview(db, org, RetentionPreviewRequest(retention_days=90), now=_now())
    analyses = {case: {"id": row_id, "has_results": bool(row and row.results),
                      "status": row.status if row else "removed",
                      "generation_at": _iso(row.results_generated_at) if row else None}
                for case, row_id in marker["analysis_ids"].items()
                for row in [db.get(Analysis, row_id)]}
    surveys = {case: {"id": row_id, "exists": row is not None,
                     "analysis_id": row.analysis_id if row else None}
               for case, row_id in marker["survey_ids"].items()
               for row in [db.get(UserBurnoutReport, row_id)]}
    return {
        "organization": {"id": org.id, "name": org.name},
        "owner": {"id": owner.id, "name": owner.name, "email": owner.email,
                  "role": owner.role, "in_demo": owner.organization_id == org.id},
        "members": [{"id": user.id, "name": user.name, "email": user.email, "role": user.role}
                    for user in db.query(User).filter(User.organization_id == org.id).order_by(User.id)],
        "saved_policy": retention_policy_response(org).model_dump(mode="json"),
        "preview_at_90_days": {
            "analyses": preview.analyses.model_dump(), "surveys": preview.survey_responses.model_dump(),
            "related_records": preview.related_records.model_dump(),
        },
        "analyses": analyses, "surveys": surveys,
    }


def upgrade_demo(db):
    """Update only the disabled, recorded fixture for result-age verification."""
    from app.models import Analysis, User
    from app.services.data_retention import read_retention_policy
    from scripts.retention_demo_fixtures import _result_payload

    try:
        org, marker = _demo(db, lock=True)
        _assert_fixture_only(db, org, marker)
        if read_retention_policy(org).retention_days is not None:
            raise ValueError("Disable the demo policy before updating its fixtures.")
        if marker.get("result_age_fixture_version") == 2:
            return demo_status(db)
        now = _now()
        members = [db.get(User, row_id) for row_id in marker["mock_user_ids"]]
        for case, row_id in marker["analysis_ids"].items():
            row = db.get(Analysis, row_id)
            generated = now - timedelta(days=120) if case in {"old", "mixed", "saved_old"} else now if case == "recent" else None
            row.results_generated_at = generated
            row.completed_at = None if case in {"running", "legacy"} else generated or now
            if case == "recent":
                row.results = _result_payload(members, case="recent", now=now)
                row.time_range = 130
                row.integration_name = "Retention Demo · Fresh four-month report; old source data retained"
        _save_marker(org, {**marker, "result_age_fixture_version": 2})
        db.commit()
        return demo_status(db)
    except Exception:
        db.rollback()
        raise


def _assert_fixture_only(db, org, marker):
    """Refuse resetting or cleaning a sandbox after nonfixture data was added."""
    from app.models import Analysis, OAuthProvider, User, UserBurnoutReport, UserCorrelation, UserLoginEvent

    expected_users = {marker["owner_user_id"], *marker["mock_user_ids"]}
    actual_users = {row[0] for row in db.query(User.id).filter(User.organization_id == org.id)}
    allowed_users = expected_users - ({marker["owner_user_id"]} if marker.get("membership_restored_at") else set())
    if actual_users != allowed_users:
        raise ValueError("Unexpected organization membership. No demo data was changed.")
    expected_analyses = set(marker["analysis_ids"].values())
    rows = db.query(Analysis).filter(Analysis.organization_id == org.id).all()
    if {row.id for row in rows} != expected_analyses or any(
        row.user_id != marker["owner_user_id"] or (row.config or {}).get(MARKER_KEY) != marker["instance"]
        or row.is_auto_refresh for row in rows
    ):
        raise ValueError("Unexpected analysis data or scheduling. No demo data was changed.")
    expected_surveys = set(marker["survey_ids"].values())
    surveys = db.query(UserBurnoutReport).filter(UserBurnoutReport.organization_id == org.id).all()
    if any(row.id not in expected_surveys or row.user_id not in marker["mock_user_ids"] for row in surveys):
        raise ValueError("Unexpected survey data. No demo data was changed.")
    linked_surveys = db.query(UserBurnoutReport).filter(or_(
        UserBurnoutReport.analysis_id.in_(expected_analyses),
        UserBurnoutReport.user_id.in_(marker["mock_user_ids"]),
    )).all()
    if any(row.id not in expected_surveys or row.organization_id != org.id for row in linked_surveys):
        raise ValueError("Unexpected foreign survey references. No demo data was changed.")
    correlations = db.query(UserCorrelation).filter(UserCorrelation.organization_id == org.id).all()
    if {row.id for row in correlations} != set(marker["correlation_ids"]):
        raise ValueError("Unexpected roster data. No demo data was changed.")
    providers = db.query(OAuthProvider).filter(OAuthProvider.user_id.in_(marker["mock_user_ids"])).all()
    if {row.id for row in providers} != set(marker["provider_ids"]) or any(row.provider != "local_demo" for row in providers):
        raise ValueError("A mock account now has nonfixture providers. No demo data was changed.")
    if db.query(UserLoginEvent.id).filter(
        UserLoginEvent.organization_id == org.id, UserLoginEvent.user_id.not_in(expected_users),
    ).first() is not None:
        raise ValueError("Unexpected login history belongs to another account. Reset/cleanup was refused.")
    # Inspect live FK declarations too: adding a mapping, schedule, notification,
    # integration or other dependent record must not cause an accidental cascade.
    targets = {"organizations": {org.id}, "users": set(marker["mock_user_ids"]),
               "analyses": expected_analyses, "user_burnout_reports": expected_surveys,
               "user_correlations": set(marker["correlation_ids"])}
    allowed_tables = {"users", "analyses", "user_burnout_reports", "user_correlations", "oauth_providers", "user_login_events", "oauth_temp_codes"}
    allowed_ids = {"users": expected_users, "analyses": expected_analyses,
                   "user_burnout_reports": expected_surveys,
                   "user_correlations": set(marker["correlation_ids"]),
                   "oauth_providers": set(marker["provider_ids"])}
    inspector = inspect(db.connection())
    metadata = MetaData()
    prefix = f"retention_demo_{marker['instance']}_"
    if db.execute(text(
        "SELECT 1 FROM oauth_temp_codes WHERE left(code, :length) = :prefix "
        "AND user_id NOT IN :users LIMIT 1"
    ).bindparams(bindparam("users", expanding=True)), {
        "length": len(prefix), "prefix": prefix, "users": list(expected_users),
    }).first():
        raise ValueError("Unexpected login data belongs to another account. Reset was refused.")
    for table_name in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(table_name):
            values = targets.get(fk["referred_table"])
            if not values or len(fk["constrained_columns"]) != 1:
                continue
            table = Table(table_name, metadata, autoload_with=db.connection(), extend_existing=True)
            column = table.c[fk["constrained_columns"][0]]
            if table_name not in allowed_tables and db.execute(select(column).where(column.in_(values)).limit(1)).first():
                raise ValueError("Unexpected dependent data. Use restore to leave it intact; reset/cleanup was refused.")
            if table_name in allowed_ids and db.execute(select(column).where(
                column.in_(values), table.c.id.not_in(allowed_ids[table_name]),
            ).limit(1)).first():
                raise ValueError("Unexpected dependent fixture identity. No demo data was changed.")
            if table_name == "oauth_temp_codes":
                prefix = f"retention_demo_{marker['instance']}_"
                if db.execute(select(column).where(column.in_(values), func.left(table.c.code, len(prefix)) != prefix).limit(1)).first():
                    raise ValueError("Unexpected login data belongs to a mock account. Reset was refused.")


def _restore_owner(db, org, marker):
    from app.models import User

    owner = db.query(User).filter_by(id=marker["owner_user_id"]).populate_existing().with_for_update().one()
    original = marker["original_membership"]
    if marker.get("membership_restored_at"):
        if owner.organization_id != original["organization_id"] or owner.role != original["role"]:
            raise ValueError("The account changed after restore. No membership was overwritten.")
        return
    if owner.organization_id != org.id or owner.role != "admin" or _iso(owner.joined_org_at) != marker["demo_joined_org_at"]:
        raise ValueError("The account's membership changed during the demo. No membership was overwritten.")
    owner.organization_id = original["organization_id"]
    owner.role = original["role"]
    owner.joined_org_at = datetime.fromisoformat(original["joined_org_at"]) if original["joined_org_at"] else None
    if owner.weekly_digest_enabled is False:
        owner.weekly_digest_enabled = original["weekly_digest_enabled"]


def restore_membership(db):
    from app.services.data_retention import POLICY_SETTINGS_KEY, RetentionPolicy
    from app.services.retention_legacy import cancel_legacy_authorization

    try:
        org, marker = _demo(db, lock=True)
        _restore_owner(db, org, marker)
        now = _now()
        cancel_legacy_authorization(org, now=now)
        org.settings = {**(org.settings or {}), POLICY_SETTINGS_KEY: RetentionPolicy(
            retention_days=None, updated_at=now, updated_by_user_id=marker["owner_user_id"],
        ).model_dump(mode="json")}
        _save_marker(org, {**marker, "membership_restored_at": now.isoformat()})
        db.commit()
        return {"restored": True, "fixtures_preserved": True}
    except Exception:
        db.rollback()
        raise


def reset_demo(db):
    from app.models import Analysis, OAuthProvider, Organization, User, UserBurnoutReport, UserCorrelation, UserLoginEvent

    try:
        org, marker = _demo(db, lock=True)
        _assert_fixture_only(db, org, marker)
        _restore_owner(db, org, marker)
        db.flush()
        ids = marker["mock_user_ids"]
        prefix = f"retention_demo_{marker['instance']}_"
        db.execute(text(
            "DELETE FROM oauth_temp_codes WHERE left(code, :length) = :prefix AND user_id IN :users"
        ).bindparams(bindparam("users", expanding=True)), {
            "length": len(prefix), "prefix": prefix, "users": [marker["owner_user_id"], *ids],
        })
        db.query(UserBurnoutReport).filter(UserBurnoutReport.id.in_(marker["survey_ids"].values()), UserBurnoutReport.organization_id == org.id).delete(synchronize_session=False)
        db.query(UserCorrelation).filter(UserCorrelation.id.in_(marker["correlation_ids"]), UserCorrelation.organization_id == org.id).delete(synchronize_session=False)
        db.query(Analysis).filter(Analysis.id.in_(marker["analysis_ids"].values()), Analysis.organization_id == org.id).delete(synchronize_session=False)
        db.query(OAuthProvider).filter(OAuthProvider.id.in_(marker["provider_ids"]), OAuthProvider.user_id.in_(ids)).delete(synchronize_session=False)
        db.query(UserLoginEvent).filter(UserLoginEvent.user_id.in_(ids)).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(ids), User.organization_id == org.id).delete(synchronize_session=False)
        db.query(Organization).filter(Organization.id == org.id).delete(synchronize_session=False)
        db.commit()
        return {"reset": True, "owner_restored": True}
    except Exception:
        db.rollback()
        raise


def run_demo_cleanup(db):
    from app.services.data_retention import read_retention_policy
    from app.services.retention_cleanup import cleanup_organization_data

    try:
        org, marker = _demo(db, lock=True)
        _assert_fixture_only(db, org, marker)
        if read_retention_policy(org).retention_days is None:
            raise ValueError("Enable the demo policy in Organization Management before running cleanup.")
        result = cleanup_organization_data(db, org.id, now=_now())
        output = asdict(result)
        for key in ("cutoff_at", "policy_updated_at"):
            output[key] = _iso(output[key])
        return output
    except Exception:
        db.rollback()
        raise


def login_link(db, member=None):
    """Use the existing single-use exchange flow, without changing passwords."""
    from app.auth.jwt import create_access_token
    from app.models import GitHubIntegration, JiraIntegration, LinearIntegration, User

    org, marker = _demo(db)
    if member is None:
        user = db.get(User, marker["owner_user_id"])
    else:
        user = db.query(User).filter(User.id.in_(marker["mock_user_ids"]), User.email == f"{member}@{DEMO_DOMAIN}").one()
    if user.organization_id != org.id or user.status != "active":
        raise ValueError("The selected account is no longer active in this demo.")
    if any(db.query(model.id).filter(model.user_id == user.id).first() is not None
           for model in (GitHubIntegration, JiraIntegration, LinearIntegration)):
        raise ValueError("This account has integrations. Use its existing session at /management or a fictional member login.")
    code = f"retention_demo_{marker['instance']}_{secrets.token_urlsafe(24)}"
    token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(minutes=30))
    db.execute(text("INSERT INTO oauth_temp_codes (code, jwt_token, user_id, expires_at, auth_method) VALUES (:code, :token, :user, :expires, :method)"),
               {"code": code, "token": token, "user": user.id, "expires": _now() + timedelta(minutes=5), "method": "local_retention_demo"})
    db.commit()
    return {"login_url": f"http://localhost:3000/auth/success?code={code}", "valid_for_minutes": 5, "account": user.name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("seed", "status", "upgrade", "cleanup", "restore", "reset", "login-link"):
        command = commands.add_parser(name)
        command.add_argument("--local-compose", action="store_true", help="Confirm use of this local Compose sandbox.")
        if name == "seed":
            command.add_argument("--email", required=True)
        if name == "login-link":
            command.add_argument("--member", choices=[key for key, _ in MOCK_MEMBERS])
    args = parser.parse_args()
    guard_local_database(os.environ.get("DATABASE_URL", ""), args.local_compose)
    if not Path("/.dockerenv").exists() or os.environ.get("DEBUG", "").lower() != "true":
        raise ValueError("Run this command in the local DEBUG-enabled Compose backend container.")
    from app.models import SessionLocal
    with SessionLocal() as db:
        if args.command == "seed":
            result = seed_demo(db, args.email)
        elif args.command == "status":
            result = demo_status(db)
        elif args.command == "upgrade":
            result = upgrade_demo(db)
        elif args.command == "restore":
            result = restore_membership(db)
        elif args.command == "reset":
            result = reset_demo(db)
        elif args.command == "cleanup":
            result = run_demo_cleanup(db)
        else:
            result = login_link(db, args.member)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception:
        # Never echo SQL parameters, database URLs, access tokens or auth codes.
        print("Demo operation failed. Check the local database schema; no automatic retry was performed.", file=sys.stderr)
        sys.exit(1)
