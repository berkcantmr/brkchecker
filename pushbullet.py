import requests


class Pushbullet:

    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.pushbullet.com/v2/pushes"

    def send_notification(self, title, body):
        headers = {
            "Access-Token": self.api_key,
            "Content-Type": "application/json"
        }
        data = {"type": "note", "title": title, "body": body}
        response = requests.post(self.url, headers=headers, json=data)
        if response.status_code == 200:
            print("Bildirim gönderildi!")
        else:
            print("Bildirim gönderilirken bir hata oluştu:", response.text)
