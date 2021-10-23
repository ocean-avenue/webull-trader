from sdk import twiliosdk
from common.utils import get_account_user_desc, get_algo_type_tags


def notify_message(message):
    twiliosdk.send_message([
        get_account_user_desc(),
        ", ".join(get_algo_type_tags()),
        message
    ])
