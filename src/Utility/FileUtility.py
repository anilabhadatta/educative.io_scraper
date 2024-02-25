import img2pdf
import base64
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
    def createTopicHtml(topicFilePath, htmlPageData):
        with open(topicFilePath, "w+", encoding="utf-8") as fh:
            fh.write(htmlPageData)


    @staticmethod
    def createHtml2PdfFile(topicFilePath, pdfPageData):
        topicFilePath = topicFilePath[:-8] + "pdf"
        with open(topicFilePath, "wb") as pdfOutput:
            pdfPageData.write(pdfOutput)


    @staticmethod
    def createTextFile(textFilePath, data):
        with open(textFilePath, "w+", encoding="utf-8") as fh:
            fh.write(data)


    def createPngFile(self, topicFilePath, base64Img):
        imageData = base64.urlsafe_b64decode(base64Img)
        with open(topicFilePath, "wb") as fh:
            fh.write(imageData)


    def createPng2PdfFile(self, topicFilePath, base64Img):
        topicFilePath = topicFilePath[:-7] + "pdf"
        imageData = base64.urlsafe_b64decode(base64Img)
        imageIterable = [imageData]
        pdfBytes = img2pdf.convert(imageIterable)
        with open(topicFilePath, "wb") as pdfOutput:
            pdfOutput.write(pdfBytes)


    def getHtmlWithImage(self, base64Png, topicName):
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>{topicName}</title>
        </head>
        <body style="background-color: rgb(21 21 30); zoom: 80%">
            <div style="text-align: center">
                <img style="max-width: 100%; display: block; margin-left: auto; margin-right: auto;" src="data:image/png;base64,{base64Png}" alt="">
            </div>
        </body>
        </html>
        """