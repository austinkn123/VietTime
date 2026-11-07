"""Conversation history in SQLite. Text only: Austin's recordings are never kept."""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_key TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
);
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL CHECK (role IN ('learner', 'tutor')),
    text TEXT NOT NULL,
    corrections TEXT NOT NULL DEFAULT '[]',
    new_words TEXT NOT NULL DEFAULT '[]',
    timings TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS turns_by_session ON turns(session_id, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path | str):
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(_SCHEMA)

    def create_session(self, persona_key: str) -> dict:
        with self._lock, self._db:
            cur = self._db.execute("INSERT INTO sessions (persona_key, started_at) VALUES (?, ?)", (persona_key, _now()))
        return self.get_session(cur.lastrowid)

    def get_session(self, session_id: int) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT s.*, (SELECT COUNT(*) FROM turns t WHERE t.session_id = s.id) AS turn_count FROM sessions s WHERE s.id = ?",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_sessions(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT s.*, (SELECT COUNT(*) FROM turns t WHERE t.session_id = s.id) AS turn_count"
                " FROM sessions s ORDER BY s.id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def last_persona(self) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT persona_key FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
        return row["persona_key"] if row else None

    def end_session(self, session_id: int) -> None:
        with self._lock, self._db:
            self._db.execute("UPDATE sessions SET ended_at = COALESCE(ended_at, ?) WHERE id = ?", (_now(), session_id))

    def add_turn(self, session_id: int, role: str, text: str, corrections=None, new_words=None, timings=None) -> dict:
        row = {
            "session_id": session_id,
            "role": role,
            "text": text,
            "corrections": corrections or [],
            "new_words": new_words or [],
            "timings": timings or {},
            "created_at": _now(),
        }
        with self._lock, self._db:
            cur = self._db.execute(
                "INSERT INTO turns (session_id, role, text, corrections, new_words, timings, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    role,
                    text,
                    json.dumps(row["corrections"], ensure_ascii=False),
                    json.dumps(row["new_words"], ensure_ascii=False),
                    json.dumps(row["timings"]),
                    row["created_at"],
                ),
            )
        return {"id": cur.lastrowid, **row}

    def turns(self, session_id: int) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM turns WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            for key in ("corrections", "new_words", "timings"):
                d[key] = json.loads(d[key])
            out.append(d)
        return out

    def close(self) -> None:
        with self._lock:
            self._db.close()
