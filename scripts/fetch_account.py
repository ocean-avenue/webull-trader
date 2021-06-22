# -*- coding: utf-8 -*-

# fetch account status from webull into database

def start():
    from sdk import webullsdk
    from scripts import utils

    paper = utils.check_paper()
    webullsdk.login(paper=paper)

    account_data = webullsdk.get_account()

    utils.save_webull_account(account_data, paper=paper)


if __name__ == "django.core.management.commands.shell":
    start()
