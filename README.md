# US Visa Bulletin Monitor (Mainland China Focus)

[查看简体中文文档 / Read this guide in Chinese](README.zh-CN.md)

Monitor U.S. Department of State visa bulletin updates for Mainland China employment-based categories. The tool scrapes, parses, compares, and notifies you via email or SMS whenever a new bulletin shifts the cut-off dates.

## Features

- Automatically scrapes the latest Visa Bulletin
- Extracts Mainland China employment-based (EB) dates
- Compares with the previous month and highlights every change
- Formats bilingual notifications (Chinese + English) for readability
- **Notification methods**:
  - **Email (default, recommended)** – works with Gmail, Outlook, QQ Mail, 163 Mail, etc.
  - **SMS** – dispatched through Twilio
- Smart scheduling: every 15 minutes on U.S. Eastern business days (Mon–Fri, 9 AM–11 PM) with retry backoff and automatic monthly reset
- Monthly lifecycle: once a month’s bulletin is captured successfully the scheduler pauses until the next cycle
- JSON history for quick auditing and backup

## Documentation

- **README.md** – project overview and usage (this file)
- **QUICKSTART.md** – 5-minute setup guide
- **UBUNTU_DEPLOYMENT.md** – Ubuntu 24.04 Server deployment guide
- **CLAUDE.md** – architecture and development guidance for AI assistants
- **GMAIL_SETUP.md** – Gmail SMTP walkthrough
- **README.zh-CN.md** – 完整中文介绍、安装与使用指南

## Project Structure

```
visa-bulletin-monitor/
├── main.py                 # Application entry point
├── config.py               # Centralized configuration
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create locally)
├── .env.example            # Example environment file
├── README.md               # Documentation (this file)
├── src/                    # Source modules
│   ├── scraper.py          # HTML fetching
│   ├── parser.py           # DOM parsing
│   ├── comparator.py       # Month-over-month diff logic
│   ├── notifier.py         # SMS helper
│   ├── email_notifier.py   # Email helper
│   ├── storage.py          # JSON persistence
│   ├── scheduler.py        # APScheduler jobs
│   ├── orchestrator.py     # Workflow coordinator
│   └── logger.py           # Logging setup
├── data/                   # Persistent JSON data
│   ├── visa_bulletin_history.json
│   └── scraper_state.json
└── logs/                   # Runtime logs
    └── visa_scraper.log
```

## Installation

### 1. Install Python

Use Python 3.8 or newer:

```bash
python --version
```

### 2. Clone the repository

```bash
git clone https://github.com/hellcatjack/visa-bulletin-monitor.git
cd visa-bulletin-monitor
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Choose a notification method

Email is enabled by default, but Twilio SMS is also supported.

#### Option 1: Email (recommended)

See [GMAIL_SETUP.md](GMAIL_SETUP.md) for Gmail-specific steps:

1. Enable 2FA for Gmail
2. Generate an App Password
3. Fill the SMTP credentials inside `.env`

Other providers:
- QQ Mail – requires auth code, SMTP `smtp.qq.com:587`
- 163 Mail – requires auth code, SMTP `smtp.163.com:465`
- Outlook – use account password, SMTP `smtp-mail.outlook.com:587`

#### Option 2: SMS via Twilio

1. Sign up at https://www.twilio.com/try-twilio
2. Create a phone number and copy the Account SID/Auth Token
3. Set `NOTIFICATION_METHOD=sms` in `.env`

### 5. Create the environment file

```bash
cp .env.example .env
```

Fill in one of the following templates:

**Email notification (default):**

```env
NOTIFICATION_METHOD=email

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

**SMS notification:**

```env
NOTIFICATION_METHOD=sms

TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
TWILIO_TO_NUMBER=+8613800138000
```

## Usage

### Test notifications

```bash
python main.py --mode test
```

- Email mode sends a sample HTML email
- SMS mode uses Twilio to send a placeholder text

### Check current status

```bash
python main.py --mode status
```

### Run a single scrape

```bash
python main.py --mode once
```

### Start the scheduler (recommended)

```bash
python main.py --mode schedule
```

The scheduler runs:
- Monday–Friday (U.S. Eastern Time)
- 09:00–23:00
- Every 15 minutes with graceful backoff

Stop with `Ctrl+C` when running in the foreground.

## Modes

| Mode      | Description              | When to use                  |
|-----------|--------------------------|------------------------------|
| `test`    | Sends a test notification| Validate Email/SMS configs   |
| `status`  | Shows persisted state    | Inspect last run             |
| `once`    | Single scrape/parse run  | Manual regression tests      |
| `schedule`| Continuous monitoring    | Production deployment        |

## Logging

- Log path: `logs/visa_scraper.log`
- Level: configure via `LOG_LEVEL` in `.env` (DEBUG/INFO/WARNING/ERROR)
- Rotation: 10 MB per file, last 5 rotations retained

## Data Files

### visa_bulletin_history.json

```json
[
  {
    "bulletin_date": "2024-11",
    "scrape_timestamp": "2024-10-15T10:30:00",
    "final_action_dates": {
      "EB-1": "C",
      "EB-2": "01JAN2020",
      "EB-3": "15JUN2018"
    },
    "filing_dates": {
      "EB-1": "C",
      "EB-2": "01FEB2020",
      "EB-3": "01JUL2018"
    }
  }
]
```

### scraper_state.json

```json
{
  "last_successful_scrape": "2024-10-15T10:30:00",
  "last_bulletin_month": "2024-11",
  "monthly_scrape_completed": true
}
```

## Notification Templates

### Email

Rich HTML emails include bilingual headings, color-coded sections, table layouts, and emoji cues to emphasize retrogression/advancement.

### SMS / Plain Text

```
US Visa Bulletin Update (China Mainland)
========================================
Previous: 2024/10/01 → Current: 2024/11/01

Final Action Dates
  EB-2: 2020/01/01 → 2020/02/15 (📈 Forward)
  EB-3: 2018/06/15 → 2018/06/01 (📉 Retrogress)

Filing Dates
  EB-2: 2020/02/01 → C (✅ Current)

Checked at: 2024/10/15 10:30:00
```

## FAQ

1. **How do I keep it running on Windows?**  
   Create a `start.bat` that launches `python main.py --mode schedule`, or wire it into Task Scheduler (trigger on startup, run `python.exe` with arguments `main.py --mode schedule` from the project folder).

2. **No notification received?**  
   Run `python main.py --mode test`, inspect `logs/visa_scraper.log`, verify spam folders, App Passwords, SMTP host/port, Twilio balance, and ensure international numbers include the `+` country code.

3. **Where is the historical record?**  
   Check `data/visa_bulletin_history.json` for the month-by-month snapshots.

4. **How many alerts per month?**  
   Usually 0–2. If a bulletin publishes changes you will get one consolidated notification. Once the month is captured the scheduler pauses until the next cycle.

5. **Can I send both email and SMS at once?**  
   Not yet. Run two instances with separate `.env` files or extend the notifier layer to broadcast to multiple channels.

6. **Why prefer email?**  
   Email is free/cheap, supports HTML, keeps history, and is not bound by international SMS rules. SMS is better for real-time phone alerts but incurs Twilio costs.

## Tech Stack

- **Python 3.8+**
- **requests** – HTTP client
- **BeautifulSoup4** – HTML parsing
- **smtplib/email** – SMTP email sending
- **Twilio** – SMS delivery
- **APScheduler** – scheduling
- **pytz** – timezone utilities

## License

MIT License

## Contributing

Issues and pull requests are welcome—please describe the scenario, test mode(s) used, and attach sanitized logs if behavior changes.

## Support

Open an issue if you run into problems or have enhancement ideas.
