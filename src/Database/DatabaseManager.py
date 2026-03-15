"""
DatabaseManager.py

SQLite persistence layer for the API scraper.

Schema
------
paths       – one row per scraped Path
courses     – one row per scraped Course / Cloudlab / Project, optionally linked to a path
topics      – leaf pages inside a course, keyed by (course_id, topic_index)
components  – one row per widget, linked by (course_id, topic_index)
"""

import json
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from src.Logging.Logger import Logger

# ── Static-asset URL extraction (mirrors StaticAssetExtractor logic) ──────── #

_API_RE = re.compile(r'/api/(?:collection|cheatsheet)/[^\s"\' <>{}\\?\]]+')


def _page_id_from_api_url(api_url: str) -> str:
    try:
        return api_url.split("/page/")[1].split("?")[0]
    except IndexError:
        return ""


def _urls_for_file(content: dict, author_id: str, collection_id: str, page_id: str) -> list:
    image_id  = content.get("image_id")
    file_name = content.get("file_name") or ""
    if not image_id:
        return []
    return [f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}/{file_name}"]


def _urls_for_image(content: dict, author_id: str, collection_id: str, page_id: str) -> list:
    image_id = content.get("image_id")
    if not image_id:
        return []
    return [f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}"]


def _urls_from_scan(content_json_str: str) -> list:
    matches = _API_RE.findall(content_json_str)
    seen, result = set(), []
    for path in matches:
        url = path
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


class DatabaseManager:
    """Thread-safe wrapper around a SQLite database."""

    _DDL = """
    CREATE TABLE IF NOT EXISTS paths (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        url         TEXT    NOT NULL UNIQUE,
        slug        TEXT    NOT NULL,
        title       TEXT,
        toc_json    TEXT,
        scraped_at  TEXT    NOT NULL
    );

    -- type: "Course" | "Cloudlab" | "Project"
    -- path_id: set when this course belongs to a Path
    -- cloudlab_id / project_id: provision for future linking
    CREATE TABLE IF NOT EXISTS courses (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        type            TEXT    NOT NULL DEFAULT 'Course',
        path_id         INTEGER REFERENCES paths(id),
        url             TEXT    NOT NULL UNIQUE,
        slug            TEXT    NOT NULL,
        author_id       TEXT,
        collection_id   TEXT,
        title           TEXT,
        toc_json        TEXT,
        cloudlab_id     TEXT,
        project_id      TEXT,
        scraped_at      TEXT    NOT NULL
    );

    CREATE TABLE IF NOT EXISTS topics (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        topic_index     INTEGER NOT NULL,
        topic_name      TEXT    NOT NULL,
        topic_slug      TEXT    NOT NULL DEFAULT '',
        topic_url       TEXT    NOT NULL,
        api_url         TEXT    NOT NULL,
        page_id         TEXT    NOT NULL DEFAULT '',
        status          TEXT    NOT NULL DEFAULT 'pending',
        scraped_at      TEXT,
        error_msg       TEXT,
        UNIQUE(course_id, topic_index),
        UNIQUE(course_id, api_url)
    );

    CREATE TABLE IF NOT EXISTS components (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        topic_index     INTEGER NOT NULL,
        component_index INTEGER NOT NULL,
        type            TEXT    NOT NULL,
        content_json    TEXT,
        scraped_at      TEXT    NOT NULL,
        FOREIGN KEY (course_id, topic_index)
            REFERENCES topics(course_id, topic_index) ON DELETE CASCADE
    );

    -- One row per (course_id, topic_index).
    -- assets_json: { "component_index": ["url1", "url2", ...], ... }
    CREATE TABLE IF NOT EXISTS static_assets (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        topic_index INTEGER NOT NULL,
        assets_json TEXT    NOT NULL DEFAULT '{}',
        created_at  TEXT    NOT NULL,
        UNIQUE(course_id, topic_index)
    );

    CREATE INDEX IF NOT EXISTS idx_courses_path       ON courses(path_id);
    CREATE INDEX IF NOT EXISTS idx_topics_course      ON topics(course_id);
    CREATE INDEX IF NOT EXISTS idx_components_topic   ON components(course_id, topic_index);
    CREATE INDEX IF NOT EXISTS idx_components_type    ON components(type);
    CREATE INDEX IF NOT EXISTS idx_static_assets_course ON static_assets(course_id);
    """

    def __init__(self, configJson, db_path: str = None):
        self.logger = Logger(configJson, "DatabaseManager").logger
        if db_path is None:
            save_dir = Path(configJson.get("saveDirectory", "."))
            save_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(save_dir / "educative_scraper.db")
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self.logger.info(f"Database ready at: {self.db_path}")

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(self._DDL)
                conn.commit()
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    #  Path
    # ------------------------------------------------------------------ #

    def upsert_path(self, url: str, slug: str, title: str, toc: list) -> int:
        toc_json = json.dumps(toc, ensure_ascii=False)
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO paths (url, slug, title, toc_json, scraped_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        slug       = excluded.slug,
                        title      = excluded.title,
                        toc_json   = excluded.toc_json,
                        scraped_at = excluded.scraped_at
                    """,
                    (url, slug, title, toc_json, now),
                )
                conn.commit()
                row = conn.execute("SELECT id FROM paths WHERE url = ?", (url,)).fetchone()
                path_id = row["id"]
                self.logger.info(f"Upserted Path '{title}' (id={path_id})")
                return path_id
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    #  Course
    # ------------------------------------------------------------------ #

    def upsert_course(self, url: str, slug: str, author_id: str, collection_id: str,
                      title: str, toc: list, course_type: str = "Course",
                      path_id: int = None) -> int:
        """Persist the course row. toc_json is stored raw here;
        call finalize_course_toc() after upsert_topics_for_course() to
        enrich it with DB-sourced course_id / topic_index values.
        """
        toc_json = json.dumps(toc, ensure_ascii=False)
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO courses
                        (type, path_id, url, slug, author_id, collection_id, title, toc_json, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        type          = excluded.type,
                        path_id       = excluded.path_id,
                        slug          = excluded.slug,
                        author_id     = excluded.author_id,
                        collection_id = excluded.collection_id,
                        title         = excluded.title,
                        toc_json      = excluded.toc_json,
                        scraped_at    = excluded.scraped_at
                    """,
                    (course_type, path_id, url, slug, author_id, collection_id, title, toc_json, now),
                )
                conn.commit()
                row = conn.execute("SELECT id FROM courses WHERE url = ?", (url,)).fetchone()
                course_id = row["id"]
                self.logger.info(f"Upserted {course_type} '{title}' (id={course_id})")
                return course_id
            finally:
                conn.close()

    def finalize_course_toc(self, course_id: int):
        """Enrich toc_json with course_id and topic_index sourced from the topics table.

        Must be called AFTER upsert_topics_for_course() so the topics rows exist.
        Looks up each toc entry's api_url in the topics table to get the
        authoritative topic_index instead of relying on the in-memory counter.

        Backward-compatible: all existing keys in each topic dict are preserved.
        """
        with self._lock:
            conn = self._connect()
            try:
                # Load the current (raw) toc_json for this course
                course_row = conn.execute(
                    "SELECT toc_json FROM courses WHERE id = ?",
                    (course_id,),
                ).fetchone()
                if not course_row or not course_row["toc_json"]:
                    self.logger.warning(f"finalize_course_toc: no course row found for id={course_id}")
                    return

                toc = json.loads(course_row["toc_json"])

                # Build api_url -> topic_index lookup from the topics table (ground truth)
                rows = conn.execute(
                    "SELECT api_url, topic_index FROM topics WHERE course_id = ?",
                    (course_id,),
                ).fetchall()
                api_url_to_index: dict = {r["api_url"]: r["topic_index"] for r in rows}

                # Walk the toc and inject course_id + topic_index from DB
                enriched = []
                for item in toc:
                    if "category" in item:
                        new_topics = []
                        for topic in item.get("topics", []):
                            new_topic = dict(topic)
                            new_topic["course_id"]   = course_id
                            new_topic["topic_index"] = api_url_to_index.get(new_topic.get("api_url"))
                            new_topics.append(new_topic)
                        new_item = dict(item)
                        new_item["topics"] = new_topics
                        enriched.append(new_item)
                    else:
                        new_item = dict(item)
                        new_item["course_id"]   = course_id
                        new_item["topic_index"] = api_url_to_index.get(new_item.get("api_url"))
                        enriched.append(new_item)

                conn.execute(
                    "UPDATE courses SET toc_json = ? WHERE id = ?",
                    (json.dumps(enriched, ensure_ascii=False), course_id),
                )
                conn.commit()
                self.logger.info(
                    f"finalize_course_toc: enriched toc_json for course_id={course_id} "
                    f"({len(api_url_to_index)} topics mapped)"
                )
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    #  Topics
    # ------------------------------------------------------------------ #

    def upsert_topics_for_course(self, course_id: int, topic_names: list,
                                  topic_urls: list, api_urls: list,
                                  topic_slugs: list = None):
        """Insert or update topic stubs. Keeps status=done for already-completed topics."""
        now = datetime.utcnow().isoformat()
        if topic_slugs is None:
            topic_slugs = [""] * len(topic_names)
        with self._lock:
            conn = self._connect()
            try:
                for idx, (name, slug, url, api_url) in enumerate(
                    zip(topic_names, topic_slugs, topic_urls, api_urls)
                ):
                    page_id = _page_id_from_api_url(api_url)
                    conn.execute(
                        """
                        INSERT INTO topics
                            (course_id, topic_index, topic_name, topic_slug, topic_url, api_url, page_id, status, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                        ON CONFLICT(course_id, topic_index) DO UPDATE SET
                            topic_name = excluded.topic_name,
                            topic_slug = excluded.topic_slug,
                            topic_url  = excluded.topic_url,
                            api_url    = excluded.api_url,
                            page_id    = excluded.page_id,
                            scraped_at = excluded.scraped_at,
                            status     = CASE
                                           WHEN topics.status = 'done' THEN 'done'
                                           ELSE 'pending'
                                         END
                        """,
                        (course_id, idx, name, slug, url, api_url, page_id, now),
                    )
                conn.commit()
                self.logger.info(f"Upserted {len(topic_names)} topics for course_id={course_id}")
            finally:
                conn.close()

    def get_topic_by_api_url(self, course_id: int, api_url: str):
        with self._lock:
            conn = self._connect()
            try:
                return conn.execute(
                    "SELECT * FROM topics WHERE course_id = ? AND api_url = ?",
                    (course_id, api_url),
                ).fetchone()
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    #  Components
    # ------------------------------------------------------------------ #

    def save_topic_content(self, course_id: int, topic_index: int, components: list,
                            author_id: str = "", collection_id: str = "",
                            topic_api_url: str = ""):
        """Mark topic done, store components, and extract static asset URLs into static_assets."""
        now = datetime.utcnow().isoformat()
        page_id = _page_id_from_api_url(topic_api_url)

        # Build assets dict: { "<component_index>": ["url", ...] }
        # For Image/File components also inject a "path" key into content so
        # the UI can use it directly without re-constructing the URL.
        assets: dict = {}
        enriched_components: list = []
        for idx, component in enumerate(components):
            comp_type = component.get("type", "")
            content   = dict(component.get("content", {}))  # shallow copy to avoid mutating caller's data
            content_str = json.dumps(content, ensure_ascii=False)

            if comp_type == "File":
                urls = _urls_for_file(content, author_id, collection_id, page_id)
                if urls:
                    content["path"] = urls[0].replace("https://www.educative.io", "")
            elif comp_type == "Image":
                urls = _urls_for_image(content, author_id, collection_id, page_id)
                if urls:
                    content["path"] = urls[0].replace("https://www.educative.io", "")
            else:
                urls = _urls_from_scan(content_str)

            if urls:
                assets[str(idx)] = urls

            enriched_components.append({**component, "content": content})

        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE topics SET status = 'done', scraped_at = ?, error_msg = NULL
                    WHERE course_id = ? AND topic_index = ?
                    """,
                    (now, course_id, topic_index),
                )
                conn.execute(
                    "DELETE FROM components WHERE course_id = ? AND topic_index = ?",
                    (course_id, topic_index),
                )
                for idx, component in enumerate(enriched_components):
                    conn.execute(
                        """
                        INSERT INTO components
                            (course_id, topic_index, component_index, type, content_json, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            course_id, topic_index, idx,
                            component.get("type", ""),
                            json.dumps(component.get("content", {}), ensure_ascii=False),
                            now,
                        ),
                    )
                if assets:
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
                conn.commit()
                self.logger.info(
                    f"Saved {len(enriched_components)} components for course_id={course_id} "
                    f"topic_index={topic_index}, assets keys={len(assets)}"
                )
            finally:
                conn.close()

    def mark_topic_done(self, course_id: int, topic_index: int):
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE topics SET status = 'done', error_msg = NULL, scraped_at = ? "
                    "WHERE course_id = ? AND topic_index = ?",
                    (now, course_id, topic_index),
                )
                conn.commit()
            finally:
                conn.close()

    def mark_topic_error(self, course_id: int, topic_index: int, error_msg: str):
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE topics SET status = 'error', error_msg = ?, scraped_at = ?
                    WHERE course_id = ? AND topic_index = ?
                    """,
                    (error_msg, now, course_id, topic_index),
                )
                conn.commit()
            finally:
                conn.close()

    # ------------------------------------------------------------------ #
    #  Progress (used by scraper for logging)
    # ------------------------------------------------------------------ #

    def get_scrape_progress(self, course_id: int) -> dict:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT status, COUNT(*) AS cnt FROM topics WHERE course_id = ? GROUP BY status",
                    (course_id,),
                ).fetchall()
                return {r["status"]: r["cnt"] for r in rows}
            finally:
                conn.close()
