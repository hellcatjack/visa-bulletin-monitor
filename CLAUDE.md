# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

US Visa Bulletin Monitor for China - A Python application that automatically monitors the US Department of State's Visa Bulletin for China mainland employment-based visa priority dates and sends notifications when changes are detected.

## Key Commands

### Development & Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Test notification system
python main.py --mode test

# Run single scrape (manual testing)
python main.py --mode once

# Check current status
python main.py --mode status

# Start scheduled monitoring
python main.py --mode schedule
```

### Configuration
Before running, copy `.env.example` to `.env` and configure:
- Email notification (default): Set SMTP credentials (Gmail requires app-specific password)
- SMS notification: Set Twilio credentials (alternative)

## Architecture

### High-Level Flow
1. **Scheduler** (`scheduler.py`) → triggers scrape every 15 minutes during US Eastern business hours (Mon-Fri, 9 AM - 11 PM)
2. **Orchestrator** (`orchestrator.py`) → coordinates the scrape cycle:
   - Checks monthly scrape status (prevents duplicate notifications)
   - Scrapes latest bulletin
   - Parses China-specific data
   - Compares with previous bulletin
   - Sends notification if changes detected
   - Updates storage
3. **Storage** (`storage.py`) → manages state and history in JSON files

### Core Components

**Scraper** (`src/scraper.py`):
- Fetches US Visa Bulletin main page
- Locates upcoming/current bulletin link (prioritizes upcoming month)
- Downloads bulletin HTML content
- Returns tuple: `(bulletin_url, html_content)`

**Parser** (`src/parser.py`):
- Extracts bulletin date from title/headers
- Locates employment-based visa tables by searching for specific heading text:
  - "FINAL ACTION DATES FOR EMPLOYMENT-BASED"
  - "DATES FOR FILING OF EMPLOYMENT-BASED VISA APPLICATIONS"
- Parses HTML tables into 2D arrays
- Identifies China column (searches for: 'china', 'mainland', 'prc', 'mainland born')
- Maps table rows to visa categories (EB-1, EB-2, EB-3, etc.)
- Returns structured data with both Final Action and Filing dates

**Comparator** (`src/comparator.py`):
- Compares two bulletin dictionaries
- Detects changes in priority dates (forward movement, backward movement, availability changes)
- Formats changes into human-readable Chinese notification messages
- Handles special cases: "C" (Current/available), date movements

**Notifiers**:
- `notifier.py` - SMS via Twilio
- `email_notifier.py` - Email via SMTP (supports HTML formatting)
- Selected based on `NOTIFICATION_METHOD` in config

**Storage** (`src/storage.py`):
- `visa_bulletin_history.json` - Array of all scraped bulletins with timestamps
- `scraper_state.json` - Tracks last scrape time, last bulletin month, monthly completion flag
- Monthly management: Prevents re-scraping same month's bulletin multiple times

### Configuration System

`config.py` loads from `.env` file:
- `NOTIFICATION_METHOD` - 'email' or 'sms'
- Email: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO
- SMS: Twilio credentials and phone numbers
- Scheduling: SCRAPE_INTERVAL_MINUTES (15), TIMEZONE ('America/New_York')

### Data Flow Example

```
Main page → Find upcoming bulletin link → Download HTML
    ↓
Parse tables → Extract China dates → Structure as dict
    ↓
Load previous bulletin from JSON → Compare
    ↓
If changes detected → Format message → Send via email/SMS
    ↓
Save new bulletin to history → Update state
```

### Monthly Scrape Logic

The application implements monthly deduplication:
- When a bulletin is successfully scraped, `monthly_scrape_completed` flag is set with that month
- Subsequent runs check if current bulletin month matches last completed month
- If match, skip scraping until next month
- This prevents spam notifications for the same bulletin

### Important Parsing Notes

- The parser is resilient to HTML structure changes by searching for text patterns rather than fixed CSS selectors
- China column identification uses multiple keywords to handle variations in table headers
- Visa category mapping handles both numeric ("1st", "2nd") and category code formats ("EB-1", "EB-2")
- Special handling for EB-5 subcategories (Unreserved, Rural, High Unemployment, Infrastructure)
- Date format: "01JAN2020" or "C" (Current/available)

### Ubuntu Deployment

For production deployment on Ubuntu 24.04 Server:
- Virtual environment: `.venv` (created with `python3 -m venv .venv`)
- Default installation path: `/opt/visa-bulletin-monitor`
- Systemd service: `visa-monitor.service`
- Service runs as dedicated user: `visa-monitor`
- Refer to `UBUNTU_DEPLOYMENT.md` for complete setup instructions

### Testing Strategy

When modifying parsing logic:
1. Use `--mode once` to test single scrape without affecting schedule
2. Use `--mode status` to verify state management
3. Check logs at `logs/visa_scraper.log` for detailed parsing output
4. Inspect `data/visa_bulletin_history.json` to verify extracted data structure
5. Use `--mode test` to verify notification delivery
