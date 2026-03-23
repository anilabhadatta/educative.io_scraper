from slugify import slugify

from src.Logging.Logger import Logger
from src.Utility.UrlUtility import UrlUtility
from src.ScraperType.ApiScraper.ScraperModules.CommonUtility import CommonUtility


class CoursePathModule:
	def __init__(self, configJson):
		self.urlUtils = UrlUtility()
		self.configJson = configJson
		self.logger = Logger(configJson, "CoursePathModule").logger


	def getCoursePathCollectionsJson(self, jsonData, courseType, workType, topicUrl):
		jsonData = jsonData["details"]
		authorId = str(jsonData["author_id"])
		collectionId = str(jsonData["collection_id"])
		title = jsonData["title"]
		pathMeta = {
			"path_author_id": str(jsonData["path_author_id"]),
			"path_collection_id": str(jsonData["path_id"]),
			"path_url_slug": jsonData.get("path_url_slug", slugify(jsonData["path_title"])),
			"path_title": jsonData["path_title"],
		} if courseType == "Path" else None

		toc = []
		topicApiUrlList = []
		topicNameList = []
		topicSlugList = []
		topicUrlList = []
		topicTypeList = []

		def add_topic(authorId, collectionId, page, workType, topicUrl):
			topicTitle = CommonUtility.sanitize_topic_name(page.get("title", ""))
			topicSlug = page.get("slug", slugify(topicTitle))
			pageType = page["type"]
			authorId = str(page.get("author_id", authorId))
			collectionId = str(page.get("collection_id", collectionId))
			pageId = str(page.get("page_id", page["id"]))

			topicApiUrl = self.urlUtils.getCollectionTopicApiUrl(
				authorId=authorId,
				collectionId=collectionId,
				pageId=pageId,
				workType=workType,
			)
			builtTopicUrl = self.urlUtils.getCollectionTopicPageUrl(topicUrl, page)

			topicApiUrlList.append(topicApiUrl)
			topicNameList.append(topicTitle)
			topicSlugList.append(topicSlug)
			topicUrlList.append(builtTopicUrl)
			topicTypeList.append(pageType)

			topicData = {
				"title": topicTitle,
				"slug": topicSlug,
				"api_url": topicApiUrl,
				"url": builtTopicUrl,
				"type": pageType,
			}
			return topicData

		categories = jsonData["toc"]["categories"]
		for category in categories:
			for tocEntry in category.get("toc", [category]):
				pages = tocEntry.get("pages")
				if not pages:
					topicData = add_topic(authorId, collectionId, tocEntry, workType, topicUrl)
					toc.append(topicData)
				else:
					categoryTitle = category["title"] if category.get("toc") else tocEntry["title"]
					categoryTopic = {"category": categoryTitle, "topics": []}
					for page in pages:
						topicData = add_topic(authorId, collectionId, page, workType, topicUrl)
						categoryTopic["topics"].append(topicData)
					toc.append(categoryTopic)

		return {
			"authorId": authorId,
			"collectionId": collectionId,
			"title": title,
			"topicApiUrlList": topicApiUrlList,
			"topicNameList": topicNameList,
			"topicSlugList": topicSlugList,
			"topicUrlList": topicUrlList,
			"topicTypeList": topicTypeList,
			"toc": toc,
			"pathMeta": pathMeta,
		}
