from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class VisaBulletinParser:
    """Parser for extracting China-specific visa bulletin data"""

    # Common visa categories to track
    VISA_CATEGORIES = [
        'EB-1',  # Employment First Preference
        'EB-2',  # Employment Second Preference
        'EB-3',  # Employment Third Preference
        'EB-4',  # Employment Fourth Preference (Special Immigrants)
        'EB-5',  # Employment Fifth Preference (Investors)
        'F1',    # Family First Preference (Unmarried Sons/Daughters of US Citizens)
        'F2A',   # Family Second Preference A (Spouses/Children of LPR)
        'F2B',   # Family Second Preference B (Unmarried 21+ Sons/Daughters of LPR)
        'F3',    # Family Third Preference (Married Sons/Daughters of US Citizens)
        'F4',    # Family Fourth Preference (Siblings of US Citizens)
    ]

    def __init__(self):
        self.china_identifiers = ['china', 'mainland', 'prc', 'mainland born']

    def parse_bulletin(self, html_content: str) -> Dict:
        """
        Parse the visa bulletin HTML and extract China-specific dates.

        Args:
            html_content: HTML content of the bulletin page

        Returns:
            Dict containing parsed data with structure:
            {
                'bulletin_date': 'YYYY-MM',
                'scrape_timestamp': 'ISO timestamp',
                'final_action_dates': {...},
                'filing_dates': {...},
                'raw_tables': [...]
            }
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract bulletin date (usually in title or header)
        bulletin_date = self._extract_bulletin_date(soup)

        # Find sections with specific headings
        # Look for: A. FINAL ACTION DATES FOR EMPLOYMENT-BASED PREFERENCE CASES
        #           B. DATES FOR FILING OF EMPLOYMENT-BASED VISA APPLICATIONS

        final_action_dates = {}
        filing_dates = {}
        raw_tables = []

        # Search for specific text patterns in the entire HTML
        html_text = soup.get_text()

        # Find all elements that might contain our target headings
        for element in soup.find_all(text=True):
            element_text = str(element).strip()
            # Normalize spaces (replace &nbsp; and multiple spaces)
            element_text_normalized = ' '.join(element_text.split())

            # Check for Final Action Dates heading
            if 'FINAL ACTION DATES FOR EMPLOYMENT-BASED' in element_text_normalized.upper():
                logger.info(f"Found Final Action heading: {element_text_normalized[:80]}")
                # Get the parent element
                parent = element.parent
                if parent:
                    # Find the next table after this element
                    table = parent.find_next('table')
                    if table:
                        table_data = self._parse_table(table)
                        if table_data:
                            china_data = self._extract_china_dates(table_data)
                            if china_data:
                                final_action_dates.update(china_data)
                                logger.info(f"Extracted Final Action Dates: {china_data}")

            # Check for Filing Dates heading
            if 'DATES FOR FILING OF EMPLOYMENT-BASED VISA APPLICATIONS' in element_text_normalized.upper():
                logger.info(f"Found Filing Dates heading: {element_text_normalized[:80]}")
                # Get the parent element
                parent = element.parent
                if parent:
                    # Find the next table after this element
                    table = parent.find_next('table')
                    if table:
                        table_data = self._parse_table(table)
                        if table_data:
                            china_data = self._extract_china_dates(table_data)
                            if china_data:
                                filing_dates.update(china_data)
                                logger.info(f"Extracted Filing Dates: {china_data}")

        # Also collect raw tables for debugging
        tables = soup.find_all('table')
        logger.info(f"Found {len(tables)} total tables in the bulletin")
        for i, table in enumerate(tables[:5]):  # Store first 5 for debugging
            table_data = self._parse_table(table)
            if table_data:
                raw_tables.append({
                    'table_index': i,
                    'data': table_data
                })

        return {
            'bulletin_date': bulletin_date,
            'scrape_timestamp': datetime.now().isoformat(),
            'final_action_dates': final_action_dates,
            'filing_dates': filing_dates,
            'raw_tables': raw_tables
        }

    def _extract_bulletin_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the bulletin date (e.g., '2024-11' for November 2024)"""
        # Look in title, headers, or prominent text
        title = soup.find('title')
        if title:
            # Example: "November 2024 Visa Bulletin"
            match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})',
                            title.get_text(), re.IGNORECASE)
            if match:
                month_name = match.group(1).capitalize()
                year = match.group(2)
                month_num = datetime.strptime(month_name, '%B').month
                return f"{year}-{month_num:02d}"

        # Try headers
        for header in soup.find_all(['h1', 'h2', 'h3']):
            match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})',
                            header.get_text(), re.IGNORECASE)
            if match:
                month_name = match.group(1).capitalize()
                year = match.group(2)
                month_num = datetime.strptime(month_name, '%B').month
                return f"{year}-{month_num:02d}"

        logger.warning("Could not extract bulletin date")
        return None

    def _parse_table(self, table) -> Optional[List[List[str]]]:
        """Parse an HTML table into a 2D list"""
        try:
            rows = []
            for tr in table.find_all('tr'):
                cells = []
                for td in tr.find_all(['td', 'th']):
                    # Get text and clean it
                    text = td.get_text(strip=True)
                    # Handle colspan/rowspan
                    cells.append(text)
                if cells:
                    rows.append(cells)
            return rows if rows else None
        except Exception as e:
            logger.error(f"Error parsing table: {e}")
            return None

    def _extract_china_dates(self, table_data: List[List[str]]) -> Dict[str, str]:
        """
        Extract China-specific dates from parsed table data.

        Returns:
            Dict mapping visa category to priority date (e.g., {'EB-2': '01JAN2020', 'EB-3': 'C'})
        """
        china_dates = {}

        # Find the header row
        header_row = None
        china_col_index = None

        for i, row in enumerate(table_data):
            # Look for China column
            for j, cell in enumerate(row):
                # Normalize spaces in cell text
                cell_normalized = ' '.join(cell.split()).lower()
                if any(identifier in cell_normalized for identifier in self.china_identifiers):
                    header_row = i
                    china_col_index = j
                    logger.info(f"Found China column '{cell}' at index {j} in row {i}")
                    break
            if china_col_index is not None:
                break

        if china_col_index is None:
            logger.warning("Could not find China column in table")
            return china_dates

        # Extract data rows
        for i in range(header_row + 1, len(table_data)):
            row = table_data[i]
            if len(row) <= china_col_index:
                continue

            # First column usually contains the visa category
            category = row[0].strip()
            date_value = row[china_col_index].strip()

            # Map employment-based categories
            # Employment table uses: 1st, 2nd, 3rd, Other Workers, 4th, 5th, etc.
            category_normalized = ' '.join(category.split()).lower()

            # Try to map to standard category names
            mapped_category = None

            if '1st' in category_normalized:
                mapped_category = 'EB-1'
            elif '2nd' in category_normalized:
                mapped_category = 'EB-2'
            elif '3rd' in category_normalized and 'other' not in category_normalized:
                mapped_category = 'EB-3'
            elif 'other workers' in category_normalized:
                mapped_category = 'EB-3 Other Workers'
            elif '4th' in category_normalized:
                mapped_category = 'EB-4'
            elif '5th' in category_normalized:
                if 'unreserved' in category_normalized:
                    mapped_category = 'EB-5 Unreserved'
                elif 'rural' in category_normalized:
                    mapped_category = 'EB-5 Rural'
                elif 'high unemployment' in category_normalized:
                    mapped_category = 'EB-5 High Unemployment'
                elif 'infrastructure' in category_normalized:
                    mapped_category = 'EB-5 Infrastructure'
                else:
                    mapped_category = 'EB-5'
            # Also check for family-based (F1, F2A, etc.)
            else:
                for visa_cat in self.VISA_CATEGORIES:
                    if visa_cat.lower() in category_normalized or category.upper() == visa_cat:
                        mapped_category = visa_cat
                        break

            if mapped_category:
                china_dates[mapped_category] = date_value

        return china_dates
