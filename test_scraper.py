#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to check what the scraper is getting from the second <li> element
"""
import sys
import os
import io

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import config
from src.logger import setup_logging
from src.scraper import VisaBulletinScraper
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

# Set up logging
setup_logging(config.LOG_FILE, 'INFO')
logger = logging.getLogger(__name__)

def test_scraper_detailed():
    """Test the scraper and show detailed information about what it finds"""

    scraper = VisaBulletinScraper(config.VISA_BULLETIN_BASE_URL)

    print("=" * 80)
    print("Testing Visa Bulletin Scraper - Detailed Analysis")
    print("=" * 80)

    # Fetch main page
    try:
        response = scraper.session.get(scraper.base_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        print(f"\n[OK] Successfully fetched main page: {scraper.base_url}")

        # Find recent_bulletins
        recent_bulletins = soup.find('ul', id='recent_bulletins')

        if recent_bulletins:
            print(f"\n[OK] Found <ul id='recent_bulletins'>")

            # Find all <li class=\"current\"> elements
            current_items = recent_bulletins.find_all('li', class_='current')

            print(f"\n[OK] Found {len(current_items)} <li class='current'> items\n")

            # Show details of each item
            for i, item in enumerate(current_items, 1):
                print(f"\n{'='*60}")
                print(f"Item #{i}:")
                print(f"{'='*60}")

                # Get link
                link = item.find('a', href=True)
                if link:
                    url = urljoin(scraper.base_url, link['href'])
                    link_text = link.get_text().strip()
                    print(f"  Has link: YES")
                    print(f"  Link text: {link_text}")
                    print(f"  Link URL: {url}")
                else:
                    print(f"  Has link: NO")

                # Show full HTML of this item
                print(f"\n  Full HTML:")
                print(f"  {item.prettify()[:500]}")

            # Show what the current code returns
            print(f"\n{'='*80}")
            print("Current scraper.get_upcoming_bulletin_url() returns:")
            print(f"{'='*80}")
            bulletin_url = scraper.get_upcoming_bulletin_url()
            if bulletin_url:
                print(f"[OK] URL: {bulletin_url}")
            else:
                print("[ERROR] No URL returned")

        else:
            print("\n[ERROR] Could not find <ul id='recent_bulletins'>")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_scraper_detailed()
