'''
 Telegram Bot for Anketing 
 version 5
 Module anketa.py 
  
'''

#import io
from collections import defaultdict
import re
import logging
import asyncio
import os.path
import sys
#import gettext
import json
from datetime import datetime
import requests
from telethon import TelegramClient, events
from telethon.tl.types import  PeerChannel, PeerUser, UpdateNewMessage
from telethon.tl.custom import Button
from telethon import errors
from telethon.events import StopPropagation
from telethon.sessions import StringSession
import pandas as pd
import filetype
import docx
from fpdf import FPDF

#from requests.packages.urllib3.util.retry import Retry
# --------------------------------
import settings as sts
import dbmodule as dbm
# --------------------------------
#Glogal vars
bot = None

class PDF(FPDF):
    
    #def __init__(self):
    #    # Add ttf fonts
    #    self.add_font('DejaVu-Bold', '', r'font/DejaVuSansCondensed-Bold.ttf')
    #   self.add_font('DejaVu', '', r'font/DejaVuSansCondensed.ttf')

    def header(self):
        # Logo
        self.image('images/'+sts.report_logo, 5, 2, 20)
        # Arial bold 15
        self.add_font('DejaVu-Bold', '', r'font/DejaVuSansCondensed-Bold.ttf')
        self.add_font('DejaVu', '', r'font/DejaVuSansCondensed.ttf')

        self.set_font('DejaVu-Bold', '', 16)
        # Move to the right
        self.cell(80)
        # Title
        self.cell(30, 10, text=self.title, border=0, align='C')
        
        # Write date and time creation report
        self.set_font('DejaVu', '', 8)
        dt = datetime.now().strftime('%d.%m.%Y %H:%M')
        self.cell(75, 0, text=dt, border=0, align='R')
        # Line break
        self.ln(20)
        self.line(10, 30, 200, 30)
        self.ln(10)

    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        # Page number
        self.cell(0, 10, text=str(self.page_no()) + '/{nb}', border=0, align='C')

async def add_admins(event):
    ''' Select users for add to admins list
        event = bot event handled id
        level = user level for show menu exxtended or no
    '''
    id_user = event.query.user_id
    logging.debug(f"Create select users dialog for user {id_user}")
    
    buttons = [
    {
        "text":"👥 Выбор Админа",
        "request_users": {
            "request_id": 1,# button id
            "max_quantity": 5,
            "user_is_bot": False,
            "request_name": True,
            "request_username": True, 
        }
    }
    ]
    reply_markup = {"keyboard": [buttons], "resize_keyboard": True, "one_time_keyboard": True }
    payload = {
    "chat_id": id_user, # Id user to
    "text": "Нажмите кнопку 'Выбор Админа' чтобы добавть в список администраторов", 
    "reply_markup": json.dumps(reply_markup)
    }

    # Send selection user Button 
    url = f"https://api.telegram.org/bot{sts.mybot_token}/sendMessage"

    response = requests.post(url, data=payload, timeout = 30, proxies=sts.proxies)
    logging.debug(f"Rеsponse Select user button post:{response}\n")

    # hanled answer
    @bot.on(events.Raw(types=UpdateNewMessage))
    async def on_requested_peer_user(event_select):
        logging.debug(f"Get select user event:{event_select}")
        text_reply=''
        new_admins={}

        try:
            if event_select.message.action.peers[0].__class__.__name__ == "RequestedPeerUser":
                button_id = event_select.message.action.button_id
                if button_id == 1:
                    for peer in event_select.message.action.peers:
                        if peer.user_id in sts.Admins:
                        #if peer.user_id in sts.Admins.keys():
                           text_reply=text_reply+f"⚠️{peer.username} {peer.first_name} уже админ!\n"
                           continue
                        new_admins[int(peer.user_id)]=peer.username,peer.first_name

                    bot.remove_event_handler(on_requested_peer_user)
                    if new_admins:
                        logging.debug(f"Get selected users:{new_admins}")
                        # Add new admins in DB
                        async with dbm.DatabaseBot(sts.db_name) as db:
                            ret = await db.db_add_admins(new_admins)
                        if ret:
                            #Update current list of admins
                            sts.Admins.update(new_admins)
                            text_reply=text_reply+"🏁Администраторы добавлены🏁"
                        else:
                            text_reply="🏁Ошибка добавления админа🏁"
                    else:
                        text_reply=text_reply+"Некого добавить!"

                    reply_markup = { "remove_keyboard": True }
                    payload_remove_kb = {
                    "chat_id": id_user, # Id user to
                    "text": text_reply, 
                    "reply_markup": json.dumps(reply_markup)
                    }
                    response = requests.post(url, data=payload_remove_kb, timeout = 30, proxies=sts.proxies)
                    logging.debug(f"Rsponse Remove keyboard:{response}\n")
                    await create_admin_menu(0, event) 
                    
                    return 
        except Exception as error :
            logging.debug(f"It is not RequestedPeerUser message:{error}")
            return None

async def del_admins(event):
    ''' Delete admins form list
        event = bot event handled id
        level = user level for show menu exxtended or no
    '''
    
    logging.debug("Call del_admins() function")
    bdata_id='DEL_ADMIN_'
    button=[]
    i=0
    admin_name=''
    admin_nickname=''
    logging.debug(f"Len Admins: {len(sts.Admins)}")
   
    if len(sts.Admins) > 1:
        message="❌ Выберете админа для удаления:"        
        for admin_id, cur_admin in sts.Admins.items():
            if i == 0: 
                i=i+1
                continue
            bdata=bdata_id+str(admin_id)
            if cur_admin[1]:
                admin_name = cur_admin[1]
                if cur_admin[0]: admin_nickname = f'@{cur_admin[0]}'
            elif cur_admin[0]: 
                admin_name = cur_admin[0]
            else:
                admin_name ='Noname'

            button.append([ Button.inline(f'👮 {admin_name} {admin_nickname} ({admin_id})', bdata)])
            admin_nickname =''
    else:
           await event.respond("⚠️Нет админов для удаления.")
           await create_admin_menu(0,event)
           return False
    
    await event.respond(message, buttons=button)    
    return True

async def show_admins(event):
    ''' Show current admins
        event = bot event handled id
        level = user level for show menu exxtended or no
    '''
    Builtin_Admin='💂‍♂️'
    Simply_Admin='👮'

    i=True

    admin_name=''
    admin_nickname=''
    rstr='📃Cписок текущих Админов:\n\n'
    for admin_id, cur_admin in sts.Admins.items(): 
        if cur_admin[1]:
            admin_name = cur_admin[1]
            if cur_admin[0]: admin_nickname = f'@{cur_admin[0]}'
        elif cur_admin[0]: 
            admin_name = f'@{cur_admin[0]}'
        else:
            admin_name ='Noname'

        if i:
            rstr=rstr+f'{Builtin_Admin} {admin_name} {admin_nickname} ({admin_id})\n'
            i=False
            admin_nickname = ''
        else:
             rstr=rstr+f'{Simply_Admin} {admin_name} {admin_nickname} ({admin_id})\n'
             admin_nickname = ''

    await event.respond(rstr)
    await create_admin_menu(0, event)

async def check_nickname(username):
    res = {}
    try:
        # Пытаемся получить информацию о пользователе/канале по нику
        entity = await bot.get_entity(username)
        #logging.debug(f"Nickname [{username}] ok. Object type is: {type(entity).__name__}")
        logging.debug(f"User ID: {entity.id}")
        logging.debug(f"First Name: {entity.first_name}")
        logging.debug(f"Username-nickname: {entity.username}")
        res[entity.id]=entity.username,entity.first_name
        return res
    except ValueError:
        # Возникает, если Telethon не нашел сущность (обычно если ника нет)
        logging.debug(f"Nickname [{username}] not found ")
        return False
    except Exception as e:
        logging.debug(f"Error check Nickname [{username}] {e}")
        return False

async def get_excel_data(fname, sheet_name=0):
    """
    Reads data from an Excel file into a pandas DataFrame.
    sheet_name can be an integer (0 for the first sheet) or a string ('Sheet1').
    """
    try:
        df = pd.read_excel(fname, sheet_name=sheet_name, header=None )
        # Convert the DataFrame to dict
        res=df.to_dict(orient='split', index=False) 
        return res
    except Exception as e:
        logging.warning(f"Error reading Excel file: {e}")
        return False

async def get_new_questions(fname):
    '''
    Docstring для get_new_questions
    Get new questions from file txt,docx,xls,xlsx and return list
    :param filename: file with questions
    '''
    #root,ext = os.path.splitext(fname)
    kind = filetype.guess(fname)
    
    #logging.debug(f'File extension: {kind.extension}')
    #logging.debug(f'File MIME type: {kind.mime}')

    if kind is None:
        logging.debug(f'Cannot guess file type filename: {fname}!')
        return False,False,False
    elif kind.extension == 'xlsx' or kind.extension == 'xls':
        text_content = await get_excel_data(fname)
        logging.debug(f'Xlsx or xls content is:{text_content}')
    
    if not text_content:
        return False,False,False
    
    qlist={}
    tlist={}
    val=[]
    warnings=''
    id4t=1
    sts.report_logo = sts.def_report_logo
    sts.report_title = sts.def_report_title
    for item in text_content['data']:
        #item - one question and variants answers if exist
        type_current_qusetion=item.pop(0)
        logging.debug(f'if {type_current_qusetion} not in {sts.TYPES_OF_QUESTONS}')
        if type_current_qusetion not in sts.TYPES_OF_QUESTONS:
            #raise ValueError("Type of question invald!")
            return False,False,False             
        logging.debug(f'Item content is:{item}')
        nan_list=pd.isna(item)
        logging.debug(f'Item content is:{nan_list}')
        i=False
        # variants answer to list values dict        
        for x, y in zip(item,nan_list):
            logging.debug(f'i_X_Y:{i},{x},{y}')
            if not y and i:
                val.append(x) 
            i=True
        #Test on exist image files
        if (type_current_qusetion == sts.TYPES_OF_QUESTONS[sts.HEADER] or \
           type_current_qusetion == sts.TYPES_OF_QUESTONS[sts.FOOTER] or \
           type_current_qusetion == sts.TYPES_OF_QUESTONS[sts.REPORT]) and \
           val:
            if await exist_file(val[0]):
                # Set user report settings else use defaut
                if type_current_qusetion == sts.TYPES_OF_QUESTONS[sts.REPORT]:
                    sts.report_title = item[0]
                    sts.report_logo = val[0]
                    logging.debug(f"Set report title = {sts.report_title} report logo = {sts.report_logo}")
                    #continue
            else:
                logging.warning(f"Warning file or url {val[0]} not exist")
                warnings=warnings+f"⚠️Внимание! файл или URL  {val[0]} не существует!\nБудет использован файл по умолчанию.\n"   
                val[0]=''
        if type_current_qusetion == sts.TYPES_OF_QUESTONS[sts.TEXT]: # Add some id to text for repeat in dict key            
            item[0]=f"ID4T_{id4t}_"+item[0]
            #val[0]=''
            id4t = id4t + 1

            
            
        qlist[item[0]]=val
        tlist[item[0]]=type_current_qusetion
        val=[]
        logging.debug(f'\ntlist={tlist}\nqlist={qlist}\nwarnings={warnings}')
    
    return tlist,qlist,warnings

async def create_admin_menu(level, event):
    ''' Create Admin menu '''
    logging.debug("Create menu buttons")
    keyboard = [
        [
            Button.inline("📈 Показать статистику", b"/am_stats")
        ],
        [
            Button.inline("📃 Пройти анкетирование", b"/am_anketa")
        ],
        [
            Button.inline("📊 Получить результаты", b"/am_answers")
        ],
        [
            Button.inline("📑 Текущие вопросы", b"/am_show_questions")
        ],
        [
            Button.inline("⬆️ Загрузить новые вопросы", b"/am_questions")
        ]
        ,
        [
            Button.inline("📰 Загрузить изображения", b"/am_get_img")
        ]
        ,
        [
            Button.inline("👮‍♂️ Добавть администратора", b"/am_add_admins")
        ]
        ,
        [
            Button.inline("🙅‍♂️ Удалить администратора", b"/am_del_admins")
        ]
        ,
        [
            Button.inline("🕵️ Просмотреть всех админов", b"/am_show_admins")
        ]
    ]
    #clear old message
    await event.delete()
    # send menu
    await event.respond("**☣ Режим Администратора:**", parse_mode='md', buttons=keyboard)

async def show_stats(event):
    '''
    show statistics for users
    '''
    logging.debug("Call show_stats() function")

    async with dbm.DatabaseBot(sts.db_name) as db:
        rows = await db.get_info_by_users()
    if not rows:
        await event.respond("🚷На данный момент нет информаци.\nЕще никто не прошел опрос.")
        return False

    strstat=f"🔢 Ответили на вопросы: {len(rows)}\n\n👥 Список прошедших опрос:\n\n"

    for row in rows:
        #dt = datetime.strptime(dict(row).get('date'),'%Y-%m-%d %H:%M:%S.%f')
        #strstat=strstat+f"{dict(row).get('name_user')} { dt.strftime('%d.%m.%y %H:%M') }\n"
        strstat=strstat+f"{dict(row).get('name_user')}\n"

    await event.respond(strstat)
  
    return True 

async def test_send_report(event):# USE for test create report excel file
    '''
    send Answers DB to Admin (load results)
    '''
    logging.debug("Call send_answ_db() function")

    dt = datetime.now().strftime('%d%m%Y_%H%M%S')
    
    fname = f"reports/report_{dt}.xlsx"
    logging.debug(f"Gen filename: {fname}")
    res = await gen_excel(fname)
    return True

async def send_report(event):
    '''
    send Answers DB to Admin (load results)
    '''
    logging.debug("Call send_answ_db() function")

    dt = datetime.now().strftime('%d%m%Y_%H%M%S')
    
    fname = f"reports/report_{dt}.xlsx"
    logging.debug(f"Gen filename: {fname}")
    res = await gen_excel(fname)
    if res:
        message="📊 Ваш отчет"
        await bot.send_file( event.query.user_id, fname, caption=message, parse_mode="html" ) 
        await asyncio.sleep(3) # Delay for user after send report and show menu
        return True
    else:
        await event.respond("🚷На данный момент нет информаци для отчета.\nЕще никто не прошел опрос.")
        return False

async def set_dataframe_sheet1(rows):
    '''
    Ctreate dataframe for Sheet1
    Colums is: name_user, nick_user, question,  answer_user, date, time
    rows: raw data from db
    '''
    data=defaultdict(list)
    lenq=len(all_questions)
    # Get name_user, nick_user, question, answer_user, date
    for row in rows:
        data['name_user'].append(dict(row).get('name_user'))       
        data['nick_user'].append(dict(row).get('nick_user'))
        index=int(dict(row).get('question_id'))
        #data['question'].append(all_questions[index-1])
        key_q=list(all_questions)[index-1]
        data['question'].append(key_q)        
        answer_cur=dict(row).get('answer_user')
        if all_questions.get(key_q):
            i=False
            for variant in answer_cur.split(','): #FIXME HERE
                logging.info(f"DF1 VARIANT:\nvariant({i})={variant}")
                data['answer_user'].append(all_questions.get(key_q)[int(variant)-1])
                if i:
                    data['name_user'].append('')
                    data['nick_user'].append('')
                    data['question'].append('')
                    data['date'].append('')
                    data['time'].append('')
                i=True
        else: 
            data['answer_user'].append(answer_cur)
            
        #2024-03-03 11:46:05.488155
        dt = datetime.strptime(dict(row).get('date'),'%Y-%m-%d %H:%M:%S.%f')
        date = dt.strftime('%d.%m.%Y')
        time = dt.strftime('%H:%M')
        data['date'].append(date)
        data['time'].append(time)
    logging.info(f"DF1 Results gen excel:\ndata:{data}")

    return data

async def set_dataframe_sheet2(rows):
    '''
    Ctreate dataframe for Sheet2
    Colums is: date, time, name_user, nick_user, question1, question2 ...
    rows: raw data from db
    '''
    global_row=0
    variant_row=0
    data=defaultdict(list)
    # Get name_user, nick_user, question, answer_user, date
    for row in rows:
        len_row = len(row)
        logging.info(f"DF2 LEN:\nlen={len_row}")
        if dict(row).get('name_user') not in data['name_user']:
            data['name_user'].append(dict(row).get('name_user'))       
            data['nick_user'].append(dict(row).get('nick_user'))
            #2024-03-03 11:46:05.488155
            dt = datetime.strptime(dict(row).get('date'),'%Y-%m-%d %H:%M:%S.%f')
            date = dt.strftime('%d.%m.%Y')
            time = dt.strftime('%H:%M')
            data['date'].append(date)
            data['time'].append(time)
            global_row = global_row + variant_row
            logging.info(f"DF2 VARIANT:\nGlobal_row={global_row} Question={key_q} variant({i})={variant}")
        
        index=int(dict(row).get('question_id'))
        #data['question'].append(all_questions[index-1])
        key_q=list(all_questions)[index-1]
        answer_cur=dict(row).get('answer_user')        
        #logging.info(f"DF2 ALL Q: Question={key_q}")

        if all_questions.get(key_q):
            i=False
            #variant_row = variant_row + 1 
            for variant in answer_cur.split(','): #FIXME HERE
                logging.info(f"DF2 VARIANT:\nGlobal_row={global_row} Question={key_q} variant({i})={variant}")
                data[key_q].insert(global_row,all_questions.get(key_q)[int(variant)-1])
                if i:
                    data['name_user'].append(' ')       
                    data['nick_user'].append(' ')        
                    data['date'].append(' ')
                    data['time'].append(' ')
                    j=0
                    while j != len_row:
                        if j != index-1:
                            key_q_tmp=list(all_questions)[j]
                            #if not data[key_q_tmp]:
                            data[key_q_tmp].append(' ')
                        j=j+1
                variant_row = variant_row + 1
                i=True
            continue    
        else: 
            #data[key_q].append(answer_cur)
            data[key_q].insert(global_row,answer_cur)
            logging.info(f"\nDF2 global_row:{global_row}")

        
    logging.info(f"DF2 Results gen excel:\ndata:{data}")
    return data

async def new_gen_excel(filename):
    '''
    Generate excel table
    '''
    async with dbm.DatabaseBot(sts.db_name) as db:
        rows = await db.get_info_for_report()
    if not rows:
        return False

    # Get name_user, nick_user, question, answer_user, date
    data = await set_dataframe_sheet1(rows)
    data_ws2 = await set_dataframe_sheet2(rows)
    df = pd.DataFrame(data)
    #logging.info(f"Results gen excel: ws2: {data_ws2}")
    df1 = pd.DataFrame(data_ws2)

    # Order the columns if necessary.
    #df = df[["name_user", "nick_user", "question", "answer_user", "date", "time" ]]
    #sort_list_ws2=["date", "time", "name_user", "nick_user"]
    #sort_list_ws2.extend(key_q)
    #logging.info(f"Results gen excel: sort: {sort_list_ws2}")
    #df1 = df1[["date", "time", "name_user", "nick_user", ]] # "question", "answer_user", 

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter(filename, engine="xlsxwriter")

    # Write the dataframe data to XlsxWriter. Turn off the default header and
    # index and skip one row to allow us to insert a user defined header.
    df1.to_excel(writer, sheet_name="По вопросам", startrow=1, header=False, index=False)
    df.to_excel(writer, sheet_name="По пользователям", startrow=1, header=False, index=False)
    # Get the xlsxwriter workbook and worksheet objects.
    #workbook = writer.book
    worksheet = writer.sheets["По вопросам"]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df1.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": column} for column in df1.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)
    # Close the Pandas Excel writer and output the Excel file.
    worksheet = writer.sheets["По пользователям"]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": column} for column in df.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)

   
    writer.close()
    
    return True

async def gen_excel(filename):
    '''
    Generate excel table
    '''
    data={}
    data['name_user']=[]
    data['nick_user']=[]
    data['question']=[]
    data['answer_user']=[]
    data['date']=[]
    data['time']=[]

    data_ws2={}
    data_ws2['date']=[]
    data_ws2['time']=[]
    data_ws2['name_user']=[]
    data_ws2['nick_user']=[]
   

    data=defaultdict(list)
    data_ws2=defaultdict(list)
    
    async with dbm.DatabaseBot(sts.db_name) as db:
        rows = await db.get_info_for_report()
    if not rows:
        return False

    # Get name_user, nick_user, question, answer_user, date
    for row in rows:
        data['name_user'].append(dict(row).get('name_user'))       
        data['nick_user'].append(dict(row).get('nick_user'))
        index=int(dict(row).get('question_id'))
        #data['question'].append(all_questions[index-1])
        key_q=list(all_questions)[index-1]
        data['question'].append(key_q)        
        answer_cur=dict(row).get('answer_user')
        logging.debug(f"Results gen excel: answer_cur:{answer_cur} all_questions.get(key_q):{all_questions.get(key_q)}")
        if all_questions.get(key_q):
            list_answer=[]
            for variant in answer_cur.split(','): #FIXME HERE
                list_answer.append(all_questions.get(key_q)[int(variant)-1])

            data['answer_user'].append(', '.join(list_answer))
            data_ws2[key_q].append(', '.join(list_answer))
        else: 
            data['answer_user'].append(answer_cur)
            data_ws2[key_q].append(answer_cur)
            
        #2024-03-03 11:46:05.488155
        dt = datetime.strptime(dict(row).get('date'),'%Y-%m-%d %H:%M:%S.%f')
        date = dt.strftime('%d.%m.%Y')
        time = dt.strftime('%H:%M')
        data['date'].append(date)
        data['time'].append(time)
        if dict(row).get('name_user') not in data_ws2['name_user']:
            data_ws2['name_user'].append(dict(row).get('name_user'))       
            data_ws2['nick_user'].append(dict(row).get('nick_user'))        
            data_ws2['date'].append(date)
            data_ws2['time'].append(time)
        else:
            continue
    logging.info(f"Results gen excel: {data}")
    df = pd.DataFrame(data)
    logging.info(f"Results gen excel: ws2: {data_ws2}")
    df1 = pd.DataFrame(data_ws2)

    # Order the columns if necessary.
    #df = df[["name_user", "nick_user", "question", "answer_user", "date", "time" ]]
    #sort_list_ws2=["date", "time", "name_user", "nick_user"]
    #sort_list_ws2.extend(key_q)
    #logging.info(f"Results gen excel: sort: {sort_list_ws2}")
    #df1 = df1[["date", "time", "name_user", "nick_user", ]] # "question", "answer_user", 

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter(filename, engine="xlsxwriter")

    # Write the dataframe data to XlsxWriter. Turn off the default header and
    # index and skip one row to allow us to insert a user defined header.
    df1.to_excel(writer, sheet_name="По вопросам", startrow=1, header=False, index=False)
    df.to_excel(writer, sheet_name="По пользователям", startrow=1, header=False, index=False)
    # Get the xlsxwriter workbook and worksheet objects.
    #workbook = writer.book
    worksheet = writer.sheets["По вопросам"]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df1.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": column} for column in df1.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)
    # Close the Pandas Excel writer and output the Excel file.
    worksheet = writer.sheets["По пользователям"]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": column} for column in df.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)

   
    writer.close()
    
    return True

async def gen_pdf(answers, fname):
    '''
    Generate pdf file

    answers: dict answers all users
    fname:   filename for report
    '''
    # Create an instance of the FPDF class (portrait, millimeters, A4 format by default)
    pdf = PDF()
    pdf.set_title(sts.report_title)
    pdf.alias_nb_pages()
    # Add a page
    pdf.add_page()
    #pdf.add_font('DejaVu', '', r'font/DejaVuSansCondensed.ttf')
    #pdf.add_font('DejaVu-Bold', '', r'font/DejaVuSansCondensed-Bold.ttf')

    i=1
    j=1
    for qst in all_questions:
        # write question
        if type_questions.get(qst) == sts.TYPES_OF_QUESTONS[0] or \
           type_questions.get(qst) == sts.TYPES_OF_QUESTONS[1] or \
           type_questions.get(qst) == sts.TYPES_OF_QUESTONS[2]:
            message = f"{j}. {qst}"
            pdf.set_font('DejaVu-Bold', '', 16)
            pdf.set_left_margin(10)
            pdf.write(text=message)
            pdf.ln(10)
            pdf.set_font('DejaVu', '', 14)
            j=j+1
        # write answers    
        if type_questions.get(qst) == sts.TYPES_OF_QUESTONS[1] or \
           type_questions.get(qst) == sts.TYPES_OF_QUESTONS[2]: # select or onlyone
            for cur_var in answers[i]:
                ans=all_questions.get(qst)[int(cur_var)-1]
                pdf.set_left_margin(17)
                pdf.write(text=str(ans))
                pdf.ln(10)
        elif type_questions.get(qst) == sts.TYPES_OF_QUESTONS[0]: #simple        
            ans = str(answers[i][0])
            pdf.set_left_margin(17)
            pdf.write(text=ans)
            pdf.ln(10)
        i=i+1  
    # Save the PDF to a file 
    pdf.output(fname)
    logging.info(f"PDF generated successfully as {fname}")

async def get_image(event_bot):
    '''
    get and load image, logo, etc...
    '''
    logging.debug("Call get_image() function")
    fmsg=''
    support_img=['jpeg','jpg','gif','png','webp']
    all_entries = os.listdir('images/')
    for file in all_entries:
        fmsg=fmsg+file+'\n'

    await event_bot.respond(\
        f"Сейчас загружены следующие файлы:\n{fmsg}\n" \
        "📎 Загрузите файл с изображнием.\n\n" \
        "Поддержиаются следующие типы файлов:\n" \
        "jpeg, jpg, gif, png, webp размером не более 5МБ")

    @bot.on(events.NewMessage())
    async def bot_handler_f_bot(event):
        #logging.debug(f"Get NewMessage event_bot: {event}")      
        if event.message.document:
            download_path = await event.message.download_media(file="images/") 
            logging.info(f'File with questions saved to: {download_path}')                                   
            kind = filetype.guess(download_path)
            if kind is None:
                logging.debug(f'Cannot guess file type filename: {download_path}!')
                message="⚠️Тип файла не определен, попробуйте другой файл!"
                os.remove(download_path)                
            elif kind.extension not in support_img:
                os.remove(download_path)
                message="⚠️ Данный тип файла не поддерживается, попробуйте другой файл!"
            else:
                message=f"Данные загружены в бот.\n Имя згруженного файла: {download_path}"
            await event.respond(message)
            bot.remove_event_handler(bot_handler_f_bot)
            await create_admin_menu(0, event_bot)

async def get_qusetion_data(event_bot):
    '''
    get and load questions to DB Questions
    '''
    logging.debug("Call get_qusetion_data() function")
    
    await event_bot.respond(\
    "📎 Загрузите файл с вопросами.\n\n" \
    #"Поддержиаются следующие типы файлов:\n" \
    #"🔹Текстовый файл (txt) по одному вопросу на строке\n" \
    #"🔹MS Word файл (docx) по одному вопросу на строке\n" \
    "MS Excel файл (xls,xlsx) заполненнный согласно шаблона\n"
    #" по одному вопросу в ячейке в первой колонке\n" \
    #"🔹варианты ответов в следующих за вопросом колонках\n" \
    #"🔹если нет варианта ответа - ответ вводит опрашиваемый\n" \
    #"⚠️ Старый формат MS word (doc) не поддерживается!\n" \
    "\n♨️ Текущие вопросы и ответы будут удалены!")

    @bot.on(events.NewMessage())
    async def bot_handler_f_bot(event):
        #logging.debug(f"Get NewMessage event_bot: {event}")      
        if event.message.document:
            download_path = await event.message.download_media(file="questionfiles/") 
            logging.info(f'File with questions saved to: {download_path}')                                   
            #with open(download_path, 'r', encoding="utf-8") as file:
            #    new_questions = [line.strip() for line in file.readlines()]
            new_type_questions, new_questions, warnings = await get_new_questions(download_path)
            if not new_questions:
                await event_bot.respond("⚠️Неверные данные, проверьте файл с вопросами!")
                bot.remove_event_handler(bot_handler_f_bot)
                await create_admin_menu(0, event_bot)
                return False
            all_questions.clear()
            type_questions.clear()   
            all_questions.update(new_questions)
            type_questions.update(new_type_questions)
            logging.debug(f'New all_questions: {all_questions}')
            logging.debug(f'New type_questions: {type_questions}')
            async with dbm.DatabaseBot(sts.db_name) as db:
                await db.db_rewrite_new_questions(all_questions,type_questions)

            await event.respond("Данные загружены в бот.")
            if warnings:
                await event.respond(warnings)
            bot.remove_event_handler(bot_handler_f_bot)
            await create_admin_menu(0, event_bot)
    
async def check_user_run_anketa(id_user, event_bot, menu):
    '''
    Test user already answer or not
    and continue
    '''    
    async with dbm.DatabaseBot(sts.db_name) as db:
        res = await db.db_exist_id_user(id_user)
    
    logging.info(f"Exist_id_user: {res}")

    # if user already answer     
    if res:
       #await event_bot.respond(f"Вы уже отвечали на вопросы.\n Желаете пройти опрос снова?\n Предыдущие ответы будут потяряны.\n")
       keyboard = [ Button.inline("Да", b"/yes"),Button.inline("Нет", b"/no") ]
       await event_bot.respond("⚠️Вы уже отвечали на вопросы.\nЖелаете пройти опрос снова?\n♨️Предыдущие ответы будут потеряны.\n", parse_mode='md', buttons=keyboard)
      
       @bot.on(events.CallbackQuery())
       async def callback_yn(event):            
            button_data = event.data.decode()
            logging.info(f"Callback yes/no: {button_data}")
            #await event.delete()
            if button_data == '/no':
                await event_bot.respond("До свидания.\n\n")
                bot.remove_event_handler(callback_yn)                
            elif button_data == '/yes': 
                async with dbm.DatabaseBot(sts.db_name) as db:
                    await db.db_del_user_answers(id_user)
                bot.remove_event_handler(callback_yn)
                await run_anketa(id_user, event_bot, menu)                                      
            return 0
    else:
        await run_anketa(id_user, event_bot, menu)       
        return 2

async def simple_conversation(id_user, event_bot, question_number, question_id, cur_question):
    '''
    simple_conversation - Dialog for simple question 
    only text filed
    
    :param id_user: dialog for telegram user - id_user
    :param event_bot: parent entity
    :param question_number: number of question for count
    :param question_id: index in dict question
    :param cur_question: current question
    '''
    answers=defaultdict(list)

    async with bot.conversation(id_user) as conv:
        def my_press_event(id_user):
            return events.CallbackQuery(func=lambda e: e.sender_id == id_user) #FIXME Need or not use pattern for get button?
        try:
            await conv.send_message(f"Вопрос {question_number}:\n{cur_question}")
            #WAIT ANSWER SIMLPE HERE
            response = await conv.get_response(timeout=sts.TIMEOUT_FOR_ANSWER)
            resp_text = response.text
            logging.info(f"Get respond text: {question_id} / {resp_text}")
            answers[question_id+1].append(resp_text)
        except TimeoutError as error:
            logging.debug(f"Get timeout {sts.TIMEOUT_FOR_ANSWER} sec for user {id_user} on answer {cur_question}\nOriginal error:{error}")
            await conv.send_message(f"⚠️Отведенное время {sts.TIMEOUT_FOR_ANSWER} секунд на ответ истекло.\n"\
                                    "Результаты не будут сохранены.\n"\
                                    "Пожалуйста пройдите опрос заново.\n"\
                                    "Для этого  в ≡Меню выберете Старт\n")
            conv.cancel()        
            return False
        
        conv.cancel()
        return answers      
    
async def onlyone_conversation(id_user, event_bot, question_number, question_id, cur_question):
    '''
    onlyone_conversation - Dialog for select only one option 
    :param id_user: dialog for telegram user - id_user
    :param event_bot: parent entity
    :param question_number: number of question for count
    :param question_id: index in dict question
    :param cur_question: current question
    '''
    sender = await event_bot.get_sender()
    sender_id = sender.id
    #sender_id = await event_bot.get_sender().id
    button=[]
    bdata=''
    answ_v=[]
    answers=defaultdict(list)

    async with bot.conversation(id_user) as conv:
        def my_press_event(id_user):
            return events.CallbackQuery(func=lambda e: e.sender_id == id_user) #FIXME Need or not use pattern for get button?
        try:
            button.clear()
            str_qst=f"Вопрос {question_number}:\n{cur_question}"
            v=1
            for variant in all_questions.get(cur_question):
                bdata=f'VARIANT_{question_id}_{v}'
                button.append([Button.inline(f'🔹 {variant}', bdata)])   
                v=v+1
            await conv.send_message(str_qst, buttons=button)            
            #Нandle respond
            handle = conv.wait_event(my_press_event(sender_id),timeout=sts.TIMEOUT_FOR_ANSWER) #FIXME Need or not use pattern for get button?
            event_res = await handle 
            button_pressed = event_res.data.decode('utf-8')
            answ_v = button_pressed.replace('VARIANT_', '').split('_')
            logging.info(f"Get respond button text:\n{question_id}\n{button_pressed}\n{answ_v}")
            answers[question_id+1].append(answ_v[1])
        except TimeoutError as error:
            logging.debug(f"Get timeout {sts.TIMEOUT_FOR_ANSWER} sec for user {id_user} on answer {cur_question}\nOriginal error:{error}")
            await conv.send_message(f"⚠️Отведенное время {sts.TIMEOUT_FOR_ANSWER} секунд на ответ истекло.\n"\
                                    "Результаты не будут сохранены.\n"\
                                    "Пожалуйста пройдите опрос заново.\n"\
                                    "Для этого  в ≡Меню выберете Старт\n")
            conv.cancel()
            return False
        
    conv.cancel()        
    return answers      

async def select_conversation(id_user, event_bot, question_number, question_id, cur_question):
    '''
    select_conversation - Dialog for multi select option 
    :param id_user: dialog for telegram user - id_user
    :param event_bot: parent entity
    :param question_number: number of question for count
    :param question_id: index in dict question
    :param cur_question: current question
    '''
    sender = await event_bot.get_sender()
    sender_id = sender.id
    #sender_id = await event_bot.get_sender().id
    button=[]
    bdata=''
    answ_v=[]
    answers=defaultdict(list)

    async with bot.conversation(id_user) as conv:
        def my_press_event(id_user):
            return events.CallbackQuery(func=lambda e: e.sender_id == id_user) #FIXME Need or not use pattern for get button?
        try:
            #sender_id = await event_bot.get_sender().id
            sender = await event_bot.get_sender()
            sender_id = sender.id
            button.clear()
            str_qst=f"Вопрос {question_number}:\n{cur_question}"
            v=1
            for variant in all_questions.get(cur_question):
                bdata=f'VARIANT_{question_id}_{v}'
                button.append([ Button.inline(f'🔘 {variant}', bdata)])
                v=v+1           
            await conv.send_message(str_qst, buttons=button)
            while True:
                #Нandle respond
                handle = conv.wait_event(my_press_event(sender_id),timeout=sts.TIMEOUT_FOR_ANSWER) #FIXME Need or not use pattern for get button?
                event_res = await handle 
                button_pressed = event_res.data.decode('utf-8')                
                if button_pressed.find('ANSWER_') == 0:
                    answers[question_id+1].sort() 
                    #TODO check for not null answers               
                    break
                answ_v = button_pressed.replace('VARIANT_', '').split('_')
                logging.info(f"Get respond button text: {question_id} : {button_pressed} : {answ_v}")

                if answ_v[1] in answers[question_id+1]: # FIXME XZ!!!!! was answ_v[2]
                    answers[question_id+1].remove(answ_v[1])
                else:   
                    answers[question_id+1].append(answ_v[1])

                button.clear()
                i=1
                for variant in all_questions.get(cur_question):
                    bdata=f'VARIANT_{question_id}_{i}'
                    if str(i) in answers[question_id+1]:
                        emoji='🟢'
                    else:
                        emoji='🔘'
                    button.append([ Button.inline(f'{emoji} {variant}', bdata)])
                    i=i+1
                
                bdata=f'ANSWER_{question_id}'
                button.append([ Button.inline('Ответить', bdata)])
                await bot.edit_message(event_res.query.user_id, event_res.query.msg_id,str_qst, buttons=button)
        except TimeoutError as error:
            logging.debug(f"Get timeout {sts.TIMEOUT_FOR_ANSWER} sec for user {id_user} on answer {cur_question}\nOriginal error:{error}")
            await conv.send_message(f"⚠️Отведенное время {sts.TIMEOUT_FOR_ANSWER} секунд на ответ истекло.\n"\
                                    "Результаты не будут сохранены.\n"\
                                    "Пожалуйста пройдите опрос заново.\n"\
                                    "Для этого  в ≡Меню выберете Старт\n")
            conv.cancel()
            return False

    conv.cancel()            
    return answers    

async def exist_file(path_to_file):
    '''
    Test for exist file or url
    '''
    if os.path.isfile('images/'+path_to_file):
        return 'images/'+path_to_file
    
    try:
        # Use HEAD request to check for existence without downloading content
        response = requests.head(path_to_file, timeout=5)
        # 200-299 status codes indicate success
        if 200 <= response.status_code <= 300:
            return path_to_file
    except:
        # Error get url
        return False
    
async def run_anketa(id_user, event_bot, menu):
    '''
    run main process for anketting
    '''
    user_ent = await bot.get_entity(id_user)
    nickname = user_ent.username
    first_name = user_ent.first_name
    if not nickname:
        nickname = first_name

    question_id=0
    question_number=1
    path_to_file=''
    answers=defaultdict(list)
    res=defaultdict(list)
    
    logging.debug(f"RUN_ANKETA: user_ent={user_ent}\nnickname={nickname}\nfirstname={first_name}\n")

    if sts.timeout_warning:
        await event_bot.respond(f"⚠️На каждый ответ отводится {sts.TIMEOUT_FOR_ANSWER} секунд.\n\n")
    #Show Header
    for cur_question,type in type_questions.items():
        if type == sts.TYPES_OF_QUESTONS[sts.HEADER]: # header
            if all_questions[cur_question]:
                path_to_file = await exist_file(all_questions[cur_question][0])
            if path_to_file:
                await bot.send_file(id_user,file=path_to_file, caption=cur_question, parse_mode="html")
                path_to_file=''                           
            else:
                await bot.send_message(id_user, cur_question, parse_mode="html")
            break
    #Show question 
    for cur_question,variants  in all_questions.items():
        if type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.SIMPLE]: # simple questinon
            res = await simple_conversation(id_user, event_bot, question_number, question_id, cur_question)
            question_number = question_number + 1
        elif type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.SELECT]: # select questinon
            res = await select_conversation(id_user, event_bot, question_number, question_id, cur_question)
            question_number = question_number + 1
        elif type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.ONLYONE]: # onlyone questinon
            res = await onlyone_conversation(id_user, event_bot, question_number, question_id, cur_question)
            question_number = question_number + 1
        elif type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.HEADER] or \
             type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.FOOTER] or \
             type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.REPORT]:            
            question_id=question_id+1
            continue
        elif type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.TEXT]: # text
            cur_question = re.sub(r"ID4T_\d+_", "", cur_question)
            await bot.send_message(id_user, cur_question, parse_mode="html")
            question_id=question_id+1
            continue

        logging.debug(f"Dict res answers: {res}")
        question_id=question_id+1
        if res:
            answers.update(res)
        else:
            return False         
    #Show footer
    for cur_question,type in type_questions.items():
        if type == sts.TYPES_OF_QUESTONS[sts.FOOTER]: # footer
            if all_questions[cur_question]:
                path_to_file = await exist_file(all_questions[cur_question][0])                
            if path_to_file:
                await bot.send_file(id_user,file=path_to_file, caption=cur_question, parse_mode="html")
                path_to_file=''
            else:
                await bot.send_message(id_user, cur_question, parse_mode="html")
            break

    logging.debug(f"Dict All answers: {answers}")

    if answers:
        # Write Answers to DB
        async with dbm.DatabaseBot(sts.db_name) as db:     
                await db.db_add_answer(id_user, first_name, nickname, answers)
        #message=f"🔆 Вы ответили на все вопросы.\nРезультаты сохранены.\nДля повторного прохождения опроса\nнажмите кнопку Старт\n"

        #await bot.send_message(id_user, message)

        dt = datetime.now().strftime('%d%m%Y_%H%M%S')
        fname = f"reports/rpt_{id_user}_{dt}.pdf"
        logging.debug(f"Gen pdf filename: {fname}")
        await gen_pdf(answers,fname)
        message="📊 Ваш отчет"
        await bot.send_file( id_user, fname, caption=message, parse_mode="html" )
        #await asyncio.sleep(1) # Delay for user after send report and show menu
        if menu: 
            await create_admin_menu(menu, event_bot)

        return True
    
    return False

async def show_qusetions(event_bot):
    '''
    Show all questions
    '''
    i=1
    message="🧐 Текущие вопросы:"

    for cur_question,type in type_questions.items():
        if type == sts.TYPES_OF_QUESTONS[sts.HEADER]: # header
          message = message + f"\n{cur_question}\n"  

    for qst in all_questions:
        if type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.SIMPLE] or \
           type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.ONLYONE] or \
           type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.SELECT]:
            message = message + f"\n{i}. {qst}\n"
            i=i+1
        elif type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.TEXT]:
              #qst.replace('ID4T_[d]_', '')
              qst = re.sub(r"ID4T_\d+_", "", qst)
              message = message + f"\n{qst}\n"
              continue
        elif type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.HEADER] or \
             type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.FOOTER] or \
             type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.REPORT]:
             continue
        for variant in all_questions.get(qst):
            if type_questions.get(qst) == sts.TYPES_OF_QUESTONS[1]: # select 
                emoji='🔘'
            elif type_questions.get(qst) == sts.TYPES_OF_QUESTONS[2]: # onlyone
                emoji='🔹'
            else:
                emoji=''
            message = message + f"  {emoji} {variant}\n"

    for cur_question,type in type_questions.items():
        if type == sts.TYPES_OF_QUESTONS[sts.FOOTER]: # footer
          message = message + f"\n{cur_question}\n"  
    
    await event_bot.respond(message, parse_mode="html")
    await create_admin_menu(0, event_bot)

async def main_frontend():
    ''' Loop for bot connection '''
    
    #global all_questions

    @bot.on(events.NewMessage())
    async def bot_handler_nm_bot(event_bot):
        logging.debug(f"Get NewMessage event_bot: {event_bot}")
        menu_level = 0
      
        id_user = event_bot.message.peer_id.user_id
        logging.info(f"LOGIN USER_ID:{id_user}")
        #user_ent = await bot.get_entity(id_user)
        #nickname = user_ent.username
        #first_name = user_ent.first_name
        
        #logging.debug(f"Get username for id {id_user}: {nickname}")


        if event_bot.message.message == '/start':
            if id_user in sts.Admins:
            #if id_user in sts.Admins.keys():
                #await event_bot.respond("You are admin!")
                await create_admin_menu(menu_level, event_bot)
            else:
                # run anketa for all users who not Admin                    
                await check_user_run_anketa(id_user, event_bot, 0)           
        #elif event_bot.message.message == '/am_stats' and permissions.is_admin:
        #    await show_stats(event_bot)
        #    await create_admin_menu(0, event_bot)
        #elif event_bot.message.message == '/am_anketa'  and permissions.is_admin:
        #    await check_user_run_anketa(id_user, event_bot, 1)
        #    await create_admin_menu(0, event_bot)
        #elif event_bot.message.message == '/am_answers'  and permissions.is_admin:
        #    await send_answ_db(event_bot)
        #    await create_admin_menu(0, event_bot)
        #elif event_bot.message.message == '/am_questions' and permissions.is_admin:
        #    all_questions = await get_qusetion_data(event_bot)
        #    await create_admin_menu(0, event_bot)
        #else:     
        #    pass

    # Run hundler for button callback - menu for Admin
    @bot.on(events.CallbackQuery())
    async def callback_bot_choice(event_bot_choice):
        menu_level = 0
        id_user = event_bot_choice.query.user_id
        #user_ent = await bot.get_entity(id_user)
        logging.debug(f"Get callback event for user[{id_user}] {event_bot_choice}")
       
        # If user not Admin ignore button actions  
        #if id_user not in sts.Admins.keys(): return 0
        if id_user not in sts.Admins: return 0

        button_data = event_bot_choice.data.decode()
        #await event_bot.delete()
        if button_data == '/am_stats':
            await show_stats(event_bot_choice)
            await create_admin_menu(menu_level, event_bot_choice)
        elif button_data == '/am_anketa':
            await check_user_run_anketa(id_user, event_bot_choice, 1)
        elif button_data == '/am_answers':
            await send_report(event_bot_choice)
            await create_admin_menu(menu_level, event_bot_choice)
        elif button_data == '/am_questions':
            await get_qusetion_data(event_bot_choice)
        elif button_data == '/am_show_questions':
            await show_qusetions(event_bot_choice)
        elif button_data == '/am_get_img':
             await get_image(event_bot_choice)   
        elif button_data == '/am_add_admins':
            await add_admins(event_bot_choice)
        elif button_data == '/am_del_admins':
            await del_admins(event_bot_choice)
        elif button_data == '/am_show_admins':
            await show_admins(event_bot_choice)
        elif  'DEL_ADMIN_' in button_data:
            # Delete admin
            data = button_data
            admin_id_delete = int(data.replace('DEL_ADMIN_', ''))
            async with dbm.DatabaseBot(sts.db_name) as db:
                await db.db_del_admins(admin_id_delete)
            logging.info(f'All:{sts.Admins} admin_id_delete:_{admin_id_delete}_')
            sts.Admins.pop(admin_id_delete)
            await event_bot_choice.respond(f"🏁Админ {admin_id_delete} удален🏁")
            await create_admin_menu(menu_level, event_bot_choice)
    return bot

async def main():
    ''' Main function '''

    print("Start anketa Bot...")
    
    # Check for Admin and get user_id, clear and create new dict Admins for 
    # full data about Admin
   
    ret = await check_nickname(sts.Builtin_admin)
    if not ret:
        logging.error(f'Admin with nickname: {sts.Builtin_admin} Not exist in Telegram! Check config file!')
        print(f'Admin with nickname: {sts.Builtin_admin} Not exist in Telegram! Check config file!')
        exit(-1)
    else:
        sts.Admins.clear()
        sts.Admins.update(ret)
        #print(f'Admin with nickname: {sts.Admins}')
        #sexit(-1)


    async with dbm.DatabaseBot(sts.db_name) as db:
        logging.debug('Create db if not exist.')
        await db.db_create()
        new_questions_type,new_questions = await db.db_load_questions()
        rows = await db.db_load_admins()
        adm = {}
        if rows:
            for row in rows:
                #sts.Admins.append(dict(row).get('admin'))
                adm[dict(row).get('admin_id')]=dict(row).get('admin_nickname'),dict(row).get('admin_firstname')
        sts.Admins.update(adm)

        logging.info(f"Get Admins from db: {adm}\n")
        logging.info(f'All:{sts.Admins}\n')

    if new_questions:
        all_questions.clear()
        all_questions.update(new_questions)
        type_questions.clear()
        type_questions.update(new_questions_type)
        #Set report settings
        real_key=None
        for key, value in type_questions.items():
            if value == sts.TYPES_OF_QUESTONS[sts.REPORT]:
                real_key = key
                break

        if real_key:
            sts.report_title = key
            if all_questions[key]: 
                sts.report_logo = all_questions[key][0]
        logging.debug(f"Set report title = {sts.report_title} report logo = {sts.report_logo}")
        

    # Run basic events loop
    await main_frontend()    

#------------------- Main begin -----------------------------------------------

sts.get_config()
# Enable logging

# Init default questions
#'logo.jpg'
all_questions = {   "header is header!":['logo.jpg'],
                    "text_q1":[],
                    "ID4T_1_text multi select here":[],
                    "text_q2":['variant1','variant2','variant3','variant4'],
                    "text_q3":['variant1'],
                    "ID4T_2_text only one here":[],
                    "text_q4":['variant1','variant2','variant3'],
                    "text_q5":[],
                    "🔆 Вы ответили на все вопросы.\nРезультаты сохранены.\nДля повторного прохождения опроса\nнажмите кнопку Старт\n":['congratulation.jpg'],
                    "Ёжная Аткета":['logo.jpg']
                }
type_questions = {  "header is header!":"header",
                    "text_q1":"simple",
                    "ID4T_1_text multi select here":"text",
                    "text_q2":"select",
                    "text_q3":"onlyone",
                    "ID4T_2_text only one here":"text",
                    "text_q4":"onlyone",
                    "text_q5":"simple",
                    "🔆 Вы ответили на все вопросы.\nРезультаты сохранены.\nДля повторного прохождения опроса\nнажмите кнопку Старт\n":"footer",
                    "Ёжная Аткета":"report"
                }

filename=os.path.join(os.path.dirname(sts.logfile),os.path.basename(sts.logfile))
logging.basicConfig(level=sts.log_level, filename=filename, filemode="a", format="%(asctime)s %(levelname)s %(message)s")
logging.info("Start frontend bot.")

localedir = os.path.join(os.path.dirname(os.path.realpath(os.path.normpath(sys.argv[0]))), 'locales')

if sts.use_proxy:
    prx = re.search('(^.*)://(.*):(.*$)', sts.proxies.get('http'))
    proxy = (prx.group(1), prx.group(2), int(prx.group(3)))
else: 
    proxy = None

# Set type session: file or env string
if not sts.ses_bot_str:
    session = sts.session_bot
    logging.info("Use File session mode.")
else:
    session = StringSession(sts.ses_bot_str)
    logging.info("Use String session mode.")
    
# Init and start Telegram client as bot
bot = TelegramClient(session, sts.api_id, sts.api_hash, system_version=sts.system_version, proxy=proxy).start(bot_token=sts.mybot_token)

#bot.start()

with bot:
    bot.loop.run_until_complete(main())
    bot.run_until_disconnected()


