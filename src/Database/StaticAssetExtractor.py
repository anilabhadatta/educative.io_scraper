"""
StaticAssetExtractor.py

Scans all stored component JSON in the database, extracts static /api/ URLs,
and stores them in the static_assets table keyed by (course_id, topic_index).

URL extraction rules
--------------------
  type == "File"
      URL is *constructed* (not scanned) as:
          /api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}/{file_name}
      where:
          author_id / collection_id  – from the courses row
          page_id                    – read from the topics.page_id column
          image_id / file_name       – from content_json

  type == "ButtonLink"
      URL is read from content.url and normalized. Relative paths such as
          /api/cheatsheet/.../download
      are converted to absolute https://www.educative.io/... URLs.

  all other types
      The raw content_json string is scanned with a regex for static /api/
      path fragments. All unique matches are collected for that component.

Output table: static_assets
-----------------------------
  course_id   INTEGER  FK -> courses(id)
  topic_index INTEGER
  assets_json TEXT     JSON object: { "<component_index>": ["url", ...], ... }
                       One row per (course_id, topic_index).

Usage
-----
  # explicit db path
  python -m src.Database.StaticAssetExtractor path/to/educative_scraper.db

  # auto-discover (looks beside downloaded_files/ in the project root)
  python -m src.Database.StaticAssetExtractor
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Captures static /api/collection/... or /api/cheatsheet/... paths, stopping at
# ?, quote, whitespace, brace, or backslash.
# Stopping at ? means query parameters are never included in the match.
_API_RE = re.compile(r'/api/(?:collection|cheatsheet)/[^\s"\' <>{}\\?\]]+')


# ── Helpers ──────────────────────────────────────────────────────────────── #

def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _urls_for_file(content: dict, author_id: str, collection_id: str, page_id: str) -> list:
    """Construct the download URL for a File component."""
    image_id  = content.get("image_id")
    file_name = content.get("file_name") or ""
    if not image_id:
        return []
    return [f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}/{file_name}"]


def _urls_for_image(content: dict, author_id: str, collection_id: str, page_id: str) -> list:
    """Construct the image URL for an Image component (id only, no filename)."""
    image_id = content.get("image_id")
    if not image_id:
        return []
    return [f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}"]


def _urls_from_scan(content_json_str: str) -> list:
    """Return all unique https://educative.io/api/collection/... URLs found in the raw JSON string."""
    matches = _API_RE.findall(content_json_str)
    seen, result = set(), []
    for path in matches:
        url = path
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


# ── Main extraction logic ─────────────────────────────────────────────────── #

def extract_and_store(db_path: str):
    conn = _connect(db_path)
    try:
        # Ensure the static_assets table exists (idempotent)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS static_assets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                topic_index INTEGER NOT NULL,
                assets_json TEXT    NOT NULL DEFAULT '{}',
                created_at  TEXT    NOT NULL,
                UNIQUE(course_id, topic_index)
            );
            CREATE INDEX IF NOT EXISTS idx_static_assets_course ON static_assets(course_id);
        """)
        conn.commit()

        # ── Build lookup tables ──────────────────────────────────────────── #

        # course_id -> (author_id, collection_id)
        courses = {
            row["id"]: (row["author_id"] or "", row["collection_id"] or "")
            for row in conn.execute(
                "SELECT id, author_id, collection_id FROM courses"
            ).fetchall()
        }

        # (course_id, topic_index) -> page_id  (stored directly in topics row)
        topic_page_ids = {
            (row["course_id"], row["topic_index"]): row["page_id"]
            for row in conn.execute(
                "SELECT course_id, topic_index, page_id FROM topics"
            ).fetchall()
        }

        # ── Iterate every (course_id, topic_index) that has components ───── #

        pairs = conn.execute(
            "SELECT DISTINCT course_id, topic_index FROM components ORDER BY course_id, topic_index"
        ).fetchall()

        now = datetime.utcnow().isoformat()
        stored = 0
        skipped = 0

        for pair in pairs:
            course_id   = pair["course_id"]
            topic_index = pair["topic_index"]

            author_id, collection_id = courses.get(course_id, ("", ""))
            page_id = topic_page_ids.get((course_id, topic_index), "")

            components = conn.execute(
                """
                SELECT component_index, type, content_json
                FROM   components
                WHERE  course_id = ? AND topic_index = ?
                ORDER  BY component_index
                """,
                (course_id, topic_index),
            ).fetchall()

            # { "<component_index>": ["url", ...] }
            assets: dict = {}

            for comp in components:
                comp_idx    = comp["component_index"]
                comp_type   = comp["type"]
                content_str = comp["content_json"] or "{}"

                try:
                    content = json.loads(content_str)
                except json.JSONDecodeError:
                    content = {}

                if comp_type == "File":
                    urls = _urls_for_file(content, author_id, collection_id, page_id)
                elif comp_type == "Image":
                    urls = _urls_for_image(content, author_id, collection_id, page_id)
                else:
                    urls = _urls_from_scan(content_str)

                if urls:
                    assets[str(comp_idx)] = urls

            if not assets:
                skipped += 1
                continue

            conn.execute(
                """
                INSERT INTO static_assets (course_id, topic_index, assets_json, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(course_id, topic_index) DO UPDATE SET
                    assets_json = excluded.assets_json,
                    created_at  = excluded.created_at
                """,
                (course_id, topic_index, json.dumps(assets, ensure_ascii=False), now),
            )
            stored += 1

        conn.commit()
        print(f"Done. Stored: {stored} topic row(s), skipped: {skipped} (no /api/ URLs found).")

    finally:
        conn.close()


# ── Entry point ───────────────────────────────────────────────────────────── #

def _resolve_db_path() -> str:
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if not p.exists():
            raise SystemExit(f"Error: database not found at '{p}'")
        return str(p)

    # Auto-discover: look in project_root/downloaded_files/
    default = Path(__file__).resolve().parent.parent.parent / "downloaded_files" / "educative_scraper.db"
    if default.exists():
        return str(default)

    raise SystemExit(
        "Usage: python -m src.Database.StaticAssetExtractor <path/to/educative_scraper.db>\n"
        f"Auto-discover path '{default}' also not found."
    )


if __name__ == "__main__":
    db = _resolve_db_path()
    print(f"Database: {db}")
    extract_and_store(db)
