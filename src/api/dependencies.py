from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from functools import lru_cache

from src.agent.decision import DecisionEngine, build_decision_engine
from src.agent.retrieval import Retriever, build_retriever
from src.db.repository import Repository, connect

DB_PATH_ENV = "APP_DB_PATH"
DEFAULT_DB_PATH = "./support_agent.db"


def get_db_path() -> str:
    return os.environ.get(DB_PATH_ENV) or DEFAULT_DB_PATH


def open_connection() -> sqlite3.Connection:
    return connect(get_db_path())


def get_repository() -> Iterator[Repository]:
    connection = open_connection()
    try:
        yield Repository(connection)
    finally:
        connection.close()


@lru_cache(maxsize=1)
def _retriever_singleton() -> Retriever:
    return build_retriever()


@lru_cache(maxsize=1)
def _decision_engine_singleton() -> DecisionEngine:
    return build_decision_engine()


def get_retriever() -> Retriever:
    return _retriever_singleton()


def get_decision_engine() -> DecisionEngine:
    return _decision_engine_singleton()
