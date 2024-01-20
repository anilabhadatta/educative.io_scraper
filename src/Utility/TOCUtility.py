import os
from src.Utility.FileUtility import FileUtility
import json

class TOCUtility:
    @staticmethod
    def serializeTocAndStore(courseTitle: str, courseUrl: str, courseBasePath: str, toc: list, topicUrlsList: list):

        def generateTopic(topicIndex, topicName, topicApiUrl, topicUrl):
            filenameSlugified = fileUtils.filenameSlugify(topicName)
            formatTopicName = f"{topicIndex:03}-{filenameSlugified}"
            topicRelativePath = f"{os.path.join(formatTopicName,formatTopicName)}"
            return (topicName, formatTopicName, topicApiUrl, topicUrl)
        
        fileUtils = FileUtility()
        tocArr = []
        idx = 0
        for item in toc:
            if type(item) is tuple: # level 1 is an topic
                tocArr.append(generateTopic(item[0], item[1], item[2], topicUrlsList[idx]))
                idx +=1
            elif type(item) is dict: # level 1 is a category
                category = {"category": item["category"], "topics": []}
                tocArr.append(category)
                for top in item["topics"]:
                    category["topics"].append(generateTopic(top[0], top[1], top[2], topicUrlsList[idx]))
                    idx += 1
        resultJson = json.dumps({"course": courseTitle, "url": courseUrl, "toc": tocArr}, indent= 4)
        fileUtils.createTextFile(os.path.join(courseBasePath, "__toc__.json"), resultJson)


        

