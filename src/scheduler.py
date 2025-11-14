import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)


class VisaScraperScheduler:
    """Scheduler for running the visa scraper at specific times"""

    def __init__(self, scrape_callback, timezone='America/New_York', interval_minutes=15):
        """
        Initialize the scheduler.

        Args:
            scrape_callback: Function to call when it's time to scrape
            timezone: Timezone for scheduling (default: US Eastern Time)
            interval_minutes: How often to run during business hours (default: 15)
        """
        self.scrape_callback = scrape_callback
        self.timezone = pytz.timezone(timezone)
        self.interval_minutes = interval_minutes
        self.scheduler = BlockingScheduler(timezone=self.timezone)

    def is_business_hours(self) -> bool:
        """
        Check if current time is during US business hours (9 AM - 5 PM ET, Mon-Fri).

        Returns:
            bool: True if during business hours
        """
        now = datetime.now(self.timezone)

        # Check if weekday (0 = Monday, 6 = Sunday)
        if now.weekday() >= 5:  # Saturday or Sunday
            logger.debug("Not a weekday, skipping")
            return False

        # Check if during business hours (9 AM - 5 PM)
        hour = now.hour
        if hour < 9 or hour >= 17:
            logger.debug(f"Outside business hours (current hour: {hour}), skipping")
            return False

        return True

    def wrapped_scrape_callback(self):
        """
        Wrapper that checks business hours before calling the scrape callback.
        """
        if not self.is_business_hours():
            logger.info("Outside business hours, skipping scrape")
            return

        logger.info("Within business hours, executing scrape")
        try:
            self.scrape_callback()
        except Exception as e:
            logger.error(f"Error in scrape callback: {e}", exc_info=True)

    def start(self):
        """
        Start the scheduler. Runs every interval_minutes.
        The callback will check if it's business hours before executing.
        """
        logger.info(f"Starting scheduler: every {self.interval_minutes} minutes in {self.timezone}")

        # Run every X minutes, but the callback will check if it's business hours
        self.scheduler.add_job(
            self.wrapped_scrape_callback,
            trigger='interval',
            minutes=self.interval_minutes,
            id='visa_scraper',
            name='Visa Bulletin Scraper',
            max_instances=1
        )

        # Also run immediately on startup if during business hours
        logger.info("Running initial check...")
        self.wrapped_scrape_callback()

        logger.info("Scheduler started. Press Ctrl+C to exit.")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
            self.scheduler.shutdown()

    def run_once(self):
        """
        Run the scraper once (for testing).
        Bypasses business hours check.
        """
        logger.info("Running scraper once (test mode)")
        try:
            self.scrape_callback()
        except Exception as e:
            logger.error(f"Error in scrape callback: {e}", exc_info=True)


class VisaScraperSchedulerCron:
    """
    Alternative scheduler using cron expressions for more precise control.
    Runs only during weekdays, business hours.
    """

    def __init__(self, scrape_callback, timezone='America/New_York', storage=None):
        """
        Initialize cron-based scheduler.

        Args:
            scrape_callback: Function to call when it's time to scrape
            timezone: Timezone for scheduling (default: US Eastern Time)
            storage: JSONStorage instance for checking monthly task status
        """
        self.scrape_callback = scrape_callback
        self.timezone = pytz.timezone(timezone)
        self.storage = storage
        self.scheduler = BlockingScheduler(timezone=self.timezone)

    def wrapped_scrape_callback(self):
        """
        Wrapper that checks if monthly task is completed before calling scrape callback.
        If we've already found next month's bulletin, reschedule to next month.
        """
        if self.storage:
            # Check BEFORE execution if we should skip
            if not self.storage.should_scrape_this_month():
                # Calculate when next month starts
                now = datetime.now(self.timezone)
                year = now.year
                month = now.month

                next_month_num = month + 1
                next_year = year
                if next_month_num > 12:
                    next_month_num = 1
                    next_year += 1

                next_month_start = datetime(next_year, next_month_num, 1, 9, 0, 0, tzinfo=self.timezone)

                logger.info(f"Monthly task already completed. Waiting until {next_month_start.strftime('%Y-%m-%d %H:%M %Z')}")
                return

        # Store state before execution
        state_before = self.storage.load_state() if self.storage else None
        monthly_completed_before = state_before.get('monthly_scrape_completed', False) if state_before else False

        # Execute the scrape
        try:
            self.scrape_callback()
        except Exception as e:
            logger.error(f"Error in scrape callback: {e}", exc_info=True)
            return

        # Check AFTER execution if state changed to completed
        if self.storage:
            state_after = self.storage.load_state()
            monthly_completed_after = state_after.get('monthly_scrape_completed', False)

            # If monthly task just completed, reschedule to next month
            if not monthly_completed_before and monthly_completed_after:
                self._reschedule_to_next_month()

    def _reschedule_to_next_month(self):
        """
        Reschedule the job to start from next month's 1st day at 9 AM.
        """
        now = datetime.now(self.timezone)
        year = now.year
        month = now.month

        next_month_num = month + 1
        next_year = year
        if next_month_num > 12:
            next_month_num = 1
            next_year += 1

        next_month_start = datetime(next_year, next_month_num, 1, 9, 0, 0, tzinfo=self.timezone)

        logger.info("=" * 60)
        logger.info("Monthly task completed! Rescheduling to next month...")
        logger.info(f"Next scrape will begin on: {next_month_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("=" * 60)

        # Remove the existing cron job if it exists
        try:
            self.scheduler.remove_job('visa_scraper_cron')
        except Exception as e:
            logger.debug(f"Could not remove cron job (may not exist): {e}")

        # Add a one-time job for next month's start
        self.scheduler.add_job(
            self._resume_regular_schedule,
            trigger='date',
            run_date=next_month_start,
            id='visa_scraper_resume',
            name='Resume Visa Bulletin Scraper'
        )

        # Confirm reschedule
        logger.info(f"Scheduler will remain idle until {next_month_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    def _resume_regular_schedule(self):
        """
        Resume regular cron schedule starting from next month.
        """
        logger.info("=" * 60)
        logger.info("Resuming regular scraping schedule")
        logger.info("=" * 60)

        # Execute the scrape first
        try:
            self.wrapped_scrape_callback()
        except Exception as e:
            logger.error(f"Error in scrape callback: {e}", exc_info=True)

        # Remove the one-time resume job
        try:
            self.scheduler.remove_job('visa_scraper_resume')
        except:
            pass

        # Re-add the regular cron job
        from apscheduler.triggers.cron import CronTrigger

        cron_trigger = CronTrigger(
            minute='*/15',
            hour='9-23',
            day_of_week='mon-fri',
            timezone=self.timezone
        )

        callback = self.wrapped_scrape_callback if self.storage else self.scrape_callback

        self.scheduler.add_job(
            callback,
            trigger=cron_trigger,
            id='visa_scraper_cron',
            name='Visa Bulletin Scraper (Cron)',
            max_instances=1
        )

        logger.info("Regular schedule resumed: every 15 minutes, Mon-Fri, 9 AM - 11 PM")

    def start(self):
        """
        Start the scheduler with cron trigger.
        Runs every 15 minutes, Monday-Friday, 9 AM - 11 PM ET.

        If monthly task is already completed at startup, immediately reschedule to next month.
        """
        logger.info(f"Starting cron scheduler in {self.timezone}")

        # Check if we should reschedule to next month immediately (at startup)
        if self.storage and not self.storage.should_scrape_this_month():
            logger.info("Monthly task already completed at startup")
            self._reschedule_to_next_month()
        else:
            # Add regular cron schedule
            cron_trigger = CronTrigger(
                minute='*/15',      # Every 15 minutes
                hour='9-23',        # 9 AM to 11 PM
                day_of_week='mon-fri',  # Monday to Friday
                timezone=self.timezone
            )

            # Use wrapped callback if storage is available
            callback = self.wrapped_scrape_callback if self.storage else self.scrape_callback

            self.scheduler.add_job(
                callback,
                trigger=cron_trigger,
                id='visa_scraper_cron',
                name='Visa Bulletin Scraper (Cron)',
                max_instances=1
            )

        # Show next few run times
        logger.info("Next scheduled runs:")
        jobs = self.scheduler.get_jobs()
        if jobs:
            previous_time = None
            now = datetime.now(self.timezone)
            for i in range(5):
                next_run_time = jobs[0].trigger.get_next_fire_time(previous_time, now)
                if next_run_time:
                    logger.info(f"  {i+1}. {next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    previous_time = next_run_time
                    now = next_run_time  # Must update now as well

        logger.info("Scheduler started. Press Ctrl+C to exit.")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
            self.scheduler.shutdown()
