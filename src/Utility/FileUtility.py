import json
import os
import re
import shutil
import stat

from slugify import slugify


class FileUtility:
    def __init__(self):
        pass


    @staticmethod
    def checkIfDirectoryExists(dirPath):
        if os.path.isdir(dirPath):
            return True
        return False


    @staticmethod
    def checkIfFileExists(filePath):
        if os.path.exists(filePath):
            return True
        return False


    def createFolderIfNotExists(self, folderPath):
        if not self.checkIfDirectoryExists(folderPath):
            os.makedirs(folderPath)


    def deleteFileIfExists(self, filePath):
        if self.checkIfFileExists(filePath):
            os.remove(filePath)


    def deleteFolderIfExists(self, folderPath):
        if self.checkIfDirectoryExists(folderPath):
            def on_rm_error(func, path, exc_info):
                os.chmod(path, stat.S_IWRITE)
                os.unlink(path)


            shutil.rmtree(folderPath, onerror=on_rm_error)


    @staticmethod
    def loadTextFile(filePath):
        with open(filePath, "r") as f:
            lines = f.readlines()
            return [line.strip() for line in lines]


    @staticmethod
    def loadJsonFile(filePath):
        with open(filePath, "r") as f:
            return json.load(f)


    def replaceFilename(str):
        numDict = {':': ' ', '?': ' ', '|': ' ', '>': ' ', '<': ' ', '/': ' '}
        return numDict[str.group()]


    def filenameSlugify(self, filename):
        filename = slugify(filename, replacements=[['+', 'plus']]).replace("-", " ")
        return re.sub(r'[:?|></]', self.replaceFilename, filename)


    @staticmethod
    def createTopicHtml(htmlFilePath, htmlPageData):
        with open(htmlFilePath, "w+", encoding="utf-8") as fh:
            fh.write(htmlPageData)


    @staticmethod
    def createTextFile(textFilePath, data):
        with open(textFilePath, "w+", encoding="utf-8") as fh:
            fh.write(data)
