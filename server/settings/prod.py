from server.settings.common import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    "webull.paper.quanturtle.net",
    "webull.paper2.quanturtle.net",
    "webull.paper3.quanturtle.net",
    "webull.paper4.quanturtle.net",
    "webull.live.quanturtle.net",
    "webull.live2.quanturtle.net",
    "webull.quanturtle.net",
]

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
