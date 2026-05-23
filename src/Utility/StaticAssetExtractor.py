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
    python -m src.Utility.StaticAssetExtractor path/to/educative_scraper.db

  # auto-discover (looks beside downloaded_files/ in the project root)
    python -m src.Utility.StaticAssetExtractor
"""

import json
import sqlite3
import sys
import configparser
from datetime import datetime
from pathlib import Path
import urllib.parse
import re

from src.Common.Constants import constants
from src.ScraperType.ApiScraper.APIScraperConstants import ASSET_SCAN_API_PATH_REGEX, UDATA_SCAN_REGEX

# D2Diagram GCS base — files are stored at a public GCS bucket, not under /api/.
# We mirror them locally under /api/educative-d2-diagrams/... so they fit the
# same path-based layout as every other downloaded asset.
_D2_GCS_HOST = "educative-d2-diagrams.storage.googleapis.com"
_D2_LOCAL_PREFIX = "/api/educative-d2-diagrams"


# ── Helpers ──────────────────────────────────────────────────────────────── #

def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _load_config_json() -> dict:
    cfg = configparser.ConfigParser()
    cfg.read(constants.defaultConfigPath)
    s = cfg["ScraperConfig"] if "ScraperConfig" in cfg else {}
    return {
        "saveDirectory": s.get("savedirectory", ".") if hasattr(s, "get") else ".",
    }


def _normalize_educative_api_url(raw_url) -> str:
    if not isinstance(raw_url, str):
        return ""

    url = raw_url.strip()
    if not url:
        return ""

    if url.startswith("/api/"):
        return "https://www.educative.io" + url
    if url.startswith("api/"):
        return "https://www.educative.io/" + url
    if url.startswith("https://www.educative.io/api/"):
        return url
    if url.startswith("http://www.educative.io/api/"):
        return "https://" + url[len("http://"):]
    return ""


def _urls_for_file(content: dict, author_id: str, collection_id: str, page_id: str) -> list:
    """Construct the download URL for a File component."""
    image_id  = content.get("image_id")
    file_name = content.get("file_name") or ""
    if not image_id:
        return []
    return [f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}/{file_name}"]


def _urls_for_image(content: dict, author_id: str, collection_id: str, page_id: str, content_str: str = "") -> list:
    """Construct the image URL for an Image component.
    Falls back to scanning the raw JSON string if image_id is absent
    (e.g. URL stored under a 'path' key with ?page_type=... query param).
    """
    image_id = content.get("image_id")
    if image_id:
        return [f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}"]
    # Fallback: scan raw JSON for any /api/ URL
    return _urls_from_scan(content_str) if content_str else []


def _urls_for_button_link(content: dict) -> list:
    seen, result = set(), []
    for candidate in (content.get("url"),):
        url = _normalize_educative_api_url(candidate)
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _local_path_for_d2_download_url(download_url: str) -> str:
    """Derive a local /api/ path from an external D2Diagram GCS download URL.

    Example:
        https://educative-d2-diagrams.storage.googleapis.com/123/456/file.txt
        → /api/educative-d2-diagrams/123/456/file.txt
    """
    if not isinstance(download_url, str):
        return ""
    url = download_url.strip()
    # Strip scheme (http:// or https://)
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    # Must come from the expected GCS host
    if not url.startswith(_D2_GCS_HOST):
        return ""
    remaining = url[len(_D2_GCS_HOST):]  # e.g. /123/456/file.txt
    return _D2_LOCAL_PREFIX + remaining


def _urls_for_d2diagram(content: dict, conn: sqlite3.Connection, course_id: int,
                        topic_index: int, component_index: int) -> list:
    """Extract the D2Diagram download URL and persist the local path into content_json.

    Returns a list with the local /api/ path (used by the downloader to resolve
    the save destination).  The actual download source is stored as a second
    element so the downloader can fetch from the external URL.
    """
    d2_file = content.get("d2File")
    if not isinstance(d2_file, dict):
        return []

    download_url = d2_file.get("downloadUrl", "")
    if not download_url:
        return []

    local_path = _local_path_for_d2_download_url(download_url)
    if not local_path:
        return []

    # Persist local_path back into content_json only if the key is not yet set.
    if not d2_file.get("localPath"):
        row = conn.execute(
            "SELECT content_json FROM components "
            "WHERE course_id = ? AND topic_index = ? AND component_index = ?",
            (course_id, topic_index, component_index),
        ).fetchone()
        if row:
            try:
                stored = json.loads(row["content_json"] or "{}")
            except json.JSONDecodeError:
                stored = {}
            if isinstance(stored.get("d2File"), dict) and not stored["d2File"].get("localPath"):
                stored["d2File"]["localPath"] = local_path
                conn.execute(
                    "UPDATE components SET content_json = ? "
                    "WHERE course_id = ? AND topic_index = ? AND component_index = ?",
                    (json.dumps(stored, ensure_ascii=False), course_id, topic_index, component_index),
                )

    # Return (local_path, download_url) tuple encoded as a two-item list so the
    # downloader knows both the save path and the fetch URL.
    return [[local_path, download_url]]


def _urls_for_drawiowidget(content: dict) -> tuple:
    """Returns (urls, updated_content) for DrawIOWidget slides."""
    slides_id = content.get("slidesId")
    if not (content.get("slidesEnabled") and content.get("isSlides") and slides_id):
        return [], content

    editor_image_path = content.get("editorImagePath", "")
    slides_api_data = content.get("slidesApiData", {})
    image_ids = slides_api_data.get("image_ids", [])

    if image_ids and editor_image_path:
        match = re.search(r'(/api/collection/\d+/\d+/page/\d+/image)', editor_image_path)
        if match:
            base_path = match.group(1)
            content["slidesImages"] = [f"{base_path}/{iid}" for iid in image_ids]

    urls = []
    slides_images = content.get("slidesImages", [])
    for img_url in slides_images:
        path_match = re.search(r'(/api/collection/\d+/\d+/page/\d+/image/\d+)', img_url)
        if path_match:
            clean_path = path_match.group(1)
            dl_url = f"{clean_path}?page_type=collection_lesson&get_optimised=true&slide_id={slides_id}&collection_token=undefined"
            urls.append(dl_url)

    return urls, content


def _urls_from_scan(content_json_str: str) -> list:
    """Return all unique https://educative.io/api/collection/... URLs found in the raw JSON string."""
    matches = ASSET_SCAN_API_PATH_REGEX.findall(content_json_str)
    seen, result = set(), []
    for path in matches:
        url = _normalize_educative_api_url(path)
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _urls_for_udata(content_json_str: str) -> tuple:
    """Extract /udata/ URLs from component JSON string and persist localPath mapping.
    
    Returns a tuple of (list of urls, updated_str).
    """
    matches = UDATA_SCAN_REGEX.findall(content_json_str)
    if not matches:
        return [], content_json_str

    seen = set()
    result = []
    
    updated_str = content_json_str

    for path in matches:
        if path not in seen:
            seen.add(path)
            local_path = "/api" + path
            # String replace directly in the JSON string
            updated_str = updated_str.replace(path, local_path)
            # Return flat string URL so static_assets table stores the direct URL without /api/
            result.append(urllib.parse.quote(path))

    return result, updated_str


def _clean_api_domains(content_json_str: str) -> str:
    """Removes educative.io domain prefix from any /api/ paths in content_json."""
    if not content_json_str:
        return content_json_str
    import re
    return re.sub(r'https?://(?:www\.)?educative\.io/api/', '/api/', content_json_str)


def resolve_db_path(config_json: dict = None, db_path: str = None) -> str:
    """Resolve database path from explicit path first, then config.ini saveDirectory."""
    if db_path:
        p = Path(db_path)
        if not p.exists():
            raise FileNotFoundError(f"Error: database not found at '{p}'")
        return str(p)

    cfg = config_json or _load_config_json()
    save_dir = Path(cfg.get("saveDirectory", "."))
    from_save_dir = save_dir / "educative_scraper.db"
    if from_save_dir.exists():
        return str(from_save_dir)

    fallback = Path(__file__).resolve().parent.parent.parent / "downloaded_files" / "educative_scraper.db"
    if fallback.exists():
        return str(fallback)

    raise FileNotFoundError(
        "Usage: python -m src.Utility.StaticAssetExtractor <path/to/educative_scraper.db>\n"
        f"Could not find DB in saveDirectory ('{from_save_dir}') or fallback ('{fallback}')."
    )


# ── Main extraction logic ─────────────────────────────────────────────────── #

def extract_and_store(db_path: str, progress_queue=None):
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

        if progress_queue:
            progress_queue.put(("color", "green"))
            progress_queue.put(("max-topic", len(pairs)))
            progress_queue.put(("progress-topic", 0))
            progress_queue.put(("max-course", len(pairs)))
            progress_queue.put(("progress-course", 0))

        now = datetime.utcnow().isoformat()
        stored = 0
        skipped = 0

        for pair_num, pair in enumerate(pairs, start=1):
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
                original_content_str = comp["content_json"] or "{}"
                content_str = original_content_str

                try:
                    content = json.loads(content_str)
                except json.JSONDecodeError:
                    content = {}

                if comp_type == "File":
                    urls = _urls_for_file(content, author_id, collection_id, page_id)
                elif comp_type == "Image":
                    urls = _urls_for_image(content, author_id, collection_id, page_id, content_str)
                elif comp_type == "ButtonLink":
                    urls = _urls_for_button_link(content)
                    if not urls:
                        urls = _urls_from_scan(content_str)
                elif comp_type == "D2Diagram":
                    urls = _urls_for_d2diagram(content, conn, course_id, topic_index, comp_idx)
                    # reload content_str in case D2Diagram modified content_json directly in DB
                    row = conn.execute("SELECT content_json FROM components WHERE course_id=? AND topic_index=? AND component_index=?", (course_id, topic_index, comp_idx)).fetchone()
                    if row: content_str = row["content_json"] or content_str
                elif comp_type == "DrawIOWidget":
                    urls, content = _urls_for_drawiowidget(content)
                    content_str = json.dumps(content, ensure_ascii=False)
                else:
                    urls = _urls_from_scan(content_str)

                udata_urls, updated_str = _urls_for_udata(content_str)
                if udata_urls:
                    urls.extend(udata_urls)

                # Clean domain prefixes from all /api/ URLs across the entire component JSON
                updated_str = _clean_api_domains(updated_str)

                # Persist modifications if string was updated
                if updated_str != original_content_str:
                    conn.execute(
                        "UPDATE components SET content_json = ? "
                        "WHERE course_id = ? AND topic_index = ? AND component_index = ?",
                        (updated_str, course_id, topic_index, comp_idx),
                    )

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

            if progress_queue:
                progress_queue.put(("progress-topic", pair_num))
                progress_queue.put(("progress-course", stored + skipped))

        conn.commit()
        print(f"Done. Stored: {stored} topic row(s), skipped: {skipped} (no /api/ URLs found).")

    except Exception:
        if progress_queue:
            progress_queue.put(("color", "red"))
        raise

    finally:
        conn.close()


def run_from_config(config_json: dict = None, db_path: str = None, progress_queue=None):
    resolved_db = resolve_db_path(config_json=config_json, db_path=db_path)
    print(f"Database: {resolved_db}")
    extract_and_store(resolved_db, progress_queue=progress_queue)


# ── Entry point ───────────────────────────────────────────────────────────── #

def _resolve_db_path() -> str:
    db_arg = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        return resolve_db_path(config_json=_load_config_json(), db_path=db_arg)
    except FileNotFoundError as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    db = _resolve_db_path()
    print(f"Database: {db}")
    extract_and_store(db)
