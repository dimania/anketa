"""Safe configuration template.

Secrets must be supplied through environment variables or an external secret
manager.  This file is also used by the Docker image, so it must remain valid
Python without local substitutions.
"""

import os


def _env(name, default=None):
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _int_env(name, default=None):
    value = _env(name)
    return int(value) if value is not None else default


#
# Config settings file
# By default filename - config.py
# Please check directive - import config in programm
# version 0.4

# Api id getted from telegram from  https://my.telegram.org change to 60328456 by example
# You can use it over env vars. 
# Using  env vars have high priority
API_ID = _int_env("API_ID")

# Api hash getted from telegram from  https://my.telegram.org change to '860438hcoibwe37842y3dcnblkjh333' by example
# You can use it over env vars. 
# Using  env vars have high priority
API_HASH = _env("API_HASH")

# Bot token getted form FatherBot change to '234324234:sdfkehf834608hlkcn38' by example  
# You can use it over env vars. 
# Using  env vars have high priority
BOT_TOKEN = _env("BOT_TOKEN")

# Telegram sesion string for user account, use it instead of sesssio file for more secure
# If not empty will be use, if empty will use session files below
# Also if set over env vars will be use with low priority
# Priority by SESSION_STRING if both setted
# By example over env vars
# Using  env vars have high priority
#SESSION_STRING_USER =  
# Telegram sesion string for bot account, use it instead of sesssio file for more secure
SESSION_STRING_BOT = _env("SESSION_STRING_BOT")

# Set version client
system_version = "0.2-yorever"

#File name for bot connection - any filename
session_bot = _env("SESSION_BOT", "nnmbot_session_bot")

# Name of bot in Telegram.
bot_name = 'anketa_bot'

#Admins array 
#Default admin user. 
# Example: Admin = admin_nickname1
Builtin_admin = _env("BUILTIN_ADMIN", "")
ADMIN_IDS = {
    int(value.strip())
    for value in _env("ADMIN_IDS", "").split(",")
    if value.strip()
}

# Runtime paths can be overridden by environment variables in containers.
db_name = _env("DB_NAME", "database.db")

# if use proxy set here 
# http required - use for set TelegramClient proxy parameter
proxies = {
  "http": "socks5://127.0.0.1:1080",
  "https": "socks5://127.0.0.1:1080",
}

# Log file name for write logs programm
logfile = _env("LOGFILE", "nnmbot.log")

#Report logo image file name for insert in report user
report_logo = 'logo.jpg'
report_title = 'Анкета'

#Use proxy or d'not
use_proxy = False # if use proxy set to 1

# Send warning for timeout answer to user  
timeout_warning = True

# Set timeout for answer one question
timeout_for_answer = 120

#Set logging level for bot
#Possible value: NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL  
log_level='INFO'

# Set lang for dialogs. Possible values ru,en 
# NOT USE NOW
Lang='en'
