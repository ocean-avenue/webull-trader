# -*- coding: utf-8 -*-

# fetch account status from webull into database

def start(day=None):
    from datetime import date
    from sdk import webullsdk
    from common import utils, db

    paper = utils.is_paper_trading()

    if day == None:
        day = date.today()

    if webullsdk.login(paper=paper):

        account_data = webullsdk.get_account()

        db.save_webull_account(account_data, paper=paper, day=day)


if __name__ == "django.core.management.commands.shell":
    start()
