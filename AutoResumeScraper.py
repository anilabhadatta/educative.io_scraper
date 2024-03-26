'''
    > If the EducativeScraper has stopped due to some error it will automatically
    update the urls.txt file with the last topic URL using the log file.
    > A Backup of the urls.txt file will be created before updating the file.
    > It will retry 3 times to start the scraper using the last specific topic Url.
    
    To implement:
    1. Implement the logic to detect if the scraper has stopped.(process id or any other way)
    2. Implement the logic to start the scraper again.
    3. Remove the break statement from line.(115)

    Note: This script should be executed only when the scraper has stopped executing for some reason.
'''

import re
import os
import time
from src.Utility.ConfigUtility import ConfigUtility
import shutil

OS_ROOT = os.path.join(os.path.expanduser('~'), 'EducativeScraper')
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
defaultConfigPath = os.path.join(OS_ROOT, 'config.ini')
lastTopicUrlsList = [] 


def getConfig():
    if os.path.exists(defaultConfigPath):
        config = ConfigUtility().loadConfig()['ScraperConfig']
        return config


def getLogFileData():
    logFilePath = os.path.join(ROOT_DIR, 'EducativeScraper.log')
    if os.path.exists(defaultConfigPath):
        config = getConfig()
        logFilePath = os.path.join(config['savedirectory'], 'EducativeScraper.log')

    print("Opening log file: ", logFilePath)
    with open(logFilePath, 'r') as file:
        data = reversed(file.readlines())
        return data


def getLastTopicUrl(logFileData):
    urlPattern = re.compile(r'(?:Started Scraping from Text File URL: |Scraping Topic: )(.+)')
    httpsPattern = re.compile(r'https://(.+)')
    for line in logFileData:
        match = urlPattern.search(line)
        if match: 
            return httpsPattern.search(match.group(1)).group(0)


def getUrsTextFilePath():
    if os.path.exists(defaultConfigPath):
        config = getConfig()
        return os.path.join(config['courseurlsfilepath'])
        

def getRefactoredUrl(url):
    if "?" in url:
        url = "".join(url.split("?")[:-1])
    url = url.split("/")
    if url[-1] in ["assessment", "cloudlab", "project"]:
        url = url[:-1]
    return "/".join(url[:-1])


def updateUrlsFile(urlsTextFilePath, refactoredUrl, lastTopicUrl):
    with open(urlsTextFilePath, 'r') as file:
        lines = file.readlines()

    idxToReplace = next((i for i, line in enumerate(lines) if refactoredUrl in line), None)
    print("Index to replace:", idxToReplace)

    if idxToReplace is not None:
        shutil.copy2(urlsTextFilePath, urlsTextFilePath + '.bak')
        newLines = [lastTopicUrl + '\n']
        newLines.extend(lines[idxToReplace + 1:])
        with open(urlsTextFilePath, 'w') as file:
            file.writelines(newLines)
        print("URL replaced in urls.txt file")


def mainLogicToUpdateTextFile(lastTopicUrl):
    refactoredUrl = getRefactoredUrl(lastTopicUrl)
    print("Refactored URL:", refactoredUrl)
    urlsTextFilePath = getUrsTextFilePath()
    print("Updating Urls Text File:", urlsTextFilePath)
    if urlsTextFilePath:
        updateUrlsFile(urlsTextFilePath, refactoredUrl, lastTopicUrl) 
    else:
        print("URLs.txt file not found")


if __name__ == '__main__':
    while True:
        '''If the scraper has stopped, it will be detected here'''
        # logic yet to be implemented

        '''
        If the scraper has stopped, this block of code will be executed 
        to update the urls.txt file with the last topic URL
        '''
        logFileData = getLogFileData()
        if logFileData:
            lastTopicUrl = getLastTopicUrl(logFileData)
            print("Last Topic URL:", lastTopicUrl)
            if lastTopicUrl:
                if lastTopicUrlsList.count(lastTopicUrl) >= 3:
                    print("Failed to start scraping. Exiting...")
                    break
                lastTopicUrlsList.append(lastTopicUrl)
                mainLogicToUpdateTextFile(lastTopicUrl)
        
        break # Remove this line after implementing the above logic

        '''After updating the urls.txt file, the scraper will be started again'''
        # logic yet to be implemented

        '''If scraper is still working then sleep for 5 minutes'''
        time.sleep(300)
        

