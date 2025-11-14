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
        """
        logger.info("=" * 60)
        logger.info("Starting scrape cycle")
        logger.info("=" * 60)

        # Check if we should scrape this month
        if not self.storage.should_scrape_this_month():
            logger.info("Monthly scrape already completed. Skipping until next month.")
            return

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

        comparison_result = None
        if previous_bulletin:
            comparison_result = self.comparator.compare_bulletins(previous_bulletin, parsed_data)

            if comparison_result['has_changes']:
                logger.info(f"CHANGES DETECTED: {len(comparison_result['changes'])} changes found")
                for change in comparison_result['changes']:
                    logger.info(f"  {change}")
            else:
                logger.info("No changes detected from previous bulletin")
        else:
            logger.info("No previous bulletin found (first run)")

        # Step 4: Send notification if changes detected
        if comparison_result and comparison_result['has_changes']:
            logger.info("Step 4: Sending notification...")
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
        else:
            logger.info("Step 4: No changes to notify")

        # Step 5: Update storage
        logger.info("Step 5: Updating storage...")
        self.storage.add_bulletin(parsed_data)

        # Mark this month as completed
        bulletin_month = parsed_data.get('bulletin_date')
        if bulletin_month:
            self.storage.mark_monthly_scrape_completed(bulletin_month)
            logger.info(f"Marked month {bulletin_month} as completed")

        logger.info("Scrape cycle completed successfully")
        logger.info("=" * 60)

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
