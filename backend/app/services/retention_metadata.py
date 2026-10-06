"""Result eligibility projections that never transfer full report JSON."""
from types import SimpleNamespace

from sqlalchemy import Text, and_, case, cast, func, or_

from ..models import Analysis


def result_present_expression():
    return and_(Analysis.results.isnot(None), cast(Analysis.results, Text).notin_(("null", "{}", '""')))


def metadata_query(db, *, include_error_content=False):
    columns = [
        Analysis.id, Analysis.status, Analysis.config, Analysis.rootly_integration_id,
        Analysis.is_saved, Analysis.is_auto_refresh, Analysis.auto_refresh_interval,
        Analysis.created_at, Analysis.completed_at, Analysis.results_generated_at, Analysis.error_generated_at,
        result_present_expression().label("has_results"),
        or_(Analysis.results.is_(None), cast(Analysis.results, Text) == "null").label("result_missing"),
        and_(Analysis.error_message.isnot(None), Analysis.error_message != "").label("has_error"),
    ]
    if include_error_content:
        columns.append(Analysis.error_message)
    return db.query(*columns)


def metadata_snapshot(row):
    values = dict(row._mapping)
    values["results"] = True if values.pop("has_results") else None
    has_error = values.pop("has_error")
    values.setdefault("error_message", "present" if has_error else None)
    return SimpleNamespace(**values)


def cleanup_candidate_expression(cutoff, pending_ids):
    generation = func.coalesce(Analysis.results_generated_at, case(
        (Analysis.status == "completed", Analysis.completed_at), else_=None,
    ))
    return or_(
        generation.is_(None), generation < cutoff,
        Analysis.status.in_(("pending", "running")),
        and_(Analysis.error_message.isnot(None), Analysis.error_message != "", or_(
            Analysis.error_generated_at.is_(None), Analysis.error_generated_at < cutoff,
        )),
        Analysis.id.in_(pending_ids),
    )
