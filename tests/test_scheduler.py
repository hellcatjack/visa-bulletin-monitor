import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytz

from src.scheduler import VisaScraperScheduler, VisaScraperSchedulerCron


class FrozenDateTime(datetime):
    """Helper datetime subclass for freezing time in tests."""

    frozen_value = None

    @classmethod
    def freeze(cls, value: datetime) -> None:
        cls.frozen_value = value

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        if cls.frozen_value is None:
            return super().now(tz)
        if tz is None:
            return cls.frozen_value
        return cls.frozen_value.astimezone(tz)

    @classmethod
    def reset(cls) -> None:
        cls.frozen_value = None


class MockBlockingScheduler:
    """Minimal scheduler stub for unit tests."""

    def __init__(self, timezone=None):
        self.timezone = timezone
        self.jobs = []
        self.removed_jobs = []

    def add_job(self, func, **kwargs):
        job = SimpleNamespace(func=func, **kwargs)
        self.jobs.append(job)
        return job

    def remove_job(self, job_id):
        self.removed_jobs.append(job_id)
        self.jobs = [job for job in self.jobs if getattr(job, 'id', None) != job_id]

    def get_jobs(self):
        return self.jobs

    def start(self):
        pass

    def shutdown(self):
        pass


class SchedulerTestCase(unittest.TestCase):
    """Common setup for scheduler tests."""

    def setUp(self):
        self.blocking_patcher = patch('src.scheduler.BlockingScheduler', MockBlockingScheduler)
        self.blocking_patcher.start()
        self.addCleanup(self.blocking_patcher.stop)
        self.tz = pytz.timezone('America/New_York')

    def tearDown(self):
        FrozenDateTime.reset()

    def freeze_time(self, year, month, day, hour, minute=0):
        FrozenDateTime.freeze(self.tz.localize(datetime(year, month, day, hour, minute)))


class TestVisaScraperScheduler(SchedulerTestCase):
    def test_is_business_hours_true_weekday(self):
        scheduler = VisaScraperScheduler(scrape_callback=Mock(), timezone='America/New_York')
        with patch('src.scheduler.datetime', FrozenDateTime):
            self.freeze_time(2025, 11, 17, 10)  # Monday 10 AM ET
            self.assertTrue(scheduler.is_business_hours())

    def test_is_business_hours_false_weekend(self):
        scheduler = VisaScraperScheduler(scrape_callback=Mock(), timezone='America/New_York')
        with patch('src.scheduler.datetime', FrozenDateTime):
            self.freeze_time(2025, 11, 16, 10)  # Sunday 10 AM ET
            self.assertFalse(scheduler.is_business_hours())

    def test_wrapped_scrape_callback_runs_only_during_business_hours(self):
        callback = Mock()
        scheduler = VisaScraperScheduler(scrape_callback=callback, timezone='America/New_York')

        # Outside hours -> should not run
        with patch('src.scheduler.datetime', FrozenDateTime):
            self.freeze_time(2025, 11, 17, 8)
            scheduler.wrapped_scrape_callback()
        self.assertEqual(callback.call_count, 0)

        # During hours -> should run
        with patch('src.scheduler.datetime', FrozenDateTime):
            self.freeze_time(2025, 11, 17, 10)
            scheduler.wrapped_scrape_callback()
        self.assertEqual(callback.call_count, 1)

    def test_run_once_bypasses_business_hours(self):
        callback = Mock()
        scheduler = VisaScraperScheduler(scrape_callback=callback, timezone='America/New_York')
        scheduler.run_once()
        callback.assert_called_once()


class CompletionTrackingStorage:
    """Test double for storage that flips completion flag after scrape."""

    def __init__(self):
        self.monthly_completed = False
        self.should_calls = 0

    def should_scrape_this_month(self):
        self.should_calls += 1
        return True

    def load_state(self):
        return {'monthly_scrape_completed': self.monthly_completed}

    def mark_completed(self):
        self.monthly_completed = True


class AlwaysCompleteStorage:
    """Storage double always reporting monthly completion."""

    def __init__(self):
        self.should_calls = 0
        self.state_calls = 0

    def should_scrape_this_month(self):
        self.should_calls += 1
        return False

    def load_state(self):
        self.state_calls += 1
        return {'monthly_scrape_completed': True}


class RecordingScheduler(MockBlockingScheduler):
    """Scheduler stub that records added jobs."""

    def __init__(self, timezone=None):
        super().__init__(timezone)
        self.add_job_calls = []

    def add_job(self, func, **kwargs):
        self.add_job_calls.append({'func': func, **kwargs})
        return super().add_job(func, **kwargs)


class TestVisaScraperSchedulerCron(SchedulerTestCase):
    def test_skip_when_monthly_task_completed(self):
        storage = AlwaysCompleteStorage()
        callback = Mock()
        cron = VisaScraperSchedulerCron(callback, timezone='America/New_York', storage=storage)

        with patch('src.scheduler.datetime', FrozenDateTime):
            self.freeze_time(2025, 11, 15, 12)
            cron.wrapped_scrape_callback()

        callback.assert_not_called()
        self.assertEqual(storage.should_calls, 1)
        self.assertEqual(storage.state_calls, 1)

    def test_reschedule_triggered_after_completion(self):
        storage = CompletionTrackingStorage()

        def fake_scrape():
            storage.mark_completed()

        cron = VisaScraperSchedulerCron(fake_scrape, timezone='America/New_York', storage=storage)
        cron.scheduler = RecordingScheduler(cron.timezone)

        with patch('src.scheduler.datetime', FrozenDateTime):
            self.freeze_time(2025, 11, 15, 12)
            cron.wrapped_scrape_callback()

        self.assertEqual(storage.should_calls, 1)
        self.assertEqual(len(cron.scheduler.add_job_calls), 1)
        resume_job = cron.scheduler.add_job_calls[0]
        self.assertEqual(resume_job['id'], 'visa_scraper_resume')
        run_date = resume_job['run_date']
        self.assertEqual(run_date.month, 12)
        self.assertEqual(run_date.day, 1)
        self.assertEqual(run_date.hour, 9)
        self.assertEqual(run_date.tzinfo.zone, 'America/New_York')

    def test_pause_until_blocks_retries_after_failure(self):
        callback = Mock(side_effect=RuntimeError("boom"))
        storage = CompletionTrackingStorage()
        cron = VisaScraperSchedulerCron(callback, timezone='America/New_York', storage=storage)

        with patch('src.scheduler.datetime', FrozenDateTime):
            base_time = self.tz.localize(datetime(2025, 11, 15, 9, 0))
            FrozenDateTime.freeze(base_time)
            cron.wrapped_scrape_callback()
            self.assertEqual(callback.call_count, 1)
            expected_resume = base_time + timedelta(minutes=15)
            self.assertEqual(cron.pause_until, expected_resume)

            # Still within pause window -> should skip and not call again
            FrozenDateTime.freeze(base_time + timedelta(minutes=5))
            cron.wrapped_scrape_callback()
            self.assertEqual(callback.call_count, 1)

    def test_pause_clears_after_successful_retry(self):
        call_order = []

        def flaky_callback():
            call_order.append('called')
            if len(call_order) == 1:
                raise RuntimeError("temporary")

        storage = CompletionTrackingStorage()
        cron = VisaScraperSchedulerCron(flaky_callback, timezone='America/New_York', storage=storage)

        with patch('src.scheduler.datetime', FrozenDateTime):
            base_time = self.tz.localize(datetime(2025, 11, 14, 15, 0))
            FrozenDateTime.freeze(base_time)
            cron.wrapped_scrape_callback()
            self.assertIsNotNone(cron.pause_until)

            FrozenDateTime.freeze(base_time + timedelta(minutes=20))
            cron.wrapped_scrape_callback()
            self.assertIsNone(cron.pause_until)
            self.assertEqual(len(call_order), 2)


if __name__ == '__main__':
    unittest.main()
