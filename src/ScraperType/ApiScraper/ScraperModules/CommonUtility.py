import re
from unicodedata import category

from src.ScraperType.ApiScraper.APIScraperConstants import (
    COLLECTION_TOPIC_API_URL_REGEX,
    PROJECT_TOPIC_API_URL_REGEX,
)


class CommonUtility:
    @staticmethod
    def sanitize_topic_name(value) -> str:
        text = str(value or "")
        text = "".join(ch for ch in text if category(ch) not in ("Cf", "Cc", "Cs"))
        text = re.sub(r"\s+", " ", text).strip()
        return text or "untitled-topic"


    @staticmethod
    def extract_ids_from_topic_api_url(topicApiUrl: str):
        apiUrl = str(topicApiUrl or "").split("?", 1)[0]

        collectionMatch = COLLECTION_TOPIC_API_URL_REGEX.search(apiUrl)
        if collectionMatch:
            return collectionMatch.group(1), collectionMatch.group(2), collectionMatch.group(3)

        projectMatch = PROJECT_TOPIC_API_URL_REGEX.search(apiUrl)
        if projectMatch:
            return projectMatch.group(1), projectMatch.group(2), projectMatch.group(4)

        return "", "", ""


    @staticmethod
    def extract_project_topic_components(topicRawJson: dict) -> list:
        content = topicRawJson.get("content", {})
        if not isinstance(content, dict):
            return []

        projectComponents = []
        for groupName in ("descriptionWidgets", "hintWidgets", "solutionWidgets"):
            widgets = content.get(groupName, [])
            if not isinstance(widgets, list):
                continue
            for widgetIndex, widget in enumerate(widgets):
                if not isinstance(widget, dict):
                    continue

                component = {
                    "type": str(widget.get("type") or "ProjectWidget"),
                    "content": widget.get("content", {}),
                    "project_widget_group": groupName,
                    "project_widget_index": widgetIndex,
                }
                extraWidgetData = {
                    key: value for key, value in widget.items()
                    if key not in ("type", "content")
                }
                if extraWidgetData:
                    component["project_widget_meta"] = extraWidgetData
                projectComponents.append(component)

        codeContent = content.get("codeContent")
        if isinstance(codeContent, dict):
            projectComponents.append({
                "type": "ProjectCodeContent",
                "content": codeContent,
                "project_widget_group": "codeContent",
                "project_widget_index": 0,
            })

        if projectComponents:
            return projectComponents

        if content:
            return [{
                "type": "ProjectContent",
                "content": content,
                "project_widget_group": "content",
                "project_widget_index": 0,
            }]

        return []


    @staticmethod
    def extract_topic_components_for_persistence(topicRawJson: dict, isProjectCourse: bool) -> list:
        if not isinstance(topicRawJson, dict):
            return []

        if isProjectCourse:
            projectComponents = CommonUtility.extract_project_topic_components(topicRawJson)
            if projectComponents:
                return projectComponents

        components = topicRawJson.get("components", [])
        return components if isinstance(components, list) else []

