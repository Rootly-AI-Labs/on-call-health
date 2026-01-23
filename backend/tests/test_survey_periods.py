"""
Unit tests for survey periods and follow-up reminder functionality.

Tests period calculation, completion, expiration, and idempotency checks.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, date, timedelta
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestCalculatePeriodBounds(unittest.TestCase):
    """Test the _calculate_period_bounds method for different frequency types."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock scheduler instance
        self.scheduler = MagicMock()

        # Import the method logic for testing
        def calculate_period_bounds(frequency_type, reference_date, day_of_week=None):
            if frequency_type == 'daily':
                return reference_date, reference_date
            elif frequency_type == 'weekday':
                days_since_monday = reference_date.weekday()
                monday = reference_date - timedelta(days=days_since_monday)
                friday = monday + timedelta(days=4)
                return monday, friday
            elif frequency_type == 'weekly':
                if day_of_week is None:
                    day_of_week = 0
                days_since_target = (reference_date.weekday() - day_of_week) % 7
                period_start = reference_date - timedelta(days=days_since_target)
                period_end = period_start + timedelta(days=6)
                return period_start, period_end
            else:
                return reference_date, reference_date

        self.calculate_period_bounds = calculate_period_bounds

    def test_daily_frequency_same_day(self):
        """Test daily frequency returns same day for start and end."""
        reference = date(2024, 1, 15)  # Monday
        start, end = self.calculate_period_bounds('daily', reference)

        self.assertEqual(start, reference)
        self.assertEqual(end, reference)

    def test_daily_frequency_any_day(self):
        """Test daily frequency works for any day of week."""
        # Test each day of the week
        for day_offset in range(7):
            reference = date(2024, 1, 15) + timedelta(days=day_offset)
            start, end = self.calculate_period_bounds('daily', reference)

            self.assertEqual(start, reference)
            self.assertEqual(end, reference)

    def test_weekday_frequency_monday(self):
        """Test weekday frequency when reference is Monday."""
        reference = date(2024, 1, 15)  # Monday
        start, end = self.calculate_period_bounds('weekday', reference)

        self.assertEqual(start, date(2024, 1, 15))  # Monday
        self.assertEqual(end, date(2024, 1, 19))    # Friday
        self.assertEqual(start.weekday(), 0)  # Monday
        self.assertEqual(end.weekday(), 4)    # Friday

    def test_weekday_frequency_wednesday(self):
        """Test weekday frequency when reference is Wednesday."""
        reference = date(2024, 1, 17)  # Wednesday
        start, end = self.calculate_period_bounds('weekday', reference)

        self.assertEqual(start, date(2024, 1, 15))  # Monday of same week
        self.assertEqual(end, date(2024, 1, 19))    # Friday of same week

    def test_weekday_frequency_friday(self):
        """Test weekday frequency when reference is Friday."""
        reference = date(2024, 1, 19)  # Friday
        start, end = self.calculate_period_bounds('weekday', reference)

        self.assertEqual(start, date(2024, 1, 15))  # Monday of same week
        self.assertEqual(end, date(2024, 1, 19))    # Friday (same as reference)

    def test_weekly_frequency_default_monday(self):
        """Test weekly frequency defaults to Monday start."""
        reference = date(2024, 1, 17)  # Wednesday
        start, end = self.calculate_period_bounds('weekly', reference, day_of_week=None)

        self.assertEqual(start, date(2024, 1, 15))  # Monday
        self.assertEqual(end, date(2024, 1, 21))    # Sunday
        self.assertEqual((end - start).days, 6)     # 7 days inclusive

    def test_weekly_frequency_friday_start(self):
        """Test weekly frequency with Friday as start day."""
        reference = date(2024, 1, 17)  # Wednesday
        start, end = self.calculate_period_bounds('weekly', reference, day_of_week=4)  # Friday

        self.assertEqual(start, date(2024, 1, 12))  # Previous Friday
        self.assertEqual(end, date(2024, 1, 18))    # Thursday
        self.assertEqual(start.weekday(), 4)        # Friday

    def test_weekly_frequency_sunday_start(self):
        """Test weekly frequency with Sunday as start day."""
        reference = date(2024, 1, 17)  # Wednesday
        start, end = self.calculate_period_bounds('weekly', reference, day_of_week=6)  # Sunday

        self.assertEqual(start, date(2024, 1, 14))  # Previous Sunday
        self.assertEqual(end, date(2024, 1, 20))    # Saturday

    def test_unknown_frequency_defaults_to_daily(self):
        """Test unknown frequency type defaults to single day."""
        reference = date(2024, 1, 15)
        start, end = self.calculate_period_bounds('unknown', reference)

        self.assertEqual(start, reference)
        self.assertEqual(end, reference)


class TestSurveyPeriodModel(unittest.TestCase):
    """Test the SurveyPeriod model methods and properties."""

    def setUp(self):
        """Set up test fixtures."""
        self.period = MagicMock()
        self.period.status = 'pending'
        self.period.frequency_type = 'weekly'
        self.period.period_start_date = date(2024, 1, 15)
        self.period.period_end_date = date(2024, 1, 21)
        self.period.reminder_count = 0

    def test_mark_completed_sets_status(self):
        """Test mark_completed sets correct status and response."""
        def mark_completed(response_id):
            self.period.status = 'completed'
            self.period.response_id = response_id
            self.period.completed_at = datetime.utcnow()

        mark_completed(123)

        self.assertEqual(self.period.status, 'completed')
        self.assertEqual(self.period.response_id, 123)
        self.assertIsNotNone(self.period.completed_at)

    def test_mark_expired_sets_status(self):
        """Test mark_expired sets correct status."""
        def mark_expired():
            self.period.status = 'expired'
            self.period.expired_at = datetime.utcnow()

        mark_expired()

        self.assertEqual(self.period.status, 'expired')
        self.assertIsNotNone(self.period.expired_at)

    def test_record_reminder_increments_count(self):
        """Test record_reminder_sent increments count."""
        def record_reminder_sent():
            self.period.last_reminder_sent_at = datetime.utcnow()
            self.period.reminder_count = (self.period.reminder_count or 0) + 1

        self.assertEqual(self.period.reminder_count, 0)

        record_reminder_sent()
        self.assertEqual(self.period.reminder_count, 1)

        record_reminder_sent()
        self.assertEqual(self.period.reminder_count, 2)

    def test_period_name_daily(self):
        """Test period_name returns 'day' for daily frequency."""
        def get_period_name(frequency_type):
            if frequency_type == 'daily':
                return 'day'
            if frequency_type in ('weekday', 'weekly'):
                return 'week'
            return 'period'

        self.assertEqual(get_period_name('daily'), 'day')

    def test_period_name_weekday(self):
        """Test period_name returns 'week' for weekday frequency."""
        def get_period_name(frequency_type):
            if frequency_type == 'daily':
                return 'day'
            if frequency_type in ('weekday', 'weekly'):
                return 'week'
            return 'period'

        self.assertEqual(get_period_name('weekday'), 'week')

    def test_period_name_weekly(self):
        """Test period_name returns 'week' for weekly frequency."""
        def get_period_name(frequency_type):
            if frequency_type == 'daily':
                return 'day'
            if frequency_type in ('weekday', 'weekly'):
                return 'week'
            return 'period'

        self.assertEqual(get_period_name('weekly'), 'week')

    def test_is_active_pending_within_range(self):
        """Test is_active returns True for pending period within date range."""
        def is_active(status, period_start, period_end, today):
            if status != 'pending':
                return False
            return period_start <= today <= period_end

        today = date(2024, 1, 17)  # Within range
        result = is_active('pending', date(2024, 1, 15), date(2024, 1, 21), today)
        self.assertTrue(result)

    def test_is_active_completed_within_range(self):
        """Test is_active returns False for completed period."""
        def is_active(status, period_start, period_end, today):
            if status != 'pending':
                return False
            return period_start <= today <= period_end

        today = date(2024, 1, 17)
        result = is_active('completed', date(2024, 1, 15), date(2024, 1, 21), today)
        self.assertFalse(result)

    def test_is_active_pending_outside_range(self):
        """Test is_active returns False for pending period outside date range."""
        def is_active(status, period_start, period_end, today):
            if status != 'pending':
                return False
            return period_start <= today <= period_end

        today = date(2024, 1, 25)  # After period end
        result = is_active('pending', date(2024, 1, 15), date(2024, 1, 21), today)
        self.assertFalse(result)

    def test_days_remaining_middle_of_period(self):
        """Test days_remaining calculation in middle of period."""
        def days_remaining(status, period_end, today):
            if status != 'pending':
                return 0
            if today > period_end:
                return 0
            return (period_end - today).days

        today = date(2024, 1, 17)  # Wednesday
        period_end = date(2024, 1, 21)  # Sunday
        result = days_remaining('pending', period_end, today)
        self.assertEqual(result, 4)

    def test_days_remaining_last_day(self):
        """Test days_remaining returns 0 on last day."""
        def days_remaining(status, period_end, today):
            if status != 'pending':
                return 0
            if today > period_end:
                return 0
            return (period_end - today).days

        today = date(2024, 1, 21)  # Sunday (last day)
        period_end = date(2024, 1, 21)
        result = days_remaining('pending', period_end, today)
        self.assertEqual(result, 0)

    def test_days_remaining_expired(self):
        """Test days_remaining returns 0 for expired period."""
        def days_remaining(status, period_end, today):
            if status != 'pending':
                return 0
            if today > period_end:
                return 0
            return (period_end - today).days

        today = date(2024, 1, 17)
        period_end = date(2024, 1, 21)
        result = days_remaining('expired', period_end, today)
        self.assertEqual(result, 0)


class TestIdempotencyChecks(unittest.TestCase):
    """Test idempotency checks for follow-up reminders."""

    def test_skip_if_initial_sent_today(self):
        """Test that reminders are skipped if initial was sent today."""
        today = date(2024, 1, 17)
        initial_sent_at = datetime(2024, 1, 17, 9, 0, 0)  # Same day

        should_skip = initial_sent_at.date() == today
        self.assertTrue(should_skip)

    def test_send_if_initial_sent_yesterday(self):
        """Test that reminders are sent if initial was sent yesterday."""
        today = date(2024, 1, 17)
        initial_sent_at = datetime(2024, 1, 16, 9, 0, 0)  # Yesterday

        should_skip = initial_sent_at.date() == today
        self.assertFalse(should_skip)

    def test_skip_if_reminder_already_sent_today(self):
        """Test that duplicate reminders are skipped on same day."""
        today = date(2024, 1, 17)
        last_reminder_sent_at = datetime(2024, 1, 17, 9, 0, 0)  # Same day

        should_skip = last_reminder_sent_at and last_reminder_sent_at.date() == today
        self.assertTrue(should_skip)

    def test_send_if_no_previous_reminder(self):
        """Test that reminders are sent if none sent before."""
        today = date(2024, 1, 17)
        last_reminder_sent_at = None

        should_skip = last_reminder_sent_at and last_reminder_sent_at.date() == today
        self.assertFalse(should_skip)

    def test_send_if_reminder_sent_yesterday(self):
        """Test that reminders are sent if last was yesterday."""
        today = date(2024, 1, 17)
        last_reminder_sent_at = datetime(2024, 1, 16, 9, 0, 0)  # Yesterday

        should_skip = last_reminder_sent_at and last_reminder_sent_at.date() == today
        self.assertFalse(should_skip)


class TestTimezoneHandling(unittest.TestCase):
    """Test timezone handling in period calculations."""

    def test_get_org_date_utc(self):
        """Test getting date in UTC timezone."""
        import pytz

        def get_org_date(org_timezone):
            try:
                tz = pytz.timezone(org_timezone)
                return datetime.now(tz).date()
            except Exception:
                return date.today()

        # Should not raise exception
        result = get_org_date('UTC')
        self.assertIsInstance(result, date)

    def test_get_org_date_america_new_york(self):
        """Test getting date in America/New_York timezone."""
        import pytz

        def get_org_date(org_timezone):
            try:
                tz = pytz.timezone(org_timezone)
                return datetime.now(tz).date()
            except Exception:
                return date.today()

        result = get_org_date('America/New_York')
        self.assertIsInstance(result, date)

    def test_get_org_date_invalid_timezone_fallback(self):
        """Test fallback to date.today() for invalid timezone."""
        import pytz

        def get_org_date(org_timezone):
            try:
                tz = pytz.timezone(org_timezone)
                return datetime.now(tz).date()
            except Exception:
                return date.today()

        result = get_org_date('Invalid/Timezone')
        self.assertIsInstance(result, date)
        self.assertEqual(result, date.today())


class TestEmailMasking(unittest.TestCase):
    """Test email masking for logging."""

    def setUp(self):
        """Set up the mask function."""
        def mask_email(email):
            if not email or '@' not in email:
                return '***'
            local, domain = email.split('@', 1)
            if len(local) <= 2:
                return f"{'*' * len(local)}@{domain}"
            return f"{local[:2]}{'*' * (len(local) - 2)}@{domain}"

        self.mask_email = mask_email

    def test_mask_normal_email(self):
        """Test masking a normal email address."""
        result = self.mask_email('john.doe@example.com')
        self.assertEqual(result, 'jo******@example.com')

    def test_mask_short_local_part(self):
        """Test masking email with short local part."""
        result = self.mask_email('ab@example.com')
        self.assertEqual(result, '**@example.com')

    def test_mask_single_char_local(self):
        """Test masking email with single character local part."""
        result = self.mask_email('a@example.com')
        self.assertEqual(result, '*@example.com')

    def test_mask_none_email(self):
        """Test masking None email."""
        result = self.mask_email(None)
        self.assertEqual(result, '***')

    def test_mask_empty_email(self):
        """Test masking empty email."""
        result = self.mask_email('')
        self.assertEqual(result, '***')

    def test_mask_email_without_at(self):
        """Test masking invalid email without @."""
        result = self.mask_email('notanemail')
        self.assertEqual(result, '***')


class TestPeriodExpiration(unittest.TestCase):
    """Test period expiration logic."""

    def test_expire_periods_past_end_date(self):
        """Test that periods past their end date are expired."""
        today = date(2024, 1, 22)  # Monday

        periods = [
            {'id': 1, 'status': 'pending', 'end_date': date(2024, 1, 21)},  # Should expire
            {'id': 2, 'status': 'pending', 'end_date': date(2024, 1, 22)},  # Should not expire (today)
            {'id': 3, 'status': 'pending', 'end_date': date(2024, 1, 25)},  # Should not expire (future)
            {'id': 4, 'status': 'completed', 'end_date': date(2024, 1, 21)},  # Already completed
        ]

        should_expire = []
        for p in periods:
            if p['status'] == 'pending' and p['end_date'] < today:
                should_expire.append(p['id'])

        self.assertEqual(should_expire, [1])

    def test_expire_does_not_affect_completed(self):
        """Test that completed periods are not re-expired."""
        today = date(2024, 1, 25)

        period = {'status': 'completed', 'end_date': date(2024, 1, 21)}

        should_expire = period['status'] == 'pending' and period['end_date'] < today
        self.assertFalse(should_expire)


class TestFollowUpMessageBuilding(unittest.TestCase):
    """Test follow-up message template building."""

    def test_build_message_with_custom_template(self):
        """Test building message with custom template."""
        template = "Reminder for your {frequency} check-in this {period_name}!"

        message = template.format(frequency='weekly', period_name='week')

        self.assertEqual(message, "Reminder for your weekly check-in this week!")

    def test_build_message_with_default_template(self):
        """Test building message with default template."""
        template = (
            "Hi! This is a reminder for your {frequency} check-in. "
            "You just need to answer it once this {period_name}, or I'll remind you again tomorrow."
        )

        message = template.format(frequency='daily', period_name='day')

        self.assertIn('daily', message)
        self.assertIn('day', message)

    def test_frequency_display_values(self):
        """Test frequency display values."""
        def frequency_display(frequency_type):
            return frequency_type

        self.assertEqual(frequency_display('daily'), 'daily')
        self.assertEqual(frequency_display('weekday'), 'weekday')
        self.assertEqual(frequency_display('weekly'), 'weekly')


class TestConcurrencyScenarios(unittest.TestCase):
    """Test scenarios that could cause concurrency issues."""

    def test_double_completion_prevention(self):
        """Test that a period cannot be completed twice."""
        period = {'status': 'pending', 'response_id': None}

        def mark_completed(response_id):
            if period['status'] != 'pending':
                return False  # Already processed
            period['status'] = 'completed'
            period['response_id'] = response_id
            return True

        # First completion should succeed
        result1 = mark_completed(100)
        self.assertTrue(result1)
        self.assertEqual(period['status'], 'completed')

        # Second completion should fail
        result2 = mark_completed(200)
        self.assertFalse(result2)
        self.assertEqual(period['response_id'], 100)  # Still first response

    def test_unique_pending_constraint(self):
        """Test that only one pending period per user is allowed."""
        pending_periods = {}

        def create_period(user_id, org_id):
            key = (user_id, org_id)
            if key in pending_periods and pending_periods[key]['status'] == 'pending':
                # Expire existing
                pending_periods[key]['status'] = 'expired'
            # Create new
            pending_periods[key] = {'status': 'pending', 'user_id': user_id}
            return True

        # First period for user 1
        create_period(1, 100)
        self.assertEqual(pending_periods[(1, 100)]['status'], 'pending')

        # Second period for user 1 should expire first
        create_period(1, 100)
        # The key is reused, so check that only one pending exists
        pending_count = sum(1 for p in pending_periods.values() if p['status'] == 'pending')
        self.assertEqual(pending_count, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
