"""Tests for org-level automated survey recipient selection."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.app.services.survey_recipient_service import (
    get_saved_recipient_ids_for_org,
    save_survey_recipient_ids_for_org,
)


def _make_query(*, first=None, all_rows=None):
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.join.return_value = query
    query.first.return_value = first
    query.all.return_value = all_rows or []
    return query


class TestSurveyRecipientService(unittest.TestCase):
    def test_get_saved_recipient_ids_prefers_workspace_mapping(self):
        db = MagicMock()
        workspace_mapping = SimpleNamespace(survey_recipients=[11, 22])
        db.query.return_value = _make_query(first=workspace_mapping)

        recipient_ids = get_saved_recipient_ids_for_org(db, 7)

        self.assertEqual(recipient_ids, {11, 22})
        self.assertEqual(db.query.call_count, 1)

    def test_get_saved_recipient_ids_falls_back_to_legacy_integration(self):
        db = MagicMock()
        workspace_mapping = SimpleNamespace(survey_recipients=None)
        legacy_integration = SimpleNamespace(id=91, survey_recipients=[3, 5, 8])
        db.query.side_effect = [
            _make_query(first=workspace_mapping),
            _make_query(all_rows=[legacy_integration]),
        ]

        recipient_ids = get_saved_recipient_ids_for_org(db, 7)

        self.assertEqual(recipient_ids, {3, 5, 8})
        self.assertEqual(db.query.call_count, 2)

    def test_save_survey_recipient_ids_updates_workspace_mapping(self):
        db = MagicMock()
        workspace_mapping = SimpleNamespace(survey_recipients=None)
        db.query.return_value = _make_query(first=workspace_mapping)

        saved_mapping = save_survey_recipient_ids_for_org(db, 7, [1, 2, 3])

        self.assertIs(saved_mapping, workspace_mapping)
        self.assertEqual(workspace_mapping.survey_recipients, [1, 2, 3])

    def test_save_survey_recipient_ids_clears_workspace_mapping_when_reset(self):
        db = MagicMock()
        workspace_mapping = SimpleNamespace(survey_recipients=[1, 2, 3])
        db.query.return_value = _make_query(first=workspace_mapping)

        saved_mapping = save_survey_recipient_ids_for_org(db, 7, None)

        self.assertIs(saved_mapping, workspace_mapping)
        self.assertIsNone(workspace_mapping.survey_recipients)


if __name__ == "__main__":
    unittest.main()
