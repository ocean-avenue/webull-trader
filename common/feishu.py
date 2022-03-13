import requests
import json
from common import utils

WEBHOOK_URL = 'https://open.feishu.cn/open-apis/bot/v2/hook/dd21cfbb-19ad-4808-86c4-5c6e3bf0a5c3'


def send_message(content):
    title = f"[WEBULL]{utils.get_account_user_desc()} | {', '.join(utils.get_algo_type_tags())}"
    msg_body = {
        "msg_type": "post",
        "content": {
            "post": {
                "en_us": {
                    "title": title,
                    "content": [
                        [
                            {
                                "tag": "text",
                                "text": content,
                            },
                        ]
                    ]
                }
            }
        }
    }
    msg_str = json.dumps(msg_body)
    requests.post(WEBHOOK_URL, headers={
        'Content-Type': 'application/json'}, data=msg_str)
