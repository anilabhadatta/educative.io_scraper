import os
import time

from git.repo.base import Repo

from src.Logging.Logger import Logger
from src.Utility.FileUtility import FileUtility


class CodeUtility:
    def __init__(self, configJson):
        self.configJson = configJson
        self.component = None
        self.codeFolderPath = None
        self.fileUtils = FileUtility()
        self.configJson = configJson
        self.logger = Logger(configJson, "CodeUtility").logger


    def downloadCodeFiles(self, courseTopicPath, component, componentIndex):
        try:
            self.component = component
            self.codeFolderPath = os.path.join(courseTopicPath, f"Codes_{componentIndex + 1}")
            self.fileUtils.deleteFolderIfExists(self.codeFolderPath)
            time.sleep(1)
            self.fileUtils.createFolderIfNotExists(self.codeFolderPath)
            if "TabbedCode" in component["type"]:
                self.downloadTabbedCode()
            elif "CodeTest" in component["type"]:
                self.downloadCodeTest()
            elif "Code" in component["type"]:
                self.downloadCode()
            elif "RunJS" in component["type"]:
                self.downloadRunJS()
            elif "WebpackBin" in component["type"]:
                self.downloadWebpackBin()
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadCodeFiles: {lineNumber}: {e}")


    def downloadCode(self):
        try:
            self.logger.info("Downloading Code...")
            content = self.component["content"]
            entryFileName = content["entryFileName"]
            prependCode, appendCode, tabTitle, testCasePrependCode = "", "", "", ""
            if "title" in content:
                tabTitle = content["title"]
            if "hiddenCodeContent" in content:
                if "prependCode" in content["hiddenCodeContent"]:
                    prependCode = content["hiddenCodeContent"]["prependCode"]
                if "appendCode" in content["hiddenCodeContent"]:
                    appendCode = content["hiddenCodeContent"]["appendCode"]
            if "judge" in content and content["judge"] and "judgeContent" in content:
                if "judgeContentPrepend" in content:
                    testCasePrependCode = content["judgeContentPrepend"]
                testCaseCode = testCasePrependCode + content["judgeContent"]["authorCode"]
                textFilePath = os.path.join(self.codeFolderPath, f"{tabTitle}TestCase.txt")
                self.fileUtils.createTextFile(textFilePath, testCaseCode)
            if "showSolution" in content and content["showSolution"] and "solutionContent" in content:
                solutionContent = content["solutionContent"]
                textFilePath = os.path.join(self.codeFolderPath, f"{tabTitle}Solution.txt")
                self.fileUtils.createTextFile(textFilePath, solutionContent)
            codeContents = prependCode + content["content"] + appendCode
            textFilePath = os.path.join(self.codeFolderPath, f"{tabTitle}{entryFileName}.txt")
            self.fileUtils.createTextFile(textFilePath, codeContents)
            if "additionalContent" in content:
                for additionalContent in content["additionalContent"]:
                    additionalContentFileName = additionalContent["fileName"]
                    additionalContentCode = additionalContent["content"]
                    textFilePath = os.path.join(self.codeFolderPath, f"{tabTitle}{additionalContentFileName}.txt")
                    self.fileUtils.createTextFile(textFilePath, additionalContentCode)

            self.logger.info(f"Code Downloaded at: {self.codeFolderPath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadCode: {lineNumber}: {e}")


    def downloadTabbedCode(self):
        try:
            self.logger.info("Downloading Tabbed Code...")
            content = self.component["content"]
            codeContents = content["codeContents"]
            for codeContent in codeContents:
                self.component["content"] = codeContent
                self.downloadCode()
            self.logger.info(f"Tabbed Code Downloaded at: {self.codeFolderPath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadTabbedCode: {lineNumber}: {e}")


    def downloadCodeTest(self):
        try:
            self.logger.info("Downloading CodeTest...")
            content = self.component["content"]
            solution = content["solution"]["content"]
            privateTestCases = content["privateTestCases"]["content"]
            publicTestCases = content["publicTestCases"]["content"]
            textFilePath = os.path.join(self.codeFolderPath, "Solution.txt")
            self.fileUtils.createTextFile(textFilePath, solution)
            textFilePath = os.path.join(self.codeFolderPath, "PrivateTestCases.txt")
            self.fileUtils.createTextFile(textFilePath, privateTestCases)
            textFilePath = os.path.join(self.codeFolderPath, "PublicTestCases.txt")
            self.fileUtils.createTextFile(textFilePath, publicTestCases)

            additionalFiles = content["additionalFiles"]
            for additionalFile in additionalFiles:
                subFiles = additionalFiles[additionalFile]
                for subFile in subFiles:
                    codeContents = subFiles[subFile]["codeContents"]["content"]
                    language = subFiles[subFile]["codeContents"]["language"]
                    textFilePath = os.path.join(self.codeFolderPath, f"{language}{subFile}.txt")
                    self.fileUtils.createTextFile(textFilePath, codeContents)

            mainCodeContent = content["languageContents"]
            for mainCode in mainCodeContent:
                codeContents = mainCodeContent[mainCode]["codeContents"]["content"]
                language = mainCodeContent[mainCode]["codeContents"]["language"]
                textFilePath = os.path.join(self.codeFolderPath, f"{language}main.txt")
                self.fileUtils.createTextFile(textFilePath, codeContents)
            self.logger.info(f"CodeTest Downloaded at: {self.codeFolderPath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadCodeTest: {lineNumber}: {e}")


    def downloadRunJS(self):
        try:
            self.logger.info("Downloading RunJS...")
            content = self.component["content"]["jotted"]
            if "showSolution" in content and content["showSolution"]:
                solutionPanels = content["solutionPanels"]
                for solutionPanel in solutionPanels:
                    solutionContent = solutionPanels[solutionPanel]
                    textFilePath = os.path.join(self.codeFolderPath, f"Solution{solutionPanel}.txt")
                    self.fileUtils.createTextFile(textFilePath, solutionContent)
            files = content["files"]
            for file in files:
                fileType = file["type"]
                fileContent = file["content"]
                textFilePath = os.path.join(self.codeFolderPath, f"{fileType}.txt")
                self.fileUtils.createTextFile(textFilePath, fileContent)
            self.logger.info(f"RunJs Code Downloaded at: {self.codeFolderPath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadRunJS: {lineNumber}: {e}")


    def downloadWebpackBin(self):
        try:
            self.logger.info("Downloading WebpackBin...")
            content = self.component["content"]
            if "codeContents" in content and "importedGithubPath" in content["codeContents"]:
                importedGithubPath = content["codeContents"]["importedGithubPath"]
                Repo.clone_from(importedGithubPath, self.codeFolderPath)
            self.logger.info(f"WebpackBin Downloaded at: {self.codeFolderPath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadWebpackBin: {lineNumber}: {e}")
