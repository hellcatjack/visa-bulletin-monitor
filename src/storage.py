import json
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class JSONStorage:
    """Manage JSON file storage for bulletin history and scraper state"""

    def __init__(self, history_file: str, state_file: str):
        """
        Initialize storage manager.

        Args:
            history_file: Path to bulletin history JSON file
            state_file: Path to scraper state JSON file
        """
        self.history_file = history_file
        self.state_file = state_file

        # Ensure directories exist
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

    def load_history(self) -> List[Dict]:
        """
        Load bulletin history from JSON file.

        Returns:
            List of bulletin dictionaries, newest first
        """
        if not os.path.exists(self.history_file):
            logger.info("No history file found, starting fresh")
            return []

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                logger.info(f"Loaded {len(history)} bulletins from history")
                return history
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing history file: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    def save_history(self, history: List[Dict]) -> bool:
        """
        Save bulletin history to JSON file.

        Args:
            history: List of bulletin dictionaries

        Returns:
            bool: True if saved successfully
        """
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(history)} bulletins to history")
            return True
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            return False

    def add_bulletin(self, bulletin_data: Dict) -> bool:
        """
        Add a new bulletin to history (avoiding duplicates).

        Args:
            bulletin_data: Parsed bulletin data

        Returns:
            bool: True if added successfully
        """
        history = self.load_history()

        # Check for duplicates based on bulletin_date
        bulletin_date = bulletin_data.get('bulletin_date')
        if bulletin_date:
            # Remove existing entry with same bulletin_date
            history = [b for b in history if b.get('bulletin_date') != bulletin_date]

        # Add new bulletin at the beginning
        history.insert(0, bulletin_data)

        # Keep only the last 12 months
        history = history[:12]

        return self.save_history(history)

    def get_latest_bulletin(self) -> Optional[Dict]:
        """
        Get the most recent bulletin from history.

        Returns:
            Dict: Latest bulletin data, or None if no history
        """
        history = self.load_history()
        if history:
            return history[0]
        return None

    def load_state(self) -> Dict:
        """
        Load scraper state from JSON file.

        Returns:
            Dict containing state info like:
            {
                'last_successful_scrape': 'ISO timestamp',
                'last_bulletin_month': 'YYYY-MM',
                'monthly_scrape_completed': bool
            }
        """
        if not os.path.exists(self.state_file):
            logger.info("No state file found, initializing new state")
            return {
                'last_successful_scrape': None,
                'last_bulletin_month': None,
                'monthly_scrape_completed': False
            }

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info(f"Loaded state: {state}")
                return state
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing state file: {e}")
            return self._get_default_state()
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return self._get_default_state()

    def save_state(self, state: Dict) -> bool:
        """
        Save scraper state to JSON file.

        Args:
            state: State dictionary

        Returns:
            bool: True if saved successfully
        """
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved state: {state}")
            return True
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            return False

    def mark_monthly_scrape_completed(self, bulletin_month: str) -> bool:
        """
        Update state after successfully scraping a bulletin.

        The monthly task is considered completed only when we find NEXT month's bulletin.
        For example, in November:
        - Scraping November bulletin -> monthly_scrape_completed = False (keep monitoring)
        - Scraping December bulletin -> monthly_scrape_completed = True (task done)

        Args:
            bulletin_month: Bulletin month in format 'YYYY-MM'

        Returns:
            bool: True if state updated successfully
        """
        state = self.load_state()
        state['last_successful_scrape'] = datetime.now().isoformat()
        state['last_bulletin_month'] = bulletin_month

        # Calculate next month
        now = datetime.now()
        year = now.year
        month = now.month

        next_month_num = month + 1
        next_year = year
        if next_month_num > 12:
            next_month_num = 1
            next_year += 1

        next_month = f"{next_year:04d}-{next_month_num:02d}"

        # Mark as completed only if we found next month's (or later) bulletin
        if bulletin_month >= next_month:
            state['monthly_scrape_completed'] = True
            logger.info(f"Scraped {bulletin_month} (>= {next_month}). Marking monthly task as completed.")
        else:
            state['monthly_scrape_completed'] = False
            logger.info(f"Scraped {bulletin_month} (< {next_month}). Continue monitoring for next month's bulletin.")

        return self.save_state(state)

    def should_scrape_this_month(self) -> bool:
        """
        Check if we should scrape this month.

        Logic: We should continue scraping until we find NEXT month's bulletin.
        For example, in November 2025:
        - If last bulletin was 2025-11 or earlier: continue scraping (waiting for 2025-12)
        - If last bulletin was 2025-12 or later: stop scraping (task completed)

        When we enter December, the logic resets and we wait for January's bulletin.

        Returns:
            bool: True if should scrape, False if already found next month's bulletin
        """
        state = self.load_state()

        # If never scraped, should scrape
        if not state.get('last_bulletin_month'):
            return True

        # Calculate next month
        now = datetime.now()
        year = now.year
        month = now.month

        next_month_num = month + 1
        next_year = year
        if next_month_num > 12:
            next_month_num = 1
            next_year += 1

        next_month = f"{next_year:04d}-{next_month_num:02d}"
        last_bulletin_month = state.get('last_bulletin_month')

        # If we've found next month's bulletin (or later), task completed for this month
        if last_bulletin_month >= next_month:
            logger.info(f"Found bulletin for {last_bulletin_month} (>= {next_month}). Monthly task completed.")
            return False

        # Otherwise, keep scraping - waiting for next month's bulletin
        logger.info(f"Last bulletin: {last_bulletin_month}, waiting for {next_month}. Continue scraping.")
        return True

    def _get_default_state(self) -> Dict:
        """Get default state structure"""
        return {
            'last_successful_scrape': None,
            'last_bulletin_month': None,
            'monthly_scrape_completed': False
        }
