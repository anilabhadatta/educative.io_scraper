import hashlib
import json
from datetime import datetime

from src.ScraperType.ApiScraper.Database.DatabaseQueryUtilities import (
    page_id_from_api_url,
    urls_for_file,
    urls_for_image,
    urls_from_scan,
)


class PathsTableQueries:
    def __init__(self, connect, lock, logger):
        self._connect = connect
        self._lock = lock
        self.logger = logger

    def upsert_path(self, path_author_id: str, path_collection_id: str,
                    path_url_slug: str, path_title: str) -> int:
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO paths
                        (path_author_id, path_collection_id, path_url_slug, path_title, scraped_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(path_author_id, path_collection_id) DO UPDATE SET
                        path_url_slug  = excluded.path_url_slug,
                        path_title     = excluded.path_title,
                        scraped_at     = excluded.scraped_at
                    """,
                    (path_author_id, path_collection_id, path_url_slug, path_title, now),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT id FROM paths WHERE path_author_id = ? AND path_collection_id = ?",
                    (path_author_id, path_collection_id),
                ).fetchone()
                path_id = row["id"]
                self.logger.info(
                    f"Upserted Path '{path_title}' (id={path_id}, "
                    f"path_author_id={path_author_id}, path_collection_id={path_collection_id})"
                )
                return path_id
            finally:
                conn.close()


class CoursesTableQueries:
    def __init__(self, connect, lock, logger):
        self._connect = connect
        self._lock = lock
        self.logger = logger

    def upsert_course(self, url: str, slug: str, author_id: str, collection_id: str,
                      title: str, toc: list, course_type: str = "Course",
                      path_id: int = None, project_id: str = None,
                      topic_slugs: list = None) -> int:
        toc_json = json.dumps(toc, ensure_ascii=False)
        now = datetime.utcnow().isoformat()
        topic_slugs = topic_slugs or []
        structure_hash = hashlib.sha256(
            json.dumps([str(slug or "") for slug in topic_slugs], ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT id FROM courses WHERE type = ? AND structure_hash = ? ORDER BY id DESC LIMIT 1",
                    (course_type, structure_hash),
                ).fetchone()
                if row:
                    course_id = row["id"]
                    conn.execute(
                        """
                        UPDATE courses
                        SET type = ?, path_id = ?, slug = ?, author_id = ?, collection_id = ?,
                            title = ?, toc_json = ?, project_id = ?, scraped_at = ?
                        WHERE id = ?
                        """,
                        (course_type, path_id, slug, author_id, collection_id, title, toc_json, project_id, now, course_id),
                    )
                    conn.commit()
                    self.logger.info(f"Reused {course_type} '{title}' (id={course_id})")
                    return course_id

                conn.execute(
                    """
                    INSERT INTO courses
                        (type, path_id, url, structure_hash, slug, author_id, collection_id, title, toc_json, project_id, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (course_type, path_id, url, structure_hash, slug, author_id, collection_id, title, toc_json, project_id, now),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT id FROM courses WHERE type = ? AND structure_hash = ? ORDER BY id DESC LIMIT 1",
                    (course_type, structure_hash),
                ).fetchone()
                course_id = row["id"]
                self.logger.info(f"Inserted new {course_type} '{title}' version (id={course_id})")
                return course_id
            finally:
                conn.close()

    def finalize_course_toc(self, course_id: int):
        with self._lock:
            conn = self._connect()
            try:
                course_row = conn.execute(
                    "SELECT toc_json FROM courses WHERE id = ?",
                    (course_id,),
                ).fetchone()
                if not course_row or not course_row["toc_json"]:
                    self.logger.warning(f"finalize_course_toc: no course row found for id={course_id}")
                    return

                toc = json.loads(course_row["toc_json"])

                rows = conn.execute(
                    "SELECT api_url, topic_index FROM topics WHERE course_id = ?",
                    (course_id,),
                ).fetchall()
                api_url_to_index: dict = {r["api_url"]: r["topic_index"] for r in rows}

                enriched = []
                for item in toc:
                    if "category" in item:
                        new_topics = []
                        for topic in item.get("topics", []):
                            new_topic = dict(topic)
                            new_topic["course_id"] = course_id
                            new_topic["topic_index"] = api_url_to_index.get(new_topic.get("api_url"))
                            new_topics.append(new_topic)
                        new_item = dict(item)
                        new_item["topics"] = new_topics
                        enriched.append(new_item)
                    else:
                        new_item = dict(item)
                        new_item["course_id"] = course_id
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


class ProjectsTableQueries:
    def __init__(self, connect, lock, logger):
        self._connect = connect
        self._lock = lock
        self.logger = logger

    def upsert_project(self, project_author_id: str,
                       project_collection_id: str, project_work_id: str,
                       project_title: str, project_url_slug: str = "") -> int:
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO projects
                        (project_author_id, project_collection_id, project_work_id, project_title, project_url_slug, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_author_id, project_collection_id, project_work_id) DO UPDATE SET
                        project_title         = excluded.project_title,
                        project_url_slug      = excluded.project_url_slug,
                        scraped_at            = excluded.scraped_at
                    """,
                    (project_author_id, project_collection_id, project_work_id, project_title, project_url_slug, now),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT id FROM projects WHERE project_author_id = ? AND project_collection_id = ? AND project_work_id = ?",
                    (project_author_id, project_collection_id, project_work_id),
                ).fetchone()
                project_row_id = row["id"]
                self.logger.info(
                    f"Upserted Project '{project_title}' (id={project_row_id}, "
                    f"project_author_id={project_author_id}, project_collection_id={project_collection_id})"
                    f" with work_id={project_work_id}"
                )
                return project_row_id
            finally:
                conn.close()


class TopicsTableQueries:
    def __init__(self, connect, lock, logger):
        self._connect = connect
        self._lock = lock
        self.logger = logger

    def upsert_topics_for_course(self, course_id: int, topic_names: list,
                                 topic_urls: list, api_urls: list,
                                 topic_slugs: list = None):
        now = datetime.utcnow().isoformat()
        if topic_slugs is None:
            topic_slugs = []
        api_count = len(api_urls)
        with self._lock:
            conn = self._connect()
            try:
                for idx in range(api_count):
                    api_url = api_urls[idx]
                    name = topic_names[idx]
                    slug = topic_slugs[idx]
                    url = topic_urls[idx]
                    page_id = page_id_from_api_url(api_url)
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

                conn.execute(
                    "DELETE FROM topics WHERE course_id = ? AND topic_index >= ?",
                    (course_id, api_count),
                )
                conn.execute(
                    "DELETE FROM static_assets WHERE course_id = ? AND topic_index >= ?",
                    (course_id, api_count),
                )
                conn.commit()
                self.logger.info(f"Upserted {api_count} topics for course_id={course_id}")
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


class ComponentsTableQueries:
    def __init__(self, connect, lock, logger):
        self._connect = connect
        self._lock = lock
        self.logger = logger

    def save_topic_content(self, course_id: int, topic_index: int, components: list,
                           author_id: str = "", collection_id: str = "",
                           topic_api_url: str = ""):
        now = datetime.utcnow().isoformat()
        page_id = page_id_from_api_url(topic_api_url)

        assets: dict = {}
        enriched_components: list = []
        for idx, component in enumerate(components):
            comp_type = component.get("type", "")
            content = dict(component.get("content", {}))
            content_str = json.dumps(content, ensure_ascii=False)

            urls = []
            if comp_type == "File":
                if not content.get("path"):
                    urls = urls_for_file(content, author_id, collection_id, page_id)
                    if urls:
                        content["path"] = urls[0].replace("https://www.educative.io", "")
                else:
                    urls = [content["path"]]
            elif comp_type == "Image":
                if not content.get("path"):
                    urls = urls_for_image(content, author_id, collection_id, page_id)
                    if urls:
                        content["path"] = urls[0].replace("https://www.educative.io", "")
                else:
                    urls = [content["path"]]
            else:
                urls = urls_from_scan(content_str)

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


class ProgressQueries:
    def __init__(self, connect, lock, logger):
        self._connect = connect
        self._lock = lock

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


class PublicCourseQueries:
    """DB helpers specific to the 'one course per public content type' model."""

    # Canonical aggregator course URLs — each type maps to exactly one courses row.
    _TYPE_URLS = {
        "Answers":    "https://www.educative.io/answers",
        "Blog":       "https://www.educative.io/blog",
        "Newsletter": "https://www.educative.io/newsletter",
    }

    def __init__(self, connect, lock, logger):
        self._connect = connect
        self._lock = lock
        self.logger = logger

    def upsert_public_course(self, page_type: str) -> int:
        """
        Find or create the single aggregator course row for a public content type
        (Answers / Blog / Newsletter).  The row is identified solely by its URL
        — structure_hash is fixed to the type slug so it never triggers a new row.
        """
        url  = self._TYPE_URLS[page_type]
        slug = page_type.lower()
        now  = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT id FROM courses WHERE url = ? AND type = ?",
                    (url, page_type),
                ).fetchone()
                if row:
                    return row["id"]
                conn.execute(
                    """
                    INSERT INTO courses
                        (type, url, structure_hash, slug, author_id, collection_id,
                         title, toc_json, scraped_at)
                    VALUES (?, ?, ?, ?, '', '', ?, '[]', ?)
                    """,
                    (page_type, url, slug, slug, page_type, now),
                )
                conn.commit()
                course_id = conn.execute(
                    "SELECT id FROM courses WHERE url = ? AND type = ?",
                    (url, page_type),
                ).fetchone()["id"]
                self.logger.info(f"Created public aggregator course '{page_type}' (id={course_id})")
                return course_id
            finally:
                conn.close()

    def upsert_topic_in_public_course(self, course_id: int, topic_url: str,
                                      title: str, slug: str, page_id: str) -> tuple:
        """
        Insert or update a single topic row inside a public course, keyed by
        api_url=topic_url.  Never deletes other topics (unlike the batch upsert).
        Returns (topic_index, is_new).
        """
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                existing = conn.execute(
                    "SELECT topic_index FROM topics WHERE course_id = ? AND api_url = ?",
                    (course_id, topic_url),
                ).fetchone()
                if existing:
                    topic_index = existing["topic_index"]
                    conn.execute(
                        """
                        UPDATE topics
                        SET topic_name = ?, topic_slug = ?, topic_url = ?,
                            page_id = ?, scraped_at = ?
                        WHERE course_id = ? AND api_url = ?
                        """,
                        (title, slug, topic_url, page_id, now, course_id, topic_url),
                    )
                    conn.commit()
                    return topic_index, False

                row = conn.execute(
                    "SELECT COALESCE(MAX(topic_index) + 1, 0) AS next_idx "
                    "FROM topics WHERE course_id = ?",
                    (course_id,),
                ).fetchone()
                topic_index = row["next_idx"]
                conn.execute(
                    """
                    INSERT INTO topics
                        (course_id, topic_index, topic_name, topic_slug, topic_url,
                         api_url, page_id, status, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (course_id, topic_index, title, slug, topic_url,
                     topic_url, page_id, now),
                )
                conn.commit()
                self.logger.info(
                    f"Inserted public topic '{title}' at index {topic_index} "
                    f"(course_id={course_id})"
                )
                return topic_index, True
            finally:
                conn.close()

    def update_public_course_toc(self, course_id: int):
        """Rebuild toc_json for a public course from its current topics rows."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT topic_index, topic_name, topic_slug, topic_url, api_url "
                    "FROM topics WHERE course_id = ? ORDER BY topic_index",
                    (course_id,),
                ).fetchall()
                toc = [
                    {
                        "index":       r["topic_index"],
                        "title":       r["topic_name"],
                        "slug":        r["topic_slug"],
                        "url":         r["topic_url"],
                        "api_url":     r["api_url"],
                        "course_id":   course_id,
                        "topic_index": r["topic_index"],
                    }
                    for r in rows
                ]
                conn.execute(
                    "UPDATE courses SET toc_json = ? WHERE id = ?",
                    (json.dumps(toc, ensure_ascii=False), course_id),
                )
                conn.commit()
                self.logger.info(
                    f"Rebuilt public course toc_json: course_id={course_id}, "
                    f"{len(toc)} topics"
                )
            finally:
                conn.close()
