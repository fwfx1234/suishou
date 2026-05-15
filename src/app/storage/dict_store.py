from __future__ import annotations

from collections.abc import Iterator
import json
from threading import RLock
from typing import Any

from .sqlite import SQLiteDatabase


_MISSING = object()


class DatabaseDictStore:
    def __init__(
        self,
        database: SQLiteDatabase,
        namespace: str,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        self.database = database
        self.namespace = namespace
        self.path = self.database.path
        self._lock = RLock()
        self._ensure_schema()
        self._loaded_from_existing_store = self._has_rows()
        if defaults:
            self.setdefault_many(defaults)

    @property
    def loaded_from_existing_store(self) -> bool:
        return self._loaded_from_existing_store

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            value = self._get_raw(key)
            if value is _MISSING:
                return default
            return _loads_value(value, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._set_rows({key: value})

    def set_many(self, values: dict[str, Any]) -> None:
        with self._lock:
            self._set_rows(values)

    def setdefault_many(self, values: dict[str, Any]) -> None:
        with self._lock:
            existing = set(self.keys())
            missing = {str(key): value for key, value in values.items() if str(key) not in existing}
            if missing:
                self._set_rows(missing)

    def delete(self, key: str) -> None:
        with self._lock:
            with self.database.connection() as conn:
                conn.execute(
                    "DELETE FROM dict_store WHERE namespace = ? AND key = ?",
                    (self.namespace, key),
                )

    def clear(self) -> None:
        with self._lock:
            with self.database.connection() as conn:
                conn.execute("DELETE FROM dict_store WHERE namespace = ?", (self.namespace,))

    def replace(self, values: dict[str, Any]) -> None:
        with self._lock:
            rows = [(self.namespace, str(key), _dumps_value(value)) for key, value in values.items()]
            with self.database.connection() as conn:
                conn.execute("DELETE FROM dict_store WHERE namespace = ?", (self.namespace,))
                conn.executemany(
                    """
                    INSERT INTO dict_store (namespace, key, value_json, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    rows,
                )

    def all(self) -> dict[str, Any]:
        with self._lock:
            with self.database.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT key, value_json
                    FROM dict_store
                    WHERE namespace = ?
                    ORDER BY key
                    """,
                    (self.namespace,),
                ).fetchall()
            data: dict[str, Any] = {}
            for key, value_json in rows:
                value = _loads_value(value_json, _MISSING)
                if value is not _MISSING:
                    data[str(key)] = value
            return data

    def keys(self) -> list[str]:
        with self._lock:
            with self.database.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT key
                    FROM dict_store
                    WHERE namespace = ?
                    ORDER BY key
                    """,
                    (self.namespace,),
                ).fetchall()
            return [str(row[0]) for row in rows]

    def items(self) -> list[tuple[str, Any]]:
        with self._lock:
            return list(self.all().items())

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        with self._lock:
            return self._get_raw(key) is not _MISSING

    def __getitem__(self, key: str) -> Any:
        with self._lock:
            value = self._get_raw(key)
            if value is _MISSING:
                raise KeyError(key)
            return _loads_value(value)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(self.keys())

    def __len__(self) -> int:
        with self._lock:
            with self.database.connection() as conn:
                return int(
                    conn.execute(
                        "SELECT COUNT(*) FROM dict_store WHERE namespace = ?",
                        (self.namespace,),
                    ).fetchone()[0]
                )

    def _ensure_schema(self) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dict_store (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (namespace, key)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_dict_store_namespace
                ON dict_store(namespace)
                """
            )

    def _has_rows(self) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM dict_store WHERE namespace = ? LIMIT 1",
                (self.namespace,),
            ).fetchone()
        return row is not None

    def _get_raw(self, key: str) -> str | object:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT value_json
                FROM dict_store
                WHERE namespace = ? AND key = ?
                """,
                (self.namespace, key),
            ).fetchone()
        return _MISSING if row is None else str(row[0])

    def _set_rows(self, values: dict[str, Any]) -> None:
        rows = [(self.namespace, str(key), _dumps_value(value)) for key, value in values.items()]
        with self.database.connection() as conn:
            conn.executemany(
                """
                INSERT INTO dict_store (namespace, key, value_json, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                rows,
            )


def _dumps_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _loads_value(value: str | object, default: Any = None) -> Any:
    if not isinstance(value, str):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
