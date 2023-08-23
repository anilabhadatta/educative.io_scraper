import os


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
            os.mkdir(folderPath)
