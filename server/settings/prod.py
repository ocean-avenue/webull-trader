from server.settings.common import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    "live1.webull.quanturtle.net",
    "live2.webull.quanturtle.net",
    "paper1.webull.quanturtle.net",
    "paper2.webull.quanturtle.net",
    "paper3.webull.quanturtle.net",
    "paper4.webull.quanturtle.net",
]

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'CONN_MAX_AGE': 60,
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
