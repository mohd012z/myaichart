"""Research-only agent skills and persistent evidence memory for myaichart."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import sqlite3

SKILLS = frozenset({"macro", "news", "market", "bbma", "supply_demand", "elliott", "critic"})

@dataclass(frozen=True)
class ResearchEvidence:
    event_id: str
    skill: str
    summary: str
    source_url: str
    published_at: str
    observed_at: str
    evidence_status: str = "unverified"

def validate(item: ResearchEvidence) -> None:
    if item.skill not in SKILLS or not 6 <= len(item.event_id) <= 120:
        raise ValueError("invalid skill or event id")
    if not 20 <= len(item.summary) <= 4000:
        raise ValueError("invalid summary")
    parsed = urlparse(item.source_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("invalid source URL")
    for value in (item.published_at, item.observed_at):
        parsed_date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed_date.tzinfo is None:
            raise ValueError("timezone required")
    if item.evidence_status not in ("unverified", "reviewed", "confirmed", "rejected"):
        raise ValueError("invalid evidence status")

class ResearchMemory:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS evidence(
                event_id TEXT PRIMARY KEY, skill TEXT NOT NULL, summary TEXT NOT NULL,
                source_url TEXT NOT NULL, published_at TEXT NOT NULL,
                observed_at TEXT NOT NULL, evidence_status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("CREATE INDEX IF NOT EXISTS evidence_skill_status ON evidence(skill,evidence_status)")
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        return db
    def ingest(self, item: ResearchEvidence) -> bool:
        validate(item)
        with self._connect() as db:
            cursor = db.execute("""INSERT OR IGNORE INTO evidence(event_id,skill,summary,source_url,published_at,observed_at,evidence_status)
                VALUES(?,?,?,?,?,?,'unverified')""", (item.event_id,item.skill,item.summary,item.source_url,item.published_at,item.observed_at))
            return cursor.rowcount == 1
    def retrieve(self, skill: str | None = None, limit: int = 20) -> list[dict]:
        if skill is not None and skill not in SKILLS:
            raise ValueError("invalid skill")
        limit = max(1, min(100, int(limit)))
        sql = "SELECT event_id,skill,summary,source_url,published_at,observed_at,evidence_status FROM evidence WHERE evidence_status='confirmed'"
        params = []
        if skill:
            sql += " AND skill=?"
            params.append(skill)
        sql += " ORDER BY observed_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute(sql, params)]
    def review_summary(self) -> dict:
        with self._connect() as db:
            counts = dict(db.execute("SELECT evidence_status,COUNT(*) FROM evidence GROUP BY evidence_status").fetchall())
        return {"counts":counts,"publish":False,"trade":False,"prediction":"not-calibrated"}
