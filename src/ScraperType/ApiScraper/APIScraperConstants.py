import re

EDUCATIVE_BASE_URL = "https://www.educative.io"

SHOW_CONTENT_QUERY = "?showContent=true"

WORK_TYPE_MODULE = "module"
WORK_TYPE_COLLECTION = "collection"

HTTP_PREFIX = "HTTP_"
HTTP_AUTH_ERRORS = ("HTTP_401", "HTTP_403")

SPECIAL_TOPIC_TYPES = [
    "COLLECTION_PROJECT",
    "COLLECTION_CATEGORY",
    "COLLECTION_ASSESSMENT",
    "PATH_EXTERNAL_PROJECT",
    "PATH_EXTERNAL_ASSESSMENT",
    "CLOUD_LAB",
    "LINKED_MOCK_INTERVIEW",
]

PROJECT_API_URL_PATTERN = re.compile(
    r"^https:\/\/www\.educative\.io\/api\/project\/(\d+)\/(\d+)\/(\d+)(?:\/.*)?(?:\?.*)?$"
)
PAL_API_URL_PATTERN = re.compile(
    r"^https:\/\/www\.educative\.io\/api\/pal\/(\d+)\/(\d+)(?:\/.*)?(?:\?.*)?$"
)
COLLECTION_API_URL_PATTERN = re.compile(
    r"^https:\/\/www\.educative\.io\/api\/collection\/(\d+)\/(\d+)(?!.*\/(?:page|image)\/)(?:\/.*)?(?:\?.*)?$"
)

COLLECTION_TOPIC_API_URL_REGEX = re.compile(r"/api/collection/([^/]+)/([^/]+)/page/([^/]+)$")
PROJECT_TOPIC_API_URL_REGEX = re.compile(r"/api/project/([^/]+)/([^/]+)/([^/]+)/([^/]+)$")
ASSET_SCAN_API_PATH_REGEX = re.compile(r'/api/(?:collection|cheatsheet)/[^\s"\' <>{}\\?\]]+')

NEXT_DATA_SELECTOR = "script[id*='__NEXT_DATA__']"

RETRY_MAIN_API_MAX_ATTEMPTS = 2
RETRY_NEXT_F_MAX_ATTEMPTS = 3