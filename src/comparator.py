import logging
from typing import Dict, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class BulletinComparator:
    """Compare visa bulletins and detect changes"""

    def __init__(self):
        pass

    def compare_bulletins(self, previous: Dict, current: Dict) -> Dict:
        """
        Compare two bulletins and identify changes.

        Args:
            previous: Previous bulletin data
            current: Current bulletin data

        Returns:
            Dict containing:
            {
                'has_changes': bool,
                'changes': [
                    {
                        'category': 'EB-2',
                        'table_type': 'Final Action Dates' or 'Filing Dates',
                        'old_date': '01JAN2020',
                        'new_date': '15FEB2020',
                        'status': 'advanced' or 'retrogressed' or 'unchanged' or 'changed'
                    },
                    ...
                ]
            }
        """
        changes = []

        # Compare Final Action Dates
        final_changes = self._compare_date_sets(
            previous.get('final_action_dates', {}),
            current.get('final_action_dates', {}),
            'Final Action Dates'
        )
        changes.extend(final_changes)

        # Compare Filing Dates
        filing_changes = self._compare_date_sets(
            previous.get('filing_dates', {}),
            current.get('filing_dates', {}),
            'Filing Dates'
        )
        changes.extend(filing_changes)

        return {
            'has_changes': len(changes) > 0,
            'previous_bulletin': previous.get('bulletin_date'),
            'current_bulletin': current.get('bulletin_date'),
            'changes': changes
        }

    def _compare_date_sets(self, old_dates: Dict, new_dates: Dict, table_type: str) -> List[Dict]:
        """Compare two sets of dates (either Final Action or Filing)"""
        changes = []

        # Get all categories present in either old or new
        all_categories = set(old_dates.keys()) | set(new_dates.keys())

        for category in sorted(all_categories):
            old_date = old_dates.get(category, 'N/A')
            new_date = new_dates.get(category, 'N/A')

            if old_date != new_date:
                status = self._determine_change_status(old_date, new_date)
                days_diff = self._calculate_days_difference(old_date, new_date)

                changes.append({
                    'category': category,
                    'table_type': table_type,
                    'old_date': old_date,
                    'new_date': new_date,
                    'status': status,
                    'days_diff': days_diff
                })

        return changes

    def _determine_change_status(self, old_date: str, new_date: str) -> str:
        """
        Determine if the date advanced, retrogressed, or changed status.

        Returns:
            'advanced', 'retrogressed', 'became_current', 'became_unavailable', or 'changed'
        """
        # Handle special values
        if new_date.upper() == 'C' and old_date.upper() != 'C':
            return 'became_current'
        elif new_date.upper() == 'U' and old_date.upper() != 'U':
            return 'became_unavailable'
        elif old_date.upper() == 'C' and new_date.upper() != 'C':
            return 'retrogressed_from_current'
        elif old_date.upper() == 'U' and new_date.upper() != 'U':
            return 'became_available'

        # Try to parse and compare dates
        old_parsed = self._parse_priority_date(old_date)
        new_parsed = self._parse_priority_date(new_date)

        if old_parsed and new_parsed:
            if new_parsed > old_parsed:
                return 'advanced'
            elif new_parsed < old_parsed:
                return 'retrogressed'

        return 'changed'

    def _parse_priority_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse priority date strings like '01JAN2020' to datetime.

        Args:
            date_str: Date string in format like '01JAN2020' or '15FEB2021'

        Returns:
            datetime object or None if unparseable
        """
        if not date_str or date_str.upper() in ['C', 'U', 'N/A']:
            return None

        # Common format: 01JAN2020, 15FEB2021
        match = re.match(r'(\d{1,2})([A-Z]{3})(\d{2,4})', date_str.upper())
        if match:
            day = int(match.group(1))
            month_str = match.group(2)
            year_str = match.group(3)

            # Handle 2-digit year (e.g., "22" -> "2022")
            if len(year_str) == 2:
                year = 2000 + int(year_str)
            else:
                year = int(year_str)

            try:
                date_obj = datetime.strptime(f"{day} {month_str} {year}", "%d %b %Y")
                return date_obj
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None

        return None

    def _calculate_days_difference(self, old_date: str, new_date: str) -> Optional[int]:
        """
        Calculate the difference in days between two priority dates.

        Args:
            old_date: Old date string
            new_date: New date string

        Returns:
            int: Positive for forward movement, negative for retrogression, None if can't calculate
        """
        old_parsed = self._parse_priority_date(old_date)
        new_parsed = self._parse_priority_date(new_date)

        if old_parsed and new_parsed:
            diff = (new_parsed - old_parsed).days
            return diff

        return None

    def format_changes_for_notification(self, comparison_result: Dict) -> str:
        """
        Format the comparison result into a readable notification message.

        Args:
            comparison_result: Result from compare_bulletins()

        Returns:
            str: Formatted message suitable for SMS
        """
        if not comparison_result['has_changes']:
            return "No changes detected in China visa bulletin."

        lines = []
        lines.append("美国签证排期更新 (中国大陆)")
        lines.append("=" * 30)

        prev_bulletin = self._format_bulletin_month(comparison_result.get('previous_bulletin'))
        curr_bulletin = self._format_bulletin_month(comparison_result.get('current_bulletin'))
        lines.append(f"上期: {prev_bulletin} → 本期: {curr_bulletin}")
        lines.append("")

        # Group changes by table type
        final_action_changes = [c for c in comparison_result['changes'] if c['table_type'] == 'Final Action Dates']
        filing_changes = [c for c in comparison_result['changes'] if c['table_type'] == 'Filing Dates']

        if final_action_changes:
            lines.append("【最终裁定日期 Final Action】")
            for change in final_action_changes:
                line = self._format_single_change(change)
                lines.append(line)
            lines.append("")

        if filing_changes:
            lines.append("【递件日期 Filing Dates】")
            for change in filing_changes:
                line = self._format_single_change(change)
                lines.append(line)
            lines.append("")

        lines.append(f"检测时间: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")

        return "\n".join(lines)

    def _format_single_change(self, change: Dict) -> str:
        """Format a single change into a readable line"""
        category = change['category']
        old_date = self._format_priority_date(change['old_date'])
        new_date = self._format_priority_date(change['new_date'])
        status = change['status']
        days_diff = change.get('days_diff')

        # Status emoji/indicator with days
        if status == 'advanced':
            if days_diff:
                indicator = f"📈 前进 {days_diff}天"
            else:
                indicator = "📈 前进"
        elif status == 'retrogressed':
            if days_diff:
                indicator = f"📉 倒退 {abs(days_diff)}天"
            else:
                indicator = "📉 倒退"
        elif status == 'became_current':
            indicator = "✅ 有名额"
        elif status == 'became_unavailable':
            indicator = "❌ 无名额"
        elif status == 'retrogressed_from_current':
            indicator = "📉 从有名额变为排期"
        elif status == 'became_available':
            indicator = "📈 从无名额变为有排期"
        else:
            indicator = "🔄 变化"

        return f"  {category}: {old_date} → {new_date} ({indicator})"

    def _format_priority_date(self, date_str: str) -> str:
        """Convert raw priority date to yyyy/mm/dd when possible."""
        parsed = self._parse_priority_date(date_str)
        if parsed:
            return parsed.strftime("%Y/%m/%d")
        return date_str

    def _format_bulletin_month(self, bulletin_str: Optional[str]) -> str:
        """Format bulletin month (YYYY-MM) into yyyy/mm/dd (use first day)."""
        if not bulletin_str:
            return "Unknown"
        try:
            date_obj = datetime.strptime(bulletin_str, "%Y-%m")
            return date_obj.strftime("%Y/%m/%d")
        except ValueError:
            return bulletin_str
