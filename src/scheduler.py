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

    def __init__(self, scrape_callback, timezone='America/New_York'):
        """
        Initialize cron-based scheduler.

        Args:
            scrape_callback: Function to call when it's time to scrape
            timezone: Timezone for scheduling (default: US Eastern Time)
        """
        self.scrape_callback = scrape_callback
        self.timezone = pytz.timezone(timezone)
        self.scheduler = BlockingScheduler(timezone=self.timezone)

    def start(self):
        """
        Start the scheduler with cron trigger.
        Runs every 15 minutes, Monday-Friday, 9 AM - 5 PM ET.
        """
        logger.info(f"Starting cron scheduler in {self.timezone}")

        # Cron: every 15 minutes (*/15), every hour from 9-16 (9AM-4:45PM), Mon-Fri
        cron_trigger = CronTrigger(
            minute='*/15',      # Every 15 minutes
            hour='9-23',        # 9 AM to 4 PM (last run at 4:45 PM)
            day_of_week='mon-fri',  # Monday to Friday
            timezone=self.timezone
        )

        self.scheduler.add_job(
            self.scrape_callback,
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
