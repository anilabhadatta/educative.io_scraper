from src.ScraperType.ApiScraper.APIScraperConstants import ASSET_SCAN_API_PATH_REGEX

def page_id_from_api_url(api_url: str) -> str:
    try:
        return api_url.split("/page/")[1].split("?")[0]
    except IndexError:
        return ""


def urls_for_file(content: dict, author_id: str, collection_id: str, page_id: str) -> list:
    image_id = content.get("image_id")
    file_name = content.get("file_name") or ""
    if not image_id:
        return []
    return [f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}/{file_name}"]


def urls_for_image(content: dict, author_id: str, collection_id: str, page_id: str) -> list:
    image_id = content.get("image_id")
    if not image_id:
        return []
    return [f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}"]


def urls_from_scan(content_json_str: str) -> list:
    matches = ASSET_SCAN_API_PATH_REGEX.findall(content_json_str)
    seen, result = set(), []
    for path in matches:
        url = path
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result
