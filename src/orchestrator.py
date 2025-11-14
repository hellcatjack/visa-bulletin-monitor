import logging
from typing import Optional
from datetime import datetime

from .scraper import VisaBulletinScraper
from .parser import VisaBulletinParser
from .comparator import BulletinComparator
from .notifier import SMSNotifier
from .email_notifier import EmailNotifier
from .storage import JSONStorage

logger = logging.getLogger(__name__)


class VisaBulletinOrchestrator:
    """Main orchestrator that coordinates all components"""

    def __init__(self, config):
        """
        Initialize orchestrator with all components.

        Args:
            config: Configuration module with all settings
        """
        self.config = config

        # Initialize components
        self.scraper = VisaBulletinScraper(config.VISA_BULLETIN_BASE_URL)
        self.parser = VisaBulletinParser()
        self.comparator = BulletinComparator()
        self.storage = JSONStorage(config.HISTORY_FILE, config.STATE_FILE)

        # Initialize notifier based on configuration
        self.notifier = None
        self.notification_method = config.NOTIFICATION_METHOD

        logger.info(f"Notification method: {self.notification_method}")

        if self.notification_method == 'email':
            # Initialize Email notifier
            if all([config.SMTP_HOST, config.SMTP_USER, config.SMTP_PASSWORD,
                    config.EMAIL_FROM, config.EMAIL_TO]):
                try:
                    self.notifier = EmailNotifier(
                        config.SMTP_HOST,
                        config.SMTP_PORT,
                        config.SMTP_USER,
                        config.SMTP_PASSWORD,
                        config.EMAIL_FROM,
                        config.EMAIL_TO,
                        config.SMTP_USE_TLS
                    )
                    logger.info("Email notifier initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Email notifier: {e}")
            else:
                logger.warning("Email credentials not configured, email notifications disabled")

        elif self.notification_method == 'sms':
            # Initialize SMS notifier
            if all([config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN,
                    config.TWILIO_FROM_NUMBER, config.TWILIO_TO_NUMBER]):
                try:
                    self.notifier = SMSNotifier(
                        config.TWILIO_ACCOUNT_SID,
                        config.TWILIO_AUTH_TOKEN,
                        config.TWILIO_FROM_NUMBER,
                        config.TWILIO_TO_NUMBER
                    )
                    logger.info("SMS notifier initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize SMS notifier: {e}")
            else:
                logger.warning("Twilio credentials not configured, SMS notifications disabled")
        else:
            logger.warning(f"Unknown notification method: {self.notification_method}")

    def run_scrape_cycle(self):
        """
        Execute one complete scrape cycle:
        1. Check if should scrape this month
        2. Scrape the bulletin
        3. Parse the data
        4. Compare with previous
        5. Send notification if changes detected
        6. Update storage

        Special handling for first run: If no history exists, will scrape both current
        and upcoming bulletins to enable comparison and notification on first run.
        """
        logger.info("=" * 60)
        logger.info("Starting scrape cycle")
        logger.info("=" * 60)

        # Check if we should scrape this month
        if not self.storage.should_scrape_this_month():
            logger.info("Monthly scrape already completed. Skipping until next month.")
            return

        # Check if this is the first run
        previous_bulletin = self.storage.get_latest_bulletin()
        is_first_run = previous_bulletin is None

        if is_first_run:
            logger.info("First run detected - will attempt to compare current and upcoming bulletins")
            self._handle_first_run()
        else:
            self._handle_regular_run()

        logger.info("Scrape cycle completed successfully")
        logger.info("=" * 60)

    def _handle_first_run(self):
        """
        Handle first run by scraping both current and upcoming bulletins for comparison.
        """
        # Step 1: Get both bulletin URLs
        logger.info("Step 1: Getting bulletin URLs...")
        current_url, upcoming_url = self.scraper.get_bulletin_urls()

        if not current_url and not upcoming_url:
            logger.error("Failed to get any bulletin URLs. Aborting cycle.")
            return

        # If we have both bulletins, compare them
        if current_url and upcoming_url:
            logger.info("Both current and upcoming bulletins available - comparing them")

            # Scrape and parse current month
            logger.info("Step 2a: Scraping current month bulletin...")
            current_result = self.scraper.scrape_bulletin_by_url(current_url)
            if not current_result:
                logger.warning("Failed to scrape current bulletin, falling back to upcoming only")
                self._scrape_and_save_single_bulletin(upcoming_url)
                return

            current_url, current_html = current_result
            current_data = self.parser.parse_bulletin(current_html)
            logger.info(f"Parsed current bulletin: {current_data.get('bulletin_date')}")

            # Scrape and parse upcoming month
            logger.info("Step 2b: Scraping upcoming month bulletin...")
            upcoming_result = self.scraper.scrape_bulletin_by_url(upcoming_url)
            if not upcoming_result:
                logger.warning("Failed to scrape upcoming bulletin, saving current only")
                self._save_bulletin_and_complete(current_data)
                return

            upcoming_url, upcoming_html = upcoming_result
            upcoming_data = self.parser.parse_bulletin(upcoming_html)
            logger.info(f"Parsed upcoming bulletin: {upcoming_data.get('bulletin_date')}")

            # Step 3: Compare bulletins
            logger.info("Step 3: Comparing current and upcoming bulletins...")
            comparison_result = self.comparator.compare_bulletins(current_data, upcoming_data)

            if comparison_result['has_changes']:
                logger.info(f"CHANGES DETECTED: {len(comparison_result['changes'])} changes found")
                for change in comparison_result['changes']:
                    logger.info(f"  {change}")

                # Step 4: Send notification
                logger.info("Step 4: Sending notification...")
                self._send_notification(comparison_result)
            else:
                logger.info("No changes detected between current and upcoming bulletins")
                logger.info("Step 4: No changes to notify")

            # Step 5: Save both bulletins
            logger.info("Step 5: Updating storage...")
            self.storage.add_bulletin(current_data)
            logger.info(f"Saved current bulletin: {current_data.get('bulletin_date')}")

            self._save_bulletin_and_complete(upcoming_data)

        else:
            # Only one bulletin available, save it without comparison
            available_url = upcoming_url or current_url
            logger.info(f"Only one bulletin available, saving without comparison")
            self._scrape_and_save_single_bulletin(available_url)

    def _handle_regular_run(self):
        """
        Handle regular run by scraping latest bulletin and comparing with history.
        """
        # Step 1: Scrape the bulletin
        logger.info("Step 1: Scraping visa bulletin...")
        scrape_result = self.scraper.scrape_latest_bulletin()

        if not scrape_result:
            logger.error("Failed to scrape bulletin. Aborting cycle.")
            return

        bulletin_url, html_content = scrape_result
        logger.info(f"Successfully scraped bulletin from: {bulletin_url}")

        # Step 2: Parse the bulletin
        logger.info("Step 2: Parsing bulletin data...")
        parsed_data = self.parser.parse_bulletin(html_content)

        if not parsed_data.get('final_action_dates') and not parsed_data.get('filing_dates'):
            logger.warning("No China-specific data found in bulletin. Check parsing logic.")
            return

        logger.info(f"Parsed bulletin for: {parsed_data.get('bulletin_date')}")
        logger.info(f"Final Action Dates: {parsed_data.get('final_action_dates')}")
        logger.info(f"Filing Dates: {parsed_data.get('filing_dates')}")

        # Step 3: Compare with previous bulletin
        logger.info("Step 3: Comparing with previous bulletin...")
        previous_bulletin = self.storage.get_latest_bulletin()

        comparison_result = self.comparator.compare_bulletins(previous_bulletin, parsed_data)

        if comparison_result['has_changes']:
            logger.info(f"CHANGES DETECTED: {len(comparison_result['changes'])} changes found")
            for change in comparison_result['changes']:
                logger.info(f"  {change}")

            # Step 4: Send notification
            logger.info("Step 4: Sending notification...")
            self._send_notification(comparison_result)
        else:
            logger.info("No changes detected from previous bulletin")
            logger.info("Step 4: No changes to notify")

        # Step 5: Update storage
        logger.info("Step 5: Updating storage...")
        self._save_bulletin_and_complete(parsed_data)

    def _scrape_and_save_single_bulletin(self, url: str):
        """Helper to scrape and save a single bulletin."""
        result = self.scraper.scrape_bulletin_by_url(url)
        if not result:
            logger.error("Failed to scrape bulletin")
            return

        bulletin_url, html_content = result
        parsed_data = self.parser.parse_bulletin(html_content)
        logger.info(f"Parsed bulletin for: {parsed_data.get('bulletin_date')}")

        self._save_bulletin_and_complete(parsed_data)

    def _send_notification(self, comparison_result):
        """Helper to send notification."""
        notification_message = self.comparator.format_changes_for_notification(comparison_result)

        if self.notifier:
            success = False
            if self.notification_method == 'email':
                success = self.notifier.send_visa_update(notification_message)
            elif self.notification_method == 'sms':
                success = self.notifier.send_sms(notification_message)

            if success:
                logger.info(f"Notification sent successfully via {self.notification_method}")
            else:
                logger.error(f"Failed to send notification via {self.notification_method}")
        else:
            logger.warning("Notifier not configured. Would have sent:")
            logger.info(notification_message)

    def _save_bulletin_and_complete(self, parsed_data):
        """Helper to save bulletin and mark as completed."""
        self.storage.add_bulletin(parsed_data)

        # Mark this month as completed
        bulletin_month = parsed_data.get('bulletin_date')
        if bulletin_month:
            self.storage.mark_monthly_scrape_completed(bulletin_month)
            logger.info(f"Marked month {bulletin_month} as completed")

    def test_notification(self):
        """Send a test notification to verify configuration"""
        if not self.notifier:
            logger.error(f"Notifier not configured. Please set {self.notification_method} credentials in .env")
            return False

        logger.info(f"Sending test notification via {self.notification_method}...")
        return self.notifier.send_test_message()

    def get_status(self) -> dict:
        """
        Get current status of the scraper.

        Returns:
            dict: Status information
        """
        state = self.storage.load_state()
        latest_bulletin = self.storage.get_latest_bulletin()

        return {
            'last_scrape': state.get('last_successful_scrape'),
            'last_bulletin_month': state.get('last_bulletin_month'),
            'monthly_scrape_completed': state.get('monthly_scrape_completed'),
            'latest_bulletin_data': latest_bulletin.get('bulletin_date') if latest_bulletin else None,
            'should_scrape': self.storage.should_scrape_this_month()
        }
