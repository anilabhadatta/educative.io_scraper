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
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from src.Logging.Logger import Logger


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

    CREATE INDEX IF NOT EXISTS idx_courses_path      ON courses(path_id);
    CREATE INDEX IF NOT EXISTS idx_topics_course     ON topics(course_id);
    CREATE INDEX IF NOT EXISTS idx_components_topic  ON components(course_id, topic_index);
    CREATE INDEX IF NOT EXISTS idx_components_type   ON components(type);
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
                    conn.execute(
                        """
                        INSERT INTO topics
                            (course_id, topic_index, topic_name, topic_slug, topic_url, api_url, status, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                        ON CONFLICT(course_id, topic_index) DO UPDATE SET
                            topic_name = excluded.topic_name,
                            topic_slug = excluded.topic_slug,
                            topic_url  = excluded.topic_url,
                            api_url    = excluded.api_url,
                            scraped_at = excluded.scraped_at,
                            status     = CASE
                                           WHEN topics.status = 'done' THEN 'done'
                                           ELSE 'pending'
                                         END
                        """,
                        (course_id, idx, name, slug, url, api_url, now),
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

    def save_topic_content(self, course_id: int, topic_index: int, components: list):
        """Mark topic done and store its components (replaces previous on re-scrape)."""
        now = datetime.utcnow().isoformat()
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
                for idx, component in enumerate(components):
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
                conn.commit()
                self.logger.info(
                    f"Saved {len(components)} components for course_id={course_id} topic_index={topic_index}"
                )
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
