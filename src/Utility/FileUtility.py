import os
import shutil


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
            shutil.rmtree(folderPath)
