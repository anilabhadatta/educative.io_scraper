import os

from src.Utility.OSUtility import OSUtility
from src.Logging.Logger import Logger
from src.Utility.FileUtility import FileUtility


class CodeUtility:
    def __init__(self, configJson):
        self.configJson = configJson
        self.component = None
        self.codeFolderPath = None
        self.fileUtils = FileUtility()
        self.osUtils = OSUtility(configJson)
        self.configJson = configJson
        self.logger = Logger(configJson, "CodeUtility").logger


    def downloadCodeFiles(self, courseTopicPath, component, componentIndex):
        try:
            self.component = component
            self.codeFolderPath = os.path.join(courseTopicPath, f"Codes_{componentIndex + 1}")
            self.fileUtils.deleteFolderIfExists(self.codeFolderPath)
            self.osUtils.sleep(1)
            self.fileUtils.createFolderIfNotExists(self.codeFolderPath)
            if "TabbedCode" in component["type"]:
                self.downloadTabbedCode()
            elif "CodeTest" in component["type"]:
                self.downloadCodeTest()
            elif "EditorCode" in component["type"]:
                self.downloadEditorCode()
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
            prependCode, appendCode, tabTitle, testCasePrependCode, entryFileName = "", "", "", "", "main"
            content = self.component["content"]
            if "entryFileName" in content:
                entryFileName = self.fileUtils.filenameSlugify(content["entryFileName"])
            if "title" in content:
                tabTitle = self.fileUtils.filenameSlugify(content["title"])
            if "hiddenCodeContent" in content and content["hiddenCodeContent"]:
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
                    additionalContentFileName = self.fileUtils.filenameSlugify(additionalContent["fileName"])
                    additionalContentCode = additionalContent["content"]
                    textFilePath = os.path.join(self.codeFolderPath, f"{tabTitle}{additionalContentFileName}.txt")
                    self.fileUtils.createTextFile(textFilePath, additionalContentCode)

            self.logger.info(f"Code Downloaded at: {self.codeFolderPath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadCode: {lineNumber}: {e}")


    def downloadEditorCode(self):
        try:
            self.logger.info("Downloading Editor Code...")
            content = self.component["content"]
            if "content" in content and "language" in content:
                language = self.fileUtils.filenameSlugify(content["language"])
                codeContent = content["content"]
                textFilePath = os.path.join(self.codeFolderPath, f"{language}Code.txt")
                self.fileUtils.createTextFile(textFilePath, codeContent)
            self.logger.info(f"Editor Code Downloaded at: {self.codeFolderPath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadEditorCode: {lineNumber}: {e}")


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
                    language = self.fileUtils.filenameSlugify(subFiles[subFile]["codeContents"]["language"])
                    textFilePath = os.path.join(self.codeFolderPath, f"{language}{subFile}.txt")
                    self.fileUtils.createTextFile(textFilePath, codeContents)

            mainCodeContent = content["languageContents"]
            for mainCode in mainCodeContent:
                codeContents = mainCodeContent[mainCode]["codeContents"]["content"]
                language = self.fileUtils.filenameSlugify(mainCodeContent[mainCode]["codeContents"]["language"])
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
                    textFilePath = os.path.join(self.codeFolderPath, f"Solution{self.fileUtils.filenameSlugify(solutionPanel)}.txt")
                    self.fileUtils.createTextFile(textFilePath, solutionContent)
            files = content["files"]
            for file in files:
                fileType = self.fileUtils.filenameSlugify(file["type"])
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
            if "codeContents" in content:
                children = content["codeContents"]["children"]
                for codeContents in children:
                    nextFolderPath = self.codeFolderPath
                    if "leaf" in codeContents and not codeContents['leaf']:
                        module = self.fileUtils.filenameSlugify(codeContents["module"])
                        nextFolderPath = os.path.join(nextFolderPath, module)
                        self.fileUtils.createFolderIfNotExists(nextFolderPath)
                    self.downloadRecursivelyFromWebpackBin(codeContents, nextFolderPath)
            self.logger.info(f"WebpackBin Downloaded at: {self.codeFolderPath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadWebpackBin: {lineNumber}: {e}")


    def downloadRecursivelyFromWebpackBin(self, codeContents, codeFolderPath):
        try:
            self.logger.info(f"Inside codeFolderPath: {codeFolderPath}")
            if "children" in codeContents:
                for child in codeContents["children"]:
                    leaf = child["leaf"]
                    module = self.fileUtils.filenameSlugify(child["module"])
                    if not leaf:
                        self.logger.info("Creating Folder")
                        nextFolderPath = os.path.join(codeFolderPath, module)
                        self.fileUtils.createFolderIfNotExists(nextFolderPath)
                        self.downloadRecursivelyFromWebpackBin(child, nextFolderPath)
                    else:
                        fileContent = child["data"]["content"]
                        textFilePath = os.path.join(codeFolderPath, f"{module}")
                        self.logger.info(f"Creating file: {module}")
                        self.fileUtils.createTextFile(textFilePath, fileContent)

            if "leaf" in codeContents and codeContents["leaf"]:
                module = self.fileUtils.filenameSlugify(codeContents["module"])
                fileContent = codeContents["data"]["content"]
                textFilePath = os.path.join(codeFolderPath, f"{module}")
                self.logger.info(f"Creating file: {module}")
                self.fileUtils.createTextFile(textFilePath, fileContent)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CodeUtility:downloadRecursivelyFromWebpackBin: {lineNumber}: {e}")
