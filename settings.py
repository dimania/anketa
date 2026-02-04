'''
 Telegram Bot for filter films from NNMCLUB channel
 version 0.6
 Module settings.py Set internal variables
 and constants, get global configs from file myconfig.py
'''
#
#!!!!!!!! Replace with you config file here !!!!!!!
# replace myconfig with config by example


import re
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
    global Lang
    global cursor
    global connection
    global ses_usr_str
    global ses_bot_str
    global all_questions 

    cursor = None
    connection = None

    try:
        system_version = config.system_version
        bot_name = config.bot_name
        admin_name = config.admin_name
        Channel_my = config.Channel_my
        db_name = config.db_name
        logfile = config.logfile
        use_proxy = config.use_proxy
        log_level = config.log_level
        Lang = config.Lang
        
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


