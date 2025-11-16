# Repository Guidelines

## Project Structure & Module Organization
`main.py` orchestrates the monitoring workflow and delegates into `src/orchestrator.py`. Each module under `src/` owns a single responsibility (scraping, parsing, comparison, notifications, scheduling, logging); keep new helpers colocated with the feature they extend. Persistent JSON state (`data/visa_bulletin_history.json`, `data/scraper_state.json`) must stay backward compatible because systemd deployments reuse these files between releases.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate` (or `.venv\\Scripts\\activate`) creates an isolated interpreter.
- `pip install -r requirements.txt` installs BeautifulSoup, Requests, Twilio, and SMTP dependencies.
- `python main.py --mode test` sends placeholder email/SMS to validate credentials.
- `python main.py --mode once` runs a single scrape/parse/notify cycle for regression checks.
- `python main.py --mode schedule` launches the scheduler (15-minute cadence, US/Eastern business hours).
- `python test_scraper.py` dumps detailed DOM findings from `VisaBulletinScraper` when upstream HTML changes.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, `snake_case` symbols, `CapWords` classes, and module-level loggers created via `logging.getLogger(__name__)`. Type hints and short docstrings are required for public functions to keep `src/` self-documented. Shared constants or regexes belong in `config.py` to avoid duplicate environment reads.

## Testing Guidelines
There is no pytest suite yet, so lean on executable flows. Run `python test_scraper.py` after modifying HTML parsing or request headers. For orchestration, comparison, or notification updates run `python main.py --mode once` and inspect `logs/visa_scraper.log` plus diffs inside `data/visa_bulletin_history.json`. Changes to notifier templates require another `--mode test` per channel to confirm formatting before merging.

## Commit & Pull Request Guidelines
Commits in this repo use concise, imperative subjects (“Add intelligent scheduler…”, “Fix Ubuntu deployment…”). Keep each change focused, explaining config or deployment impacts in the body when relevant. Pull requests should summarize the scenario, list the modes exercised, link related docs (README, QUICKSTART, UBUNTU_DEPLOYMENT), and attach sanitized log excerpts or notification screenshots if behavior changed.

## Configuration & Security Tips
Secrets stay in `.env`, loaded centrally by `config.py`; share reproducible instructions by referencing `.env.example` keys instead of real values. Review `visa-monitor.service` whenever filesystem paths change so the service user still owns `data/` and `logs/`. Rotate SMTP or Twilio credentials immediately if they appear in logs, and avoid checking generated files outside `data/` and `logs/` into version control.
