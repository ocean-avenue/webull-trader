from server.settings.common import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    "webull.p1.quanturtle.net",
    "webull.p2.quanturtle.net",
    "webull.p3.quanturtle.net",
    "webull.p4.quanturtle.net",
    "webull.l1.quanturtle.net",
    "webull.l2.quanturtle.net",
]

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
