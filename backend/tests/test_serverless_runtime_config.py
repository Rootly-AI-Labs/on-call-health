import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from app.models import base

BACKEND_DIR = Path(__file__).resolve().parents[1]


def run_python(script: str, **env_overrides) -> str:
    """Run in a fresh interpreter, since these settings are read at import time.

    An override of None removes the variable; .env files are not loaded.
    """
    env = {**os.environ, **env_overrides}
    env = {key: value for key, value in env.items() if value is not None}
    prelude = "import dotenv; dotenv.load_dotenv = lambda *args, **kwargs: False\n"
    result = subprocess.run([sys.executable, "-c", prelude + script], env=env, cwd=BACKEND_DIR,
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def test_connect_args_include_timeouts_by_default(monkeypatch):
    monkeypatch.setattr(base, "DB_STARTUP_OPTIONS", True)

    connect_args = base.build_connect_args()

    assert connect_args["application_name"] == base.APP_NAME
    assert f"-c statement_timeout={base.STATEMENT_TIMEOUT_MS}" in connect_args["options"]
    assert f"-c lock_timeout={base.LOCK_TIMEOUT_MS}" in connect_args["options"]
    assert f"-c idle_in_transaction_session_timeout={base.IDLE_IN_TX_TIMEOUT_MS}" in connect_args["options"]


def test_connect_args_skip_startup_options_for_poolers(monkeypatch):
    monkeypatch.setattr(base, "DB_STARTUP_OPTIONS", False)

    assert base.build_connect_args() == {"application_name": base.APP_NAME}


@pytest.mark.parametrize("value,expected", [(None, "True"), ("true", "True"), ("false", "False")])
def test_startup_options_flag_reads_env(value, expected):
    script = "from app.models.base import DB_STARTUP_OPTIONS; print(DB_STARTUP_OPTIONS)"

    assert run_python(script, DB_STARTUP_OPTIONS=value) == expected


@pytest.mark.parametrize("db,expected", [
    (None, "redis://cache.example:6379/1"),
    ("0", "redis://cache.example:6379/0"),
])
def test_rate_limit_redis_database_is_configurable(db, expected):
    # Importing rate_limiting probes Redis; keep the child offline.
    script = (
        "import redis\n"
        "def offline(*args, **kwargs):\n    raise ConnectionError('offline')\n"
        "redis.from_url = offline\n"
        "from app.core.rate_limiting import get_redis_storage_uri; print(get_redis_storage_uri())"
    )

    assert run_python(script, REDIS_URL="redis://cache.example:6379/5", RATE_LIMIT_REDIS_DB=db) == expected


def test_collector_caches_live_in_the_temp_directory():
    from app.services.github_collector import GitHubCollector
    from app.services.slack_collector import SlackCollector

    temp_dir = Path(tempfile.gettempdir())

    assert GitHubCollector().cache_dir == temp_dir / ".github_cache"
    assert SlackCollector().cache_dir == temp_dir / ".slack_cache"
