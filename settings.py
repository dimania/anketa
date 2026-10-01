'''
 Telegram Bot Anketing 
 version 0.1
 Module settings.py Set internal variables
 and constants, get global configs from file config.py
'''
#
# Local deployments may provide myconfig.py; containers use the safe template
# config.py and receive secrets through environment variables.

import os

try:
    import myconfig as cfg
except ModuleNotFoundError:
    import config as cfg

#-----------------
# CONSTANTS
#

NO_MENU = 0
BASIC_MENU = 1
CUSER_MENU = 2
LIST_REC_IN_MSG = 20
RETRIES_DB_LOCK = 5
#Timeout for answer user in sec
TIMEOUT_FOR_ANSWER = 120
# Type of qestions: 
# simple - text answer
# select - multi selection dialog
# onlyone - select oly one answer from list
# header - Text and image before begin run anketa
# footer - Text and image after and anketa
# text - any text message in process (must not be repet same text)
# report - setting text Title and logo for user report in pdf file

#Define vars for index
SIMPLE = 0 
SELECT = 1
ONLYONE = 2
HEADER = 3
FOOTER = 4
TEXT = 5
REPORT = 6

TYPES_OF_QUESTONS = ["simple", "select", "onlyone","header","footer","text","report"]

api_id = None
api_hash = None
mybot_token = None
system_version = None
session_bot = None
bot_name = None
db_name = None
proxies = None
logfile = None
use_proxy = None
log_level = None
cursor = None
connection = None
ses_bot_str = None
type_questions = None
all_questions = None
Admins = {}
Builtin_admin = None
Admin_ids = set()
report_logo = None
report_title = None
timeout_warning = True
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_EXCEL_ROWS = 1000
MAX_EXCEL_COLUMNS = 100


def get_config(config=cfg):
    ''' set global variable from included config.py - import config directive'''
    global api_id
    global api_hash
    global mybot_token
    global system_version
    global session_bot
    global bot_name
    global admin_name
    global Channel_my
    global db_name
    global proxies
    global logfile
    global use_proxy
    global log_level
    global cursor
    global connection
    global ses_bot_str
    global all_questions
    global type_questions
    global Admins
    global Builtin_admin
    global Admin_ids
    global report_logo
    global report_title
    global def_report_logo
    global def_report_title
    global timeout_warning
    global TIMEOUT_FOR_ANSWER
    global Lang

    cursor = None
    connection = None

    try:
        # Environment variables always have precedence over the config module.
        def setting(name, default=None):
            value = os.environ.get(name)
            return value if value not in (None, "") else getattr(config, name, default)

        system_version = setting("SYSTEM_VERSION", config.system_version)
        bot_name = setting("BOT_NAME", config.bot_name)
        db_name = setting("DB_NAME", config.db_name)
        logfile = setting("LOGFILE", config.logfile)
        use_proxy = config.use_proxy
        log_level = setting("LOG_LEVEL", config.log_level)
        Builtin_admin = getattr(config, "Builtin_admin", None)
        configured_admin_ids = getattr(config, "ADMIN_IDS", set())
        report_logo = config.report_logo
        report_title = config.report_title
        def_report_logo = config.report_logo
        def_report_title = config.report_title
        timeout_warning = config.timeout_warning
        Lang = config.Lang

        if 'timeout_for_answer' in vars(config):
            TIMEOUT_FOR_ANSWER = config.timeout_for_answer

        raw_api_id = setting("API_ID")
        api_id = int(raw_api_id) if raw_api_id not in (None, "") else None
        api_hash = setting("API_HASH")
        mybot_token = setting("BOT_TOKEN")
        ses_bot_str = setting("SESSION_STRING_BOT")
        session_bot = setting("SESSION_BOT", getattr(config, "session_bot", None))

        raw_admin_ids = os.environ.get("ADMIN_IDS")
        if raw_admin_ids:
            configured_admin_ids = raw_admin_ids.split(",")
        Admin_ids = {int(value) for value in configured_admin_ids if str(value).strip()}

        if not Admin_ids:
            raise ValueError("ADMIN_IDS must be configured; username authorization is disabled")

        # Upload limits are intentionally conservative and can be overridden by env.
        max_upload = setting("MAX_UPLOAD_BYTES", "5242880")
        max_excel_rows = setting("MAX_EXCEL_ROWS", "1000")
        max_excel_columns = setting("MAX_EXCEL_COLUMNS", "100")
        globals()["MAX_UPLOAD_BYTES"] = int(max_upload)
        globals()["MAX_EXCEL_ROWS"] = int(max_excel_rows)
        globals()["MAX_EXCEL_COLUMNS"] = int(max_excel_columns)
    
        if use_proxy:
            proxies = config.proxies
        else:
            proxies = None

    except Exception as error:
        print(f"Error in config file: {error}")
        exit(-1)
