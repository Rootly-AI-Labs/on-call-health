import asyncio
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from app import main

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "run_migrations,run_schedulers",
    [(True, True), (False, False), (True, False), (False, True)],
)
def test_startup_runs_only_enabled_work(monkeypatch, run_migrations, run_schedulers):
    monkeypatch.setattr(main.settings, "RUN_MIGRATIONS_ON_STARTUP", run_migrations)
    monkeypatch.setattr(main.settings, "RUN_SCHEDULERS", run_schedulers)

    with patch.object(main, "run_startup_migrations") as migrations, patch.object(main, "start_schedulers") as schedulers:
        asyncio.run(main.startup_event())

    assert migrations.called is run_migrations
    assert schedulers.called is run_schedulers


def test_startup_work_is_enabled_by_default():
    env = {key: value for key, value in os.environ.items() if key not in ("RUN_MIGRATIONS_ON_STARTUP", "RUN_SCHEDULERS")}
    script = "from app.core.config import settings; print(settings.RUN_MIGRATIONS_ON_STARTUP, settings.RUN_SCHEDULERS)"

    result = subprocess.run([sys.executable, "-c", script], env=env, cwd=BACKEND_DIR, capture_output=True, text=True, check=True)

    assert result.stdout.split() == ["True", "True"]
