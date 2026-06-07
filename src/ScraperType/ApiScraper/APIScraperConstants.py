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
    "LINKED_CLOUD_LAB"
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
ASSET_SCAN_API_PATH_REGEX = re.compile(
    r'/api/(?:'
    r'collection|cheatsheet'            # course / cheatsheet images
    r'|edpresso/shot'                   # Answers images: /api/edpresso/shot/{id}/image/{id}
    r'|page/\d+/image'                  # Blog/Newsletter images: /api/page/{id}/image/download/{id}
    r')/[^\s"\' <>{}\\\]]+'
)
UDATA_SCAN_REGEX = re.compile(r'(?<!/api)/udata/[^"\'<>{}\\)\];]+')

NEXT_DATA_SELECTOR = "script[id*='__NEXT_DATA__']"

COURSE_TYPE_SELECTOR_TEMPLATE = "//div[contains(@id, 'view-collection-article-content-root')]//a[contains(@href, '/{segment}/')]"
COURSE_TYPE_COLLECTION_NAV_SELECTOR = "//nav//a[contains(@href, '/collection/')]/span/.."
COURSE_TYPE_BREADCRUMB_SELECTOR = "(//*[starts-with(@id,'problemPage_breadcrumbsContainer')]//a)[last()]"

MINIMAP_BUTTON_XPATH = "//button[@aria-label='Toggle Mini Map']"

PROJECT_START_OR_RESUME_BUTTON_SELECTOR = "//button[(normalize-space(.)='Start Project' or normalize-space(.)='Resume Project') and not(@disabled)]"
PROJECT_WIDGET_SELECTOR = "//div[contains(@id, 'widget-parent')][.//text()[normalize-space()]]"

RETRY_MAIN_API_MAX_ATTEMPTS = 2
RETRY_NEXT_F_MAX_ATTEMPTS = 3