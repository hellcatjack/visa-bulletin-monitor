#!/usr/bin/env python3
"""
US Visa Bulletin Monitor
Monitors visa bulletin updates for China and sends SMS notifications for changes.
"""

import argparse
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import config
from src.logger import setup_logging
from src.orchestrator import VisaBulletinOrchestrator
from src.scheduler import VisaScraperSchedulerCron

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='US Visa Bulletin Monitor - Tracks China visa bulletin changes'
    )
    parser.add_argument(
        '--mode',
        choices=['schedule', 'once', 'test', 'status'],
        default='schedule',
        help='Run mode: schedule (continuous), once (single run), test (test notification), status (show status)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=config.LOG_LEVEL,
        help='Logging level'
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(config.LOG_FILE, args.log_level)

    logger.info("=" * 60)
    logger.info("US Visa Bulletin Monitor Starting")
    logger.info("=" * 60)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Notification method: {config.NOTIFICATION_METHOD}")
    logger.info(f"Timezone: {config.TIMEZONE}")
    logger.info(f"Scrape interval: {config.SCRAPE_INTERVAL_MINUTES} minutes")
    logger.info(f"Data directory: {config.DATA_DIR}")
    logger.info(f"Log file: {config.LOG_FILE}")

    # Validate notification configuration
    if config.NOTIFICATION_METHOD == 'email':
        if not all([config.SMTP_HOST, config.SMTP_USER, config.SMTP_PASSWORD,
                    config.EMAIL_FROM, config.EMAIL_TO]):
            logger.warning("Email credentials not fully configured!")
            logger.warning("Please set up .env file with email credentials")
            logger.warning("Copy .env.example to .env and fill in your credentials")

            if args.mode in ['test', 'schedule']:
                logger.error("Cannot run in this mode without email credentials")
                sys.exit(1)
    elif config.NOTIFICATION_METHOD == 'sms':
        if not all([config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN,
                    config.TWILIO_FROM_NUMBER, config.TWILIO_TO_NUMBER]):
            logger.warning("Twilio credentials not fully configured!")
            logger.warning("Please set up .env file with Twilio credentials for SMS notifications")
            logger.warning("Copy .env.example to .env and fill in your credentials")

            if args.mode in ['test', 'schedule']:
                logger.error("Cannot run in this mode without Twilio credentials")
                sys.exit(1)

    # Initialize orchestrator
    orchestrator = VisaBulletinOrchestrator(config)

    # Run based on mode
    if args.mode == 'status':
        # Show current status
        status = orchestrator.get_status()
        logger.info("=" * 60)
        logger.info("CURRENT STATUS")
        logger.info("=" * 60)
        logger.info(f"Last scrape: {status['last_scrape']}")
        logger.info(f"Last bulletin month: {status['last_bulletin_month']}")
        logger.info(f"Monthly scrape completed: {status['monthly_scrape_completed']}")
        logger.info(f"Latest bulletin in history: {status['latest_bulletin_data']}")
        logger.info(f"Should scrape this month: {status['should_scrape']}")
        logger.info("=" * 60)

    elif args.mode == 'test':
        # Test notification
        logger.info("Testing SMS notification...")
        success = orchestrator.test_notification()
        if success:
            logger.info("Test notification sent successfully!")
        else:
            logger.error("Test notification failed")
            sys.exit(1)

    elif args.mode == 'once':
        # Run scrape once
        logger.info("Running single scrape cycle...")
        orchestrator.run_scrape_cycle()
        logger.info("Single scrape completed")

    elif args.mode == 'schedule':
        # Run on schedule
        logger.info("Starting scheduled scraping...")
        logger.info("Will run every 15 minutes during US Eastern business hours (9 AM - 11 PM, Mon-Fri)")

        scheduler = VisaScraperSchedulerCron(
            scrape_callback=orchestrator.run_scrape_cycle,
            timezone=config.TIMEZONE
        )

        try:
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")

    logger.info("Program exiting")


if __name__ == '__main__':
    main()
