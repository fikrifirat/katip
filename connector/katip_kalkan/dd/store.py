"""Local store: one SQLite file plus gzipped raw snapshots.

Lives in ``~/.katip/dd`` (override with ``KATIP_DD_HOME``). Nothing leaves the computer.
The lists contain real people's ID numbers and parents' names, so the store is never
committed and never synced.
"""
from __future__ import annotations

import gzip
import json
import os
import sqlite3
import time
from pathlib import Path


def home() -> Path:
    p = Path(os.environ.get("KATIP_DD_HOME", Path.home() / ".katip" / "dd"))
    p.mkdir(parents=True, exist_ok=True)
    return p


SCHEMA = """
create table if not exists records(
  source text, rid text, payload text, fetched_at text,
  primary key(source, rid));
create table if not exists runs(
  id integer primary key autoincrement, source text, started text, finished text,
  status text, n integer, added integer, removed integer, detail text);
"""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or home() / "dd.sqlite"
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)

    def replace_source(self, source: str, records: list[dict], detail: dict, started: str) -> dict:
        """Swap in a full snapshot for one source. Returns counts of added/removed rows."""
        old = {r for (r,) in self.db.execute("select rid from records where source=?", (source,))}
        new = {r["rid"] for r in records}
        ts = now()
        with self.db:
            self.db.execute("delete from records where source=?", (source,))
            self.db.executemany(
                "insert or replace into records values(?,?,?,?)",
                [(source, r["rid"], json.dumps(r, ensure_ascii=False), ts) for r in records],
            )
            stats = {"n": len(new), "added": len(new - old), "removed": len(old - new)}
            self.db.execute(
                "insert into runs(source,started,finished,status,n,added,removed,detail) values(?,?,?,?,?,?,?,?)",
                (source, started, ts, "ok", stats["n"], stats["added"], stats["removed"], json.dumps(detail, ensure_ascii=False)),
            )
        raw = home() / "raw" / source
        raw.mkdir(parents=True, exist_ok=True)
        with gzip.open(raw / f"{time.strftime('%Y%m%dT%H%M%S')}.json.gz", "wt", encoding="utf-8") as f:
            json.dump({"detail": detail, "records": records}, f, ensure_ascii=False)
        return stats

    def log_failure(self, source: str, started: str, status: str, detail: dict):
        with self.db:
            self.db.execute(
                "insert into runs(source,started,finished,status,n,added,removed,detail) values(?,?,?,?,0,0,0,?)",
                (source, started, now(), status, json.dumps(detail, ensure_ascii=False)),
            )

    def records(self, source: str | None = None) -> list[dict]:
        q, a = "select payload from records", ()
        if source:
            q, a = q + " where source=?", (source,)
        return [json.loads(p) for (p,) in self.db.execute(q, a)]

    def runs(self, limit: int = 20) -> list[dict]:
        cols = ["id", "source", "started", "finished", "status", "n", "added", "removed", "detail"]
        rows = self.db.execute("select * from runs order by id desc limit ?", (limit,)).fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def last_ok(self, source: str) -> dict | None:
        for r in self.runs(200):
            if r["source"] == source and r["status"] == "ok":
                return r
        return None
