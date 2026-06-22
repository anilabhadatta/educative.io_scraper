"""
DatabaseManager.py

SQLite persistence layer for the API scraper.

Schema
------
paths        one row per scraped Path
courses      one row per scraped Course / Cloudlab / Project, optionally linked to a path
projects     project metadata linked to a course row (one project per course)
topics       leaf pages inside a course, keyed by (course_id, topic_index)
components   one row per widget, linked by (course_id, topic_index)
"""

import sqlite3
import threading
from pathlib import Path

from src.ScraperType.ApiScraper.Database.DatabaseTableQueries import (
    ComponentsTableQueries,
    CoursesTableQueries,
    PathsTableQueries,
    ProgressQueries,
    ProjectsTableQueries,
    PublicCourseQueries,
    TopicsTableQueries,
)
from src.Logging.Logger import Logger


class DatabaseManager:
    """Thread-safe wrapper around a SQLite database."""

    _DDL = """
    CREATE TABLE IF NOT EXISTS paths (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        path_author_id      TEXT    NOT NULL,
        path_collection_id  TEXT    NOT NULL,
        path_url_slug       TEXT,
        path_title          TEXT,
        is_active           INTEGER NOT NULL DEFAULT 1,
        scraped_at          TEXT    NOT NULL,
        UNIQUE(path_author_id, path_collection_id)
    );

    CREATE TABLE IF NOT EXISTS courses (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        type            TEXT    NOT NULL DEFAULT 'Course',
        path_id         INTEGER REFERENCES paths(id),
        url             TEXT    NOT NULL,
        structure_hash  TEXT    NOT NULL,
        slug            TEXT    NOT NULL,
        author_id       TEXT,
        collection_id   TEXT,
        title           TEXT,
        toc_json        TEXT,
        cloudlab_id     TEXT,
        project_id      INTEGER REFERENCES projects(id),
        is_active       INTEGER NOT NULL DEFAULT 1,
        scraped_at      TEXT    NOT NULL,
        UNIQUE(type, structure_hash)
    );

    CREATE TABLE IF NOT EXISTS projects (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        project_author_id     TEXT    NOT NULL,
        project_collection_id TEXT    NOT NULL,
        project_work_id       TEXT    NOT NULL,
        project_title         TEXT,
        project_url_slug      TEXT,
        is_active             INTEGER NOT NULL DEFAULT 1,
        scraped_at            TEXT    NOT NULL,
        UNIQUE(project_author_id, project_collection_id, project_work_id)
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
        UNIQUE(course_id, topic_index)
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
    CREATE INDEX IF NOT EXISTS idx_paths_author_collection ON paths(path_author_id, path_collection_id);
    CREATE INDEX IF NOT EXISTS idx_projects_triplet   ON projects(project_author_id, project_collection_id, project_work_id);
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
        self.paths      = PathsTableQueries(self._connect, self._lock, self.logger)
        self.courses    = CoursesTableQueries(self._connect, self._lock, self.logger)
        self.projects   = ProjectsTableQueries(self._connect, self._lock, self.logger)
        self.topics     = TopicsTableQueries(self._connect, self._lock, self.logger)
        self.components = ComponentsTableQueries(self._connect, self._lock, self.logger)
        self.progress   = ProgressQueries(self._connect, self._lock, self.logger)
        self.publicContent = PublicCourseQueries(self._connect, self._lock, self.logger)
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

    def shutdown(self):
        """Force a WAL checkpoint to merge data and clean up the .wal file."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except Exception as e:
                self.logger.error(f"Error during database shutdown checkpoint: {e}")
            finally:
                conn.close()
                self.logger.info("Database shutdown complete, WAL checkpointed.")

    # ------------------------------------------------------------------ #
    #  Path
    # ------------------------------------------------------------------ #

    def upsert_path(self, path_author_id: str, path_collection_id: str,
                    path_url_slug: str, path_title: str) -> int:
        return self.paths.upsert_path(path_author_id, path_collection_id, path_url_slug, path_title)

    # ------------------------------------------------------------------ #
    #  Course
    # ------------------------------------------------------------------ #

    def upsert_course(self, url: str, slug: str, author_id: str, collection_id: str,
                      title: str, toc: list, course_type: str = "Course",
                      path_id: int = None, project_id: str = None,
                      topic_slugs: list = None) -> int:
        """Persist the course row. toc_json is stored raw here;
        call finalize_course_toc() after upsert_topics_for_course() to
        enrich it with DB-sourced course_id / topic_index values.
        """
        return self.courses.upsert_course(
            url,
            slug,
            author_id,
            collection_id,
            title,
            toc,
            course_type,
            path_id,
            project_id,
            topic_slugs,
        )

    def upsert_project(self, project_author_id: str,
                       project_collection_id: str, project_work_id: str,
                       project_title: str, project_url_slug: str = "") -> int:
        return self.projects.upsert_project(
            project_author_id,
            project_collection_id,
            project_work_id,
            project_title,
            project_url_slug,
        )

    def finalize_course_toc(self, course_id: int):
        """Enrich toc_json with course_id and topic_index sourced from the topics table.

        Must be called AFTER upsert_topics_for_course() so the topics rows exist.
        Looks up each toc entry's api_url in the topics table to get the
        authoritative topic_index instead of relying on the in-memory counter.

        Backward-compatible: all existing keys in each topic dict are preserved.
        """
        self.courses.finalize_course_toc(course_id)

    # ------------------------------------------------------------------ #
    #  Topics
    # ------------------------------------------------------------------ #

    def upsert_topics_for_course(self, course_id: int, topic_names: list,
                                  topic_urls: list, api_urls: list,
                                  topic_slugs: list = None):
        """Insert or update topic stubs. Keeps status=done for already-completed topics."""
        self.topics.upsert_topics_for_course(course_id, topic_names, topic_urls, api_urls, topic_slugs)

    def get_topic_by_api_url(self, course_id: int, api_url: str):
        return self.topics.get_topic_by_api_url(course_id, api_url)

    # ------------------------------------------------------------------ #
    #  Components
    # ------------------------------------------------------------------ #

    def save_topic_content(self, course_id: int, topic_index: int, components: list,
                            author_id: str = "", collection_id: str = "",
                            topic_api_url: str = ""):
        """Mark topic done, store components, and extract static asset URLs into static_assets."""
        self.components.save_topic_content(course_id, topic_index, components, author_id, collection_id, topic_api_url)

    def mark_topic_done(self, course_id: int, topic_index: int):
        self.topics.mark_topic_done(course_id, topic_index)

    def mark_topic_error(self, course_id: int, topic_index: int, error_msg: str):
        self.topics.mark_topic_error(course_id, topic_index, error_msg)

    # ------------------------------------------------------------------ #
    #  Progress (used by scraper for logging)
    # ------------------------------------------------------------------ #

    def get_scrape_progress(self, course_id: int) -> dict:
        return self.progress.get_scrape_progress(course_id)

    # ------------------------------------------------------------------ #
    #  Public Content (Answers / Blog / Newsletter)
    # ------------------------------------------------------------------ #

    def upsert_public_course(self, page_type: str) -> int:
        """Find or create the single aggregator course row for a public content type."""
        return self.publicContent.upsert_public_course(page_type)

    def upsert_topic_in_public_course(self, course_id: int, topic_url: str,
                                      title: str, slug: str, page_id: str) -> tuple:
        """Append/update one topic inside a public course. Returns (topic_index, is_new)."""
        return self.publicContent.upsert_topic_in_public_course(
            course_id, topic_url, title, slug, page_id
        )

    def update_public_course_toc(self, course_id: int):
        """Rebuild toc_json for a public course from its current topics."""
        self.publicContent.update_public_course_toc(course_id)
