from slugify import slugify
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.ScraperType.ApiScraper.APIScraperConstants import (
	PROJECT_START_OR_RESUME_BUTTON_SELECTOR,
	PROJECT_WIDGET_SELECTOR,
)
from src.ScraperType.ApiScraper.ScraperModules.CommonUtility import CommonUtility
from src.Utility.UrlUtility import UrlUtility
from src.Utility.OSUtility import OSUtility
from src.Logging.Logger import Logger

class ProjectModule:
	def __init__(self, configJson):
		self.urlUtils = UrlUtility()
		self.browser = None
		self.timeout = 10
		self.configJson = configJson
		self.osUtils = OSUtility(configJson)
		self.logger = Logger(configJson, "ProjectModule").logger


	def getProjectCollectionsJson(self, jsonData, workType):
		authorId = str(jsonData["author_id"])
		collectionId = str(jsonData["collection_id"])
		projectId = str(jsonData["project_id"])
		title = jsonData["title"]

		toc = []
		topicApiUrlList = []
		topicNameList = []
		topicSlugList = []
		topicUrlList = []
		topicTypeList = []

		def add_topic(authorId, collectionId, projectId, page, workType):
			topicTitle = CommonUtility.sanitize_topic_name(page.get("title", ""))
			topicSlug = page.get("slug", slugify(topicTitle))
			pageType = page["type"]
			authorId = str(page.get("author_id") or authorId)
			collectionId = str(page.get("collection_id") or collectionId)
			pageId = str(page.get("page_id", page["id"]))

			topicApiUrl = self.urlUtils.getProjectTopicApiUrl(
				authorId=authorId,
				collectionId=collectionId,
				projectId=projectId,
				pageId=pageId,
				workType=workType,
			)
			topicUrl = "cannot infer_project_topic_url"

			topicApiUrlList.append(topicApiUrl)
			topicNameList.append(topicTitle)
			topicSlugList.append(topicSlug)
			topicUrlList.append(topicUrl)
			topicTypeList.append(pageType)

			topicData = {
				"title": topicTitle,
				"slug": topicSlug,
				"api_url": topicApiUrl,
				"url": topicUrl,
				"type": pageType,
			}
			return topicData

		categories = jsonData["toc"]["categories"]
		for category in categories:
			if not category["pages"]:
				topicData = add_topic(authorId, collectionId, projectId, category, workType)
				toc.append(topicData)
			else:
				categoryTopic = {"category": category["title"], "topics": []}
				for page in category["pages"]:
					topicData = add_topic(authorId, collectionId, projectId, page, workType)
					categoryTopic["topics"].append(topicData)
				toc.append(categoryTopic)

		return {
			"authorId": authorId,
			"collectionId": collectionId,
			"projectId": projectId,
			"title": title,
			"topicApiUrlList": topicApiUrlList,
			"topicNameList": topicNameList,
			"topicSlugList": topicSlugList,
			"topicUrlList": topicUrlList,
			"topicTypeList": topicTypeList,
			"toc": toc,
		}
	

	def clickOnStartProject(self):
		try:
			self.logger.info("Clicking on Start Project button")			
			# Click the button
			clickButtonScript = f"""
			try {{
				var startButton = document.evaluate("{PROJECT_START_OR_RESUME_BUTTON_SELECTOR}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
				if (startButton.snapshotLength > 0) {{
					startButton.snapshotItem(0).click();
					return true;
				}}
				return false;
			}} catch (e) {{
				console.log(e);
				return false;
			}}
			"""
			
			buttonClicked = self.browser.execute_script(clickButtonScript)
			if not buttonClicked:
				self.logger.warning("Start/Resume Project button not found on the page.")
				return False
			
			self.logger.info("Successfully clicked 'Start Project' button. Waiting for button to disappear...")
			
			# Wait for the Start Project button to disappear
			try:
				WebDriverWait(self.browser, self.timeout).until(EC.staleness_of_element_located((By.XPATH, PROJECT_START_OR_RESUME_BUTTON_SELECTOR)))
				self.logger.info("Start Project button has disappeared.")
			except:
				self.logger.info("Start Project button is not present anymore or timeout occurred.")
				
			self.osUtils.sleep(5)
			# Wait for the project widget to load
			self.logger.info("Waiting for project widget to load...")
			try:
				WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located((By.XPATH, PROJECT_WIDGET_SELECTOR)))
				self.logger.info("Project widget loaded successfully.")
				return True
			except Exception as wait_error:
				self.logger.warning(f"Timeout waiting for project widget: {wait_error}")
				return False
		except Exception as e:
			lineNumber = e.__traceback__.tb_lineno
			self.logger.error(f"clickOnStartProject: {lineNumber}: {e}")
			return False
