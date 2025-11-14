import requests
from bs4 import BeautifulSoup
import logging
from typing import Optional, Tuple
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class VisaBulletinScraper:
    """Scraper for US Visa Bulletin website"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_upcoming_bulletin_url(self) -> Optional[str]:
        """
        Fetch the main visa bulletin page and extract the 'Upcoming Visa Bulletin' link.
        The structure is: <ul id="recent_bulletins"> with <li class="current"> items.
        First <li class="current"> = current month
        Second <li class="current"> = upcoming month

        Returns:
            str: URL of the upcoming visa bulletin, or None if not found
        """
        try:
            logger.info(f"Fetching main page: {self.base_url}")
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the recent_bulletins ul element
            recent_bulletins = soup.find('ul', id='recent_bulletins')

            if not recent_bulletins:
                logger.warning("Could not find <ul id='recent_bulletins'>")
                return None

            # Find all <li class="current"> elements
            current_items = recent_bulletins.find_all('li', class_='current')

            if not current_items:
                logger.warning("No <li class='current'> items found")
                return None

            logger.info(f"Found {len(current_items)} current bulletin items")

            # Try to get the second one (index 1) for upcoming month
            # If it doesn't have a link (not published yet), fall back to first one
            target_item = None
            link = None

            if len(current_items) >= 2:
                logger.info("Checking second current item (upcoming month)...")
                second_item = current_items[1]
                link = second_item.find('a', href=True)

                if link:
                    logger.info("Upcoming month bulletin found (second item has link)")
                    target_item = second_item
                else:
                    logger.info("Second item has no link (upcoming month not published yet)")

            # If no valid second item, use the first one (current month)
            if not target_item and len(current_items) >= 1:
                logger.info("Using first current item (current month bulletin)")
                target_item = current_items[0]
                link = target_item.find('a', href=True)

            if link and target_item:
                url = urljoin(self.base_url, link['href'])
                link_text = link.get_text().strip()
                logger.info(f"Found bulletin: '{link_text}' at {url}")
                return url

            logger.warning("No valid link found in any current item")
            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching main page: {e}")
            return None

    def fetch_bulletin_content(self, bulletin_url: str) -> Optional[str]:
        """
        Fetch the HTML content of a specific bulletin page.

        Args:
            bulletin_url: URL of the bulletin to fetch

        Returns:
            str: HTML content of the page, or None if error
        """
        try:
            logger.info(f"Fetching bulletin content from: {bulletin_url}")
            response = self.session.get(bulletin_url, timeout=30)
            response.raise_for_status()
            return response.text

        except requests.RequestException as e:
            logger.error(f"Error fetching bulletin content: {e}")
            return None

    def get_bulletin_urls(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get both current and upcoming bulletin URLs.

        Returns:
            Tuple[Optional[str], Optional[str]]: (current_url, upcoming_url)
            Either can be None if not available.
        """
        try:
            logger.info(f"Fetching main page: {self.base_url}")
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            recent_bulletins = soup.find('ul', id='recent_bulletins')

            if not recent_bulletins:
                logger.warning("Could not find <ul id='recent_bulletins'>")
                return None, None

            current_items = recent_bulletins.find_all('li', class_='current')

            if not current_items:
                logger.warning("No <li class='current'> items found")
                return None, None

            logger.info(f"Found {len(current_items)} current bulletin items")

            current_url = None
            upcoming_url = None

            # First item = current month
            if len(current_items) >= 1:
                link = current_items[0].find('a', href=True)
                if link:
                    current_url = urljoin(self.base_url, link['href'])
                    link_text = link.get_text().strip()
                    logger.info(f"Current month bulletin: '{link_text}' at {current_url}")

            # Second item = upcoming month
            if len(current_items) >= 2:
                link = current_items[1].find('a', href=True)
                if link:
                    upcoming_url = urljoin(self.base_url, link['href'])
                    link_text = link.get_text().strip()
                    logger.info(f"Upcoming month bulletin: '{link_text}' at {upcoming_url}")

            return current_url, upcoming_url

        except requests.RequestException as e:
            logger.error(f"Error fetching main page: {e}")
            return None, None

    def scrape_latest_bulletin(self) -> Optional[Tuple[str, str]]:
        """
        Scrape the latest upcoming visa bulletin.

        Returns:
            Tuple[str, str]: (bulletin_url, html_content) or None if error
        """
        bulletin_url = self.get_upcoming_bulletin_url()
        if not bulletin_url:
            return None

        content = self.fetch_bulletin_content(bulletin_url)
        if not content:
            return None

        return bulletin_url, content

    def scrape_bulletin_by_url(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Scrape a specific bulletin by URL.

        Args:
            url: URL of the bulletin to scrape

        Returns:
            Tuple[str, str]: (bulletin_url, html_content) or None if error
        """
        if not url:
            return None

        content = self.fetch_bulletin_content(url)
        if not content:
            return None

        return url, content
