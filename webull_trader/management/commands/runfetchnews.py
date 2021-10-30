from datetime import datetime
from django.core.management.base import BaseCommand
from common import utils
from scripts import fetch_news


class Command(BaseCommand):
    help = 'run fetch stats data'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str)

    def handle(self, *args, **options):
        date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        print("[{}] Start fetch news job...".format(utils.get_now()))
        fetch_news.start(day=date)
        print("[{}] Done fetch news job!".format(utils.get_now()))