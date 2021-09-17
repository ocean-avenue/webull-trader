from server.settings.common import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    "live1.webull-trader.quanturtle.net",
    "live2.webull-trader.quanturtle.net",
    "paper1.webull-trader.quanturtle.net",
    "paper2.webull-trader.quanturtle.net",
    "paper3.webull-trader.quanturtle.net",
    "paper4.webull-trader.quanturtle.net",
]

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
