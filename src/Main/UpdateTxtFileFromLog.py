'''
    > If the EducativeScraper has stopped due to some error it will automatically
    update the urls.txt file with the last topic URL using the log file.
    > A Backup of the urls.txt file will be created before updating the file.
    > It will retry 3 times to start the scraper using the last specific topic Url.

    Note: This script should be executed only when the scraper has stopped executing for some reason.
'''

import re
import os
from src.Main.MailNotify import MailNotify
from src.Utility.FileUtility import FileUtility
from src.Utility.ConfigUtility import ConfigUtility
from src.Logging.Logger import Logger
from src.Common.Constants import constants
import shutil


class UpdateTxtFileFromLog:
    def __init__(self):
        self.configUtil = ConfigUtility()
        self.fileUtil = FileUtility()
        self.mailNotify = MailNotify()
        self.config = self.configUtil.loadConfig()['ScraperConfig']
        self.logger = Logger(self.config, "UpdateTxtFileFromLog").logger
        self.lastTopicUrlsList = []
        self.blockScraper = False


    def getBlockScraper(self):
        return self.blockScraper
    

    def setBlockScraper(self, blockScraper):
        self.blockScraper = blockScraper

    
    def resetLastTopicUrlsList(self):
        self.lastTopicUrlsList = []


    def getLogFileData(self):
        try:
            logFilePath = os.path.join(constants.ROOT_DIR, 'EducativeScraper.log')
            if os.path.exists(constants.defaultConfigPath):
                logFilePath = os.path.join(self.config['savedirectory'], 'EducativeScraper.log')

            self.logger.info(f"Opening log file: {logFilePath}")
            fileData = self.fileUtil.loadTextFileNonStrip(logFilePath)
            return reversed(fileData)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"getLogFileData: {lineNumber}: {e}")


    def getLastTopicUrl(self, logFileData):
        try:
            urlPattern = re.compile(r'(?:Started Scraping from Text File URL: |Scraping Topic: )(.+)')
            httpsPattern = re.compile(r'https://(.+)')
            for line in logFileData:
                match = urlPattern.search(line)
                if match: 
                    return httpsPattern.search(match.group(1)).group(0)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"getLastTopicUrl: {lineNumber}: {e}")


    def getRefactoredUrl(self, url):
        if "?" in url:
            url = "".join(url.split("?")[:-1])
        url = url.split("/")
        if url[-1] in ["assessment", "cloudlab", "project"]:
            url = url[:-1]
        return "/".join(url[:-1])


    def updateUrlsFile(self, urlsTextFilePath, refactoredUrl, lastTopicUrl):
        try:
            lines = self.fileUtil.loadTextFileNonStrip(urlsTextFilePath)
            idxToReplace = next((i for i, line in enumerate(lines) if refactoredUrl in line), None)
            self.logger.info(f"Index to replace: {idxToReplace}")

            if idxToReplace is not None:
                shutil.copy2(urlsTextFilePath, urlsTextFilePath + '.bak')
                newLines = [lastTopicUrl + '\n']
                newLines.extend(lines[idxToReplace + 1:])
                self.fileUtil.writeLines(urlsTextFilePath, newLines)
                self.logger.info("URL replaced in urls.txt file")
                return True
            raise Exception("Index to replace is None")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"updateUrlsFile: {lineNumber}: {e}")
    

    def checkCountOfLastTopicUrls(self, lastTopicUrl):
        if self.lastTopicUrlsList.count(lastTopicUrl) >= 2:
            message = f"Failed to start scraping 3 times for {lastTopicUrl}. Exiting..."
            self.logger.error(message)
            self.mailNotify.send_email(message)
            self.blockScraper = True
            return False
        return True


    def updateTextFileFromLogMain(self):
        try:
            logFileData = self.getLogFileData()
            lastTopicUrl = self.getLastTopicUrl(logFileData)
            if "?showContent=true" not in lastTopicUrl:
                lastTopicUrl += "?showContent=true"
            self.logger.info(f"Last Topic URL: {lastTopicUrl}")
            if not self.checkCountOfLastTopicUrls(lastTopicUrl):
                return False
            self.lastTopicUrlsList.append(lastTopicUrl)
            refactoredUrl = self.getRefactoredUrl(lastTopicUrl)
            self.logger.info(f"Refactored URL: {refactoredUrl}")
            urlsTextFilePath = self.config['courseurlsfilepath']
            self.logger.info(f"Updating Urls Text File: {urlsTextFilePath}")
            return self.updateUrlsFile(urlsTextFilePath, refactoredUrl, lastTopicUrl)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            message = f"updateTextFileFromLogMain: {lineNumber}: {e}"
            self.logger.error(message)
            self.mailNotify.send_email(message)


if __name__ == '__main__':
    updateTextFileFromLog = UpdateTxtFileFromLog()
    updateTextFileFromLog.updateTextFileFromLogMain()