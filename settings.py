'''
 Telegram Bot Anketing 
 version 0.1
 Module settings.py Set internal variables
 and constants, get global configs from file config.py
'''
#
#!!!!!!!! Replace with you config file here !!!!!!!
# replace myconfig with config by example

import os

#------------------------
import myconfig as cfg
#------------------------

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
report_logo = None
report_title = None
timeout_warning = True


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
        system_version = config.system_version
        bot_name = config.bot_name
        db_name = config.db_name
        logfile = config.logfile
        use_proxy = config.use_proxy
        log_level = config.log_level
        Builtin_admin = config.Builtin_admin
        report_logo = config.report_logo
        report_title = config.report_title
        def_report_logo = config.report_logo
        def_report_title = config.report_title
        timeout_warning = config.timeout_warning
        Lang = config.Lang

        if 'timeout_for_answer' in vars(config):
            TIMEOUT_FOR_ANSWER = config.timeout_for_answer

        # May be comment out in config.py
        if 'API_ID' in vars(config):
            api_id = config.API_ID
        else: api_id = os.environ.get("API_ID", None)

        if 'API_HASH' in vars(config):
            api_hash = config.API_HASH
        else: api_hash = os.environ.get("API_HASH", None)

        if 'BOT_TOKEN' in vars(config):
            mybot_token = config.BOT_TOKEN
        else: mybot_token = os.environ.get("BOT_TOKEN", None)

        if 'SESSION_STRING_BOT' in vars(config):
            ses_bot_str = config.SESSION_STRING_BOT 
        else: ses_bot_str = os.environ.get("SESSION_STRING_BOT", None)

        if not ses_bot_str: session_bot = config.session_bot 
    
        if use_proxy:
            proxies = config.proxies
        else:
            proxies = None

    except Exception as error:
        print(f"Error in config file: {error}")
        exit(-1)


