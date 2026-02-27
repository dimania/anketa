#
# Configuration file foe Anketa bot
#

API_ID = 21832940
API_HASH = 'a498a3ea167b32bb857169fb54f9c16a'
BOT_TOKEN = '8519388431:AAHevru0lDJ7Bna4fuLXrNEd0N7Q0xDbH44'

#SESSION_STRING_USER = <SESSION STRING FOR USER>
#SESSION_STRING_BOT = <SESSION STRING FOR USER>

system_version = "0.1-nfb"
session_bot = 'session/nfb_session_bot'

# Name of bot - will be to switch on you bot for control database.
bot_name = 'QanswerSurvey_bot'
Builtin_admin = 'murhuhu'
db_name = 'data/database_anketa.db'
logfile = 'logs/anketa.log'

# http required - use for set TelegramClient proxy parameter
proxies = {
    "http": "socks5://192.168.110.100:1080",
    "https": "socks5://192.168.110.100:1080",
}

use_proxy = 0

# Set logging level for bot
log_level = 'INFO'


