from twilio.rest import Client
from sdk.config import TWLO_ACCOUNT_SID, TWLO_AUTH_TOKEN, TWLO_SENDER_NUMBER, TWLO_MESSAGE_MAX_LENGTH

client = None

def _send_message(message_body, receiver):

    global client

    if client == None:
        client = Client(TWLO_ACCOUNT_SID, TWLO_AUTH_TOKEN)

    client.messages.create(
        body=message_body, from_=TWLO_SENDER_NUMBER, to=receiver)


def send_message(messages, receiver="+14159395985"):

    message_body = ""
    for msg in messages:
        message_body = message_body + msg + "\n"
        if len(message_body) >= TWLO_MESSAGE_MAX_LENGTH:
            _send_message(message_body, receiver)
            message_body = ""
    if len(message_body) > 0:
        _send_message(message_body, receiver)