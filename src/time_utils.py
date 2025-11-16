"""Helper utilities for working with the project's timezone."""

from datetime import datetime
from functools import lru_cache

import pytz
from pytz.tzinfo import BaseTzInfo

import config


@lru_cache(maxsize=1)
def get_project_timezone() -> BaseTzInfo:
    """Return the pytz timezone instance configured for the project."""
    return pytz.timezone(config.TIMEZONE)


def now_in_project_timezone() -> datetime:
    """Get the current datetime localized to the project timezone."""
    return datetime.now(get_project_timezone())
