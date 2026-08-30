from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.api.main import _load_local_env

_VAR = "FOO_TEST_VAR"


@pytest.fixture
def clean_var() -> Iterator[None]:
    os.environ.pop(_VAR, None)
    try:
        yield
    finally:
        os.environ.pop(_VAR, None)


def test_load_local_env_reads_variables_from_env_file(
    tmp_path: Path, clean_var: None
) -> None:
    (tmp_path / ".env").write_text(f"{_VAR}=bar\n", encoding="utf-8")

    _load_local_env(tmp_path / ".env")

    assert os.environ[_VAR] == "bar"


def test_load_local_env_does_not_override_exported_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_VAR, "original")
    (tmp_path / ".env").write_text(f"{_VAR}=fromfile\n", encoding="utf-8")

    _load_local_env(tmp_path / ".env")

    assert os.environ[_VAR] == "original"


def test_load_local_env_is_a_no_op_when_file_is_missing(
    tmp_path: Path, clean_var: None
) -> None:
    _load_local_env(tmp_path / "missing.env")

    assert _VAR not in os.environ


def test_default_env_file_points_at_the_repo_root() -> None:
    from src.api.main import _ENV_FILE

    # A wrong parents[N] would still be a valid Path and load_dotenv would
    # silently no-op; anchor it to markers that only exist at the repo root.
    assert _ENV_FILE.name == ".env"
    assert (_ENV_FILE.parent / "pyproject.toml").is_file()
    assert (_ENV_FILE.parent / "kb").is_dir()
