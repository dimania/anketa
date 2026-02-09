#
# Connfig settings file
# By default filename - config.py
# Please check directive - import config in programm
# version 0.4

# Api id getted from telegram from  https://my.telegram.org change to 60328456 by example
# You can use it over env vars. 
# Using  env vars have high priority
API_ID = <API_ID>

# Api hash getted from telegram from  https://my.telegram.org change to '860438hcoibwe37842y3dcnblkjh333' by example
# You can use it over env vars. 
# Using  env vars have high priority
API_HASH = <API_HASH> 

# Bot token getted form FatherBot change to '234324234:sdfkehf834608hlkcn38' by example  
# You can use it over env vars. 
# Using  env vars have high priority
BOT_TOKEN = <BOT_TOKEN>

# Telegram sesion string for user account, use it instead of sesssio file for more secure
# If not empty will be use, if empty will use session files below
# Also if set over env vars will be use with low priority
# Priority by SESSION_STRING if both setted
# By example over env vars
# Using  env vars have high priority
#SESSION_STRING_USER =  
# Telegram sesion string for bot account, use it instead of sesssio file for more secure
#SESSION_STRING_BOT =

# Set version client
system_version = "0.2-yorever"

#File name for bot connection - any filename
session_bot='nnmbot_session_bot'

# Name of bot in Telegram.
bot_name = 'anketa_bot'

#Admins array 
#Default admin user. 
# Example: Admin = admin_nickname1
Admin = 'admin_nickname'

# filename database - better use full path
db_name = 'database.db'  # database name, better set full path

# if use proxy set here 
# http required - use for set TelegramClient proxy parameter
proxies = {
  "http": "socks5://127.0.0.1:1080",
  "https": "socks5://127.0.0.1:1080",
}

#Log file name for write logs programm
logfile = 'nnmbot.log'

#Use proxy or d'not
use_proxy = 0 # if use proxy set to 1

#Set logging level for bot
#Possible value: NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL  
log_level='INFO'

# Set lang for dialogs. Possible values ru,en 
Lang='en'
