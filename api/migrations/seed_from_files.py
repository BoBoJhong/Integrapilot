"""Seed database metadata from existing files."""

from __future__ import annotations

import json
from pathlib import Path

from api import db
from api import helpers as h
from api.config import AGENTS_FILE, REPORTS_DIR


def seed_agents() -> int:
    seeded = 0
    now = h.now_taipei()
    defaults = h.default_agents()
    db.upsert_default_agent(now, defaults[0])
    if not AGENTS_FILE.exists():
        return 1
    try:
        raw = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return 1
    if not isinstance(raw, list):
        return 1
    for item in raw:
        if not isinstance(item, dict):
            continue
        if item.get("id") == "integration-advisor":
            continue
        name = str(item.get("name") or "").strip()
        role = str(item.get("role") or "").strip()
        goal = str(item.get("goal") or "").strip()
        backstory = str(item.get("backstory") or "").strip()
        if not name or not role or not goal or not backstory:
            continue
        db.create_agent(name, role, goal, backstory, str(item.get("model") or ""), now)
        seeded += 1
    return seeded + 1


def seed_reports() -> int:
    seeded = 0
    for p in sorted(REPORTS_DIR.glob("*.md")):
        stat = p.stat()
        now = h.now_taipei()
        db.upsert_report(
            report_id=p.name,
            report_name=p.name,
            file_path=str(p.resolve()),
            project_a_path="",
            project_b_path="",
            input_mode="legacy_unknown",
            size_bytes=stat.st_size,
            now=now,
        )
        seeded += 1
    return seeded


def main() -> None:
    db.run_migrations()
    agents = seed_agents()
    reports = seed_reports()
    print(f"seeded agents={agents}, reports={reports}")


if __name__ == "__main__":
    main()
