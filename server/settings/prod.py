from server.settings.common import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    "webull-trader-p1.quanturtle.net",
    "webull-trader-p2.quanturtle.net",
    "webull-trader-p3.quanturtle.net",
    "webull-trader-p4.quanturtle.net",
    "webull-trader-l1.quanturtle.net",
    "webull-trader-l2.quanturtle.net",
]

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
