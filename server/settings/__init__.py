
try:
    from server.settings.local_settings import *
    print("Load from local settings...")
except:
    # if there's no local_settings specified, use prod settings
    from server.settings.prod import *
    print("No local settings found, load settings from prod...")
