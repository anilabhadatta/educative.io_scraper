import requests


class MailNotify:
    def __int__(self):
        pass

    def send_email(self, message):
        url = ""
        payload = {
            "toAddress": "",
            "title": "Educative Scraper Update",
            "message": f"{message}"
        }
        headers = {
            "content-type": "application/json",
        }
        # response = requests.request("POST", url, json=payload, headers=headers)
        # print(response.status_code)