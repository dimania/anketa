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
import os
from pathlib import Path
import sys
import gettext
import json
from html import escape
from uuid import uuid4
from datetime import datetime
import requests
from telethon import TelegramClient, events
from telethon.tl.types import UpdateNewMessage
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
_ = None

BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "images"
QUESTION_DIR = BASE_DIR / "questionfiles"
REPORT_DIR = BASE_DIR / "reports"
os.umask(0o077)


def safe_path(directory, name, *, allow_symlink=False):
    """Return a path confined to directory, rejecting traversal and symlinks."""
    root = Path(directory).resolve()
    candidate = (root / str(name)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("path escapes storage directory") from error
    if not allow_symlink and (root / str(name)).is_symlink():
        raise ValueError("symlinks are not allowed")
    return candidate


def excel_safe(value):
    """Prevent spreadsheet formula injection from user-controlled strings."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def safe_excel_writer(filename):
    return pd.ExcelWriter(
        filename,
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_formulas": False, "strings_to_urls": False}},
    )


def safe_dataframe(df):
    """Apply cell escaping without relying on removed pandas APIs."""
    return df.apply(lambda column: column.map(excel_safe))

async def exist_file(path_to_file):
    '''
    Test for an image stored locally by the application.

    param path_to_file: url or file for test
    '''
    if not isinstance(path_to_file, str) or not path_to_file:
        return False
    if Path(path_to_file).name != path_to_file:
        return False
    try:
        path = safe_path(IMAGE_DIR, path_to_file)
    except ValueError:
        return False
    return str(path) if path.is_file() else False
    
class PDF(FPDF):
    
    #def __init__(self):
    #    # Add ttf fonts
    #    self.add_font('DejaVu-Bold', '', r'font/DejaVuSansCondensed-Bold.ttf')
    #   self.add_font('DejaVu', '', r'font/DejaVuSansCondensed.ttf')

    def header(self):
        # Logo
        logo = safe_path(IMAGE_DIR, sts.report_logo)
        self.image(str(logo), 5, 2, 20)
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

async def gen_pdf(answers, fname):
    '''
    Generate pdf file

    param answers: dict answers all users
    param fname:   filename for report
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

async def add_admins(event):
    ''' 
    Select users for add to admins list

    param event: bot event handled id    
    '''
    id_user = event.query.user_id
    logging.debug(f"Create select users dialog for user {id_user}")
    
    buttons = [
    {
        "text":_("👥 Выбор Админа"),
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
    "text": _("Нажмите кнопку 'Выбор Админа' чтобы добавть в список администраторов"), 
    "reply_markup": json.dumps(reply_markup)
    }

    # Send selection user Button 
    url = f"https://api.telegram.org/bot{sts.mybot_token}/sendMessage"

    response = requests.post(url, data=payload, timeout = 30, proxies=sts.proxies)
    logging.debug("Telegram admin-selection keyboard sent: %s", response.status_code)

    # hanled answer
    @bot.on(events.Raw(types=UpdateNewMessage))
    async def on_requested_peer_user(event_select):
        text_reply=''
        new_admins={}

        try:
            peer_id = getattr(getattr(event_select.message, "peer_id", None), "user_id", None)
            if peer_id != id_user:
                return
            if event_select.message.action.peers[0].__class__.__name__ == "RequestedPeerUser":
                button_id = event_select.message.action.button_id
                if button_id == 1:
                    for peer in event_select.message.action.peers:
                        if peer.user_id in sts.Admins:
                        #if peer.user_id in sts.Admins.keys():
                           text_reply=text_reply+f"⚠️{peer.username} {peer.first_name}" + _(" уже админ!\n")
                           continue
                        new_admins[int(peer.user_id)]=peer.username,peer.first_name

                    bot.remove_event_handler(on_requested_peer_user)
                    if new_admins:
                        logging.info("Adding %d administrator(s)", len(new_admins))
                        # Add new admins in DB
                        async with dbm.DatabaseBot(sts.db_name) as db:
                            ret = await db.db_add_admins(new_admins)
                        if ret:
                            #Update current list of admins
                            sts.Admins.update(new_admins)
                            text_reply=text_reply+_("🏁Администраторы добавлены🏁")
                        else:
                            text_reply=_("🏁Ошибка добавления админа🏁")
                    else:
                        text_reply=text_reply+_("Некого добавить!")

                    reply_markup = { "remove_keyboard": True }
                    payload_remove_kb = {
                    "chat_id": id_user, # Id user to
                    "text": text_reply, 
                    "reply_markup": json.dumps(reply_markup)
                    }
                    response = requests.post(url, data=payload_remove_kb, timeout = 30, proxies=sts.proxies)
                    logging.debug("Telegram admin-selection keyboard removed: %s", response.status_code)
                    await create_admin_menu(0, event) 
                    
                    return 
        except Exception:
            logging.debug("Ignored non-admin-selection update", exc_info=True)
            return None

async def del_admins(event):
    ''' 
    Delete admins form list
    
    param event: bot event handled id
    '''
    
    logging.debug("Call del_admins() function")
    bdata_id='DEL_ADMIN_'
    button=[]
    admin_name=''
    admin_nickname=''
    deletable = {
        admin_id: cur_admin for admin_id, cur_admin in sts.Admins.items()
        if admin_id not in sts.Admin_ids
    }
    logging.debug("Deletable administrators: %d", len(deletable))

    if deletable:
        message=_("❌ Выберете админа для удаления:")
        for admin_id, cur_admin in deletable.items():
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
           await event.respond(_("⚠️Нет админов для удаления."))
           await create_admin_menu(0,event)
           return False
    
    await event.respond(message, buttons=button)    
    return True

async def show_admins(event):
    ''' 
    Show current admins

    param event: bot event handled id
    '''
    Builtin_Admin='💂‍♂️'
    Simply_Admin='👮'

    i=True

    admin_name=''
    admin_nickname=''
    rstr=_('📃Cписок текущих Админов:\n\n')
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
    '''
    Try get Nikckname of user

    param username: Name of user
    return nickname or False
    '''
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
    param fname: Excel file with questions 
    param sheet_name: Name of Sheet - can be an integer (0 for the first sheet) or a string ('Sheet1').

    return dict of data.
    """
    try:
        df = pd.read_excel(
            fname,
            sheet_name=sheet_name,
            header=None,
            nrows=sts.MAX_EXCEL_ROWS + 1,
        )
        # Convert the DataFrame to dict
        res=df.to_dict(orient='split', index=False) 
        return res
    except Exception as e:
        logging.warning(f"Error reading Excel file: {e}")
        return False

async def gen_excel(filename):
    '''
    Generate excel report table

    param filename: filename of created report file in excel format
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
    sort_order_qst=[]
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
        sort_order_qst.append(key_q)
        data['question'].append(key_q)        
        answer_cur=dict(row).get('answer_user')
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
    df = pd.DataFrame(data)
    df1 = pd.DataFrame(data_ws2)
    df = safe_dataframe(df)
    df1 = safe_dataframe(df1)

    # Order the columns 
    df = df[["name_user", "nick_user", "question", "answer_user", "date", "time" ]]
    sort_list_ws2=["date", "time", "name_user", "nick_user"]
    sort_list_ws2 = sort_list_ws2 + sort_order_qst
    logging.debug(f"Results gen excel: sort: {sort_list_ws2}")
    df1 = df1[sort_list_ws2]

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = safe_excel_writer(filename)

    # Write the dataframe data to XlsxWriter. Turn off the default header and
    # index and skip one row to allow us to insert a user defined header.
    df1.to_excel(writer, sheet_name=_("По вопросам"), startrow=1, header=False, index=False)
    df.to_excel(writer, sheet_name=_("По пользователям"), startrow=1, header=False, index=False)
    # Get the xlsxwriter workbook and worksheet objects.
    #workbook = writer.book
    worksheet = writer.sheets[_("По вопросам")]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df1.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": excel_safe(str(column))} for column in df1.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)
    # Close the Pandas Excel writer and output the Excel file.
    worksheet = writer.sheets[_("По пользователям")]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": excel_safe(str(column))} for column in df.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)

   
    writer.close()
    
    return True

async def new_gen_excel(filename):
    '''
    Generate excel report table

    param filename: filename of created report file in excel format
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
    df = safe_dataframe(df)
    df1 = safe_dataframe(df1)

    # Order the columns if necessary.
    #df = df[["name_user", "nick_user", "question", "answer_user", "date", "time" ]]
    #sort_list_ws2=["date", "time", "name_user", "nick_user"]
    #sort_list_ws2.extend(key_q)
    #logging.info(f"Results gen excel: sort: {sort_list_ws2}")
    #df1 = df1[["date", "time", "name_user", "nick_user", ]] # "question", "answer_user", 

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = safe_excel_writer(filename)

    # Write the dataframe data to XlsxWriter. Turn off the default header and
    # index and skip one row to allow us to insert a user defined header.
    df1.to_excel(writer, sheet_name=_("По вопросам"), startrow=1, header=False, index=False)
    df.to_excel(writer, sheet_name=_("По пользователям"), startrow=1, header=False, index=False)
    # Get the xlsxwriter workbook and worksheet objects.
    #workbook = writer.book
    worksheet = writer.sheets[_("По вопросам")]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df1.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": excel_safe(str(column))} for column in df1.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)
    # Close the Pandas Excel writer and output the Excel file.
    worksheet = writer.sheets[_("По пользователям")]

    # Get the dimensions of the dataframe.
    (max_row, max_col) = df.shape

    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": excel_safe(str(column))} for column in df.columns]

    # Add the Excel table structure. Pandas will add the data.
    worksheet.add_table(0, 0, max_row, max_col - 1, {"columns": column_settings})

    # Make the columns wider for clarity.
    worksheet.set_column(0, max_col - 1, 12)

   
    writer.close()
    
    return True

async def send_excel_report(event):
    '''
    Send ecxel report 

    param event: bot event handled id
    '''
    logging.debug("Call send_answ_db() function")

    dt = datetime.now().strftime('%d%m%Y_%H%M%S')
    
    fname = str(REPORT_DIR / f"report_{dt}.xlsx")
    logging.debug(f"Gen filename: {fname}")
    try:
        res = await gen_excel(fname)
        if res:
            message="📊 Ваш отчет"
            await bot.send_file(event.query.user_id, fname, caption=message, parse_mode="html")
            await asyncio.sleep(3)
            return True
        await event.respond(_("🚷На данный момент нет информаци для отчета.\nЕще никто не прошел опрос."))
        return False
    finally:
        Path(fname).unlink(missing_ok=True)
    
async def set_dataframe_sheet1(rows):
    '''
    Ctreate dataframe for Sheet1
    param rows: raw data from db - Colums is: name_user, nick_user, question,  answer_user, date, time
    
    return list data for gen excel file
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
    logging.debug("Prepared detailed Excel sheet")

    return data

async def set_dataframe_sheet2(rows):
    '''
    Ctreate dataframe for Sheet2
    
    param rows: raw data from db - Colums is: date, time, name_user, nick_user, question1, question2 ...
    
    return list data for gen excel file
    '''
    global_row=0
    variant_row=0
    data=defaultdict(list)
    # Get name_user, nick_user, question, answer_user, date
    for row in rows:
        len_row = len(row)
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
        
        index=int(dict(row).get('question_id'))
        #data['question'].append(all_questions[index-1])
        key_q=list(all_questions)[index-1]
        answer_cur=dict(row).get('answer_user')        
        #logging.info(f"DF2 ALL Q: Question={key_q}")

        if all_questions.get(key_q):
            i=False
            #variant_row = variant_row + 1 
            for variant in answer_cur.split(','): #FIXME HERE
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

        
    logging.debug("Prepared aggregated Excel sheet")
    return data

async def get_qusetion_data(event_bot):
    '''
    Get form user and load questions to DB Questions

    param event_bot: bot event handled id
    '''
    logging.debug("Call get_qusetion_data() function")
    
    await event_bot.respond(\
    _("📎 Загрузите файл с вопросами.\n\n" \
    "MS Excel файл (xls,xlsx) заполненнный согласно шаблона\n"
    "\n♨️ Текущие вопросы и ответы будут удалены!"))

    admin_id = event_bot.query.user_id

    @bot.on(events.NewMessage(from_users=admin_id))
    async def bot_handler_f_bot(event):
        if event.sender_id != admin_id:
            return
        if event.message.document:
            download_path = None
            try:
                file_size = getattr(event.message.file, "size", None)
                if file_size and file_size > sts.MAX_UPLOAD_BYTES:
                    await event.respond(_("⚠️Файл слишком большой."))
                    return
                download_path = QUESTION_DIR / f"upload-{uuid4().hex}"
                downloaded = await event.message.download_media(file=str(download_path))
                if not downloaded or Path(downloaded).stat().st_size > sts.MAX_UPLOAD_BYTES:
                    await event.respond(_("⚠️Файл слишком большой."))
                    return
                new_type_questions, new_questions, warnings = await get_new_questions(downloaded)
                if not new_questions:
                    await event_bot.respond(_("⚠️Неверные данные, проверьте файл с вопросами!"))
                    return
                async with dbm.DatabaseBot(sts.db_name) as db:
                    await db.db_rewrite_new_questions(new_questions, new_type_questions)
                all_questions.clear()
                type_questions.clear()
                all_questions.update(new_questions)
                type_questions.update(new_type_questions)
                await event.respond(_("Данные загружены в бот."))
                if warnings:
                    await event.respond(warnings)
                await create_admin_menu(0, event_bot)
            except Exception:
                logging.exception("Question file processing failed")
                await event.respond(_("⚠️Не удалось обработать файл."))
            finally:
                if download_path:
                    Path(download_path).unlink(missing_ok=True)
                bot.remove_event_handler(bot_handler_f_bot)

async def get_new_questions(fname):
    '''
    Get new questions from file xls,xlsx and return list

    param fname: file with questions

    return tlist,qlist,warnings  tlist - type of filed, qlist - text question, warnings - Warning for user if image file not exist
    '''
    #root,ext = os.path.splitext(fname)
    try:
        if Path(fname).stat().st_size > sts.MAX_UPLOAD_BYTES:
            return False, False, False
    except OSError:
        return False, False, False
    kind = filetype.guess(fname)
    
    #logging.debug(f'File extension: {kind.extension}')
    #logging.debug(f'File MIME type: {kind.mime}')

    if kind is None:
        logging.debug(f'Cannot guess file type filename: {fname}!')
        return False,False,False
    elif kind.extension == 'xlsx' or kind.extension == 'xls':
        text_content = await get_excel_data(fname)
    else:
        return False, False, False
    
    if not text_content:
        return False,False,False
    if len(text_content.get('data', [])) > sts.MAX_EXCEL_ROWS:
        return False, False, False
    if any(len(row) > sts.MAX_EXCEL_COLUMNS for row in text_content.get('data', [])):
        return False, False, False
    
    qlist={}
    tlist={}
    val=[]
    warnings=''
    id4t=1
    sts.report_logo = sts.def_report_logo
    sts.report_title = sts.def_report_title
    for item in text_content['data']:
        #item - one question and variants answers if exist
        if not item:
            return False, False, False
        type_current_qusetion=item.pop(0)
        if type_current_qusetion not in sts.TYPES_OF_QUESTONS:
            #raise ValueError("Type of question invald!")
            return False,False,False             
        if not item or not isinstance(item[0], str) or len(item[0]) > 4096:
            return False, False, False
        if any(isinstance(value, str) and len(value) > 4096 for value in item):
            return False, False, False
        nan_list=pd.isna(item)
        i=False
        # variants answer to list values dict        
        for x, y in zip(item,nan_list):
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
                    logging.debug("Set report logo from validated local file")
                    #continue
            else:
                logging.warning(f"Warning file or url {val[0]} not exist")
                warnings=warnings + _("⚠️Внимание! файл или URL ") + f"{val[0]}" + _(" не существует!\nБудет использован файл по умолчанию.\n")   
                val[0]=''
        if type_current_qusetion == sts.TYPES_OF_QUESTONS[sts.TEXT]: # Add some id to text for repeat in dict key            
            item[0]=f"ID4T_{id4t}_"+item[0]
            #val[0]=''
            id4t = id4t + 1

            
            
        qlist[item[0]]=val
        tlist[item[0]]=type_current_qusetion
        val=[]
        logging.debug("Validated questionnaire row %d", len(tlist))
    
    return tlist,qlist,warnings

async def show_qusetions(event_bot):
    '''
    Show all current questions

    param event_bot: bot event handled id
    '''
    i=1
    message=_("🧐 Текущие вопросы:")

    for cur_question,type in type_questions.items():
        if type == sts.TYPES_OF_QUESTONS[sts.HEADER]: # header
              message = message + f"\n{escape(str(cur_question))}\n"

    for qst in all_questions:
        if type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.SIMPLE] or \
           type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.ONLYONE] or \
           type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.SELECT]:
            message = message + f"\n{i}. {escape(str(qst))}\n"
            i=i+1
        elif type_questions.get(qst) == sts.TYPES_OF_QUESTONS[sts.TEXT]:
              #qst.replace('ID4T_[d]_', '')
              qst = re.sub(r"ID4T_\d+_", "", qst)
              message = message + f"\n{escape(str(qst))}\n"
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
            message = message + f"  {emoji} {escape(str(variant))}\n"

    for cur_question,type in type_questions.items():
        if type == sts.TYPES_OF_QUESTONS[sts.FOOTER]: # footer
          message = message + f"\n{escape(str(cur_question))}\n"
    
    await event_bot.respond(message, parse_mode="html")
    await create_admin_menu(0, event_bot)

async def create_admin_menu(level, event):
    ''' 
    Create Admin menu 
    
    param level: currently not used
    param event: bot event handled id
    '''
    logging.debug("Create menu buttons")
    keyboard = [
        [
            Button.inline(_("📈 Показать статистику"), b"/am_stats")
        ],
        [
            Button.inline(_("📃 Пройти анкетирование"), b"/am_anketa")
        ],
        [
            Button.inline(_("📊 Получить результаты"), b"/am_answers")
        ],
        [
            Button.inline(_("📑 Текущие вопросы"), b"/am_show_questions")
        ],
        [
            Button.inline(_("⬆️ Загрузить новые вопросы"), b"/am_questions")
        ]
        ,
        [
            Button.inline(_("📰 Работа с файлами"), b"/am_files")
        ]
        ,
        [
            Button.inline(_("👮‍♂️ Добавть администратора"), b"/am_add_admins")
        ]
        ,
        [
            Button.inline(_("🙅‍♂️ Удалить администратора"), b"/am_del_admins")
        ]
        ,
        [
            Button.inline(_("🕵️ Просмотреть всех админов"), b"/am_show_admins")
        ]
    ]
    #clear old message
    await event.delete()
    # send menu
    await event.respond(_("**☣ Режим Администратора:**"), parse_mode='md', buttons=keyboard)

async def show_stats(event):
    '''
    Show statistics for users

    param event: bot event handled id
    '''
    logging.debug("Call show_stats() function")

    async with dbm.DatabaseBot(sts.db_name) as db:
        rows = await db.get_info_by_users()
    if not rows:
        await event.respond(_("🚷На данный момент нет информаци.\nЕще никто не прошел опрос."))
        return False

    strstat=_("🔢 Ответили на вопросы: ") + f"{len(rows)}\n\n" + _("👥 Список прошедших опрос:\n\n")

    for row in rows:
        #dt = datetime.strptime(dict(row).get('date'),'%Y-%m-%d %H:%M:%S.%f')
        #strstat=strstat+f"{dict(row).get('name_user')} { dt.strftime('%d.%m.%y %H:%M') }\n"
        strstat=strstat+f"{dict(row).get('name_user')}\n"

    await event.respond(strstat)
  
    return True 

async def test_send_excel_report(event):# USE for test create report excel file
    '''
    Send answers DB to Admin (load results)

    param event: bot event handled id
    '''
    logging.debug("Call send_answ_db() function")

    dt = datetime.now().strftime('%d%m%Y_%H%M%S')
    
    fname = str(REPORT_DIR / f"report_{dt}.xlsx")
    logging.debug(f"Gen filename: {fname}")
    res = await gen_excel(fname)
    return True

async def list_files4selection(directory, exclude = None):
    '''
    List files in dir and create menu 

    param directory: directory where files
    param exclude: dont include its list files in selection
    return selection list
    '''
    fbut=[]
    if not exclude:
        exclude=[]
    all_entries = os.listdir(directory)
    for file in all_entries:
        if file in exclude:
            continue
        try:
            path = safe_path(directory, file)
        except ValueError:
            continue
        if path.is_file() and not path.is_symlink():
            fbut.append(file)

    return fbut

async def delete_files( directory, list_files ):
    '''
    Delete files list_files in dir

    
    param directory: dir where delete files
    param list_files: list files from deletion
    '''
    for file in list_files:
        try:
            f = safe_path(directory, file)
            if f.is_file() and not f.is_symlink():
                f.unlink()
                logging.info("Removed managed file %s", f.name)
        except (OSError, ValueError) as e:
            logging.warning("Error removing managed file: %s", e)
            return False
    return True

async def create_menu_files(event): 
    '''
    Create Menu for work with files

    param event: bot event handled id
    '''

    logging.debug("Create menu files")
    keyboard = [
        [
            Button.inline(_("🖼 Показать файлы изображений"), b"/fm_list_images") #📈
        ],
        [
            Button.inline(_("⬆️ Загрузить файлы изображений"), b"/fm_upl_images")
        ],
        [
            Button.inline(_("🗑️ Удалить файлы изображений"), b"/fm_del_images")
        ],
        [
            Button.inline(_("📊 Показать файлы отчетов"), b"/fm_list_reports")
        ],
        [
            Button.inline(_("🗑️ Удалить файлы отчетов"), b"/fm_del_reports")
        ],
        [
            Button.inline(_("⬇️ Получить файлы отчетов"), b"/fm_down_reports")
        ]
        ,
        [
            Button.inline(_("📋 Показать файлы вопросов"), b"/fm_list_qst")
        ]
        ,
        [
            Button.inline(_("🗑️ Удалить файлы вопросов"), b"/fm_del_qst")
        ]
        ,
        [
            Button.inline(_("⬇️ Получить файлы вопросов"), b"/fm_down_qst")
        ]
        ,
        [
            Button.inline(_("⬅️ Назад"), b"/fm_to_adm_menu")
        ]
        
    ]
    #clear old message
    await event.delete()
    # send menu
    await event.respond(_("**☣ Режим Администратора - файлы:**"), parse_mode='md', buttons=keyboard)

async def ui_list_files(event, directory, title, exclude = None):
    '''
    Send to user list files

    param event: bot event handled id
    param directory: dir where delete files
    param title: text of message
    param exclude: list files with not include to list for show user - may be default images by example 
    '''
    listf=await list_files4selection(directory, exclude)
    if listf:
        message = title + '\n'
        for f in listf:
            message = message + f  + '\n'
        await event.respond(message)
    else:
        await event.respond(_('Нет файлов'))

async def ui_del_files(event, directory, title, exclude = None):
    '''
    Show user dialog for delete files

    param event: bot event handled id
    param directory: dir - where delete files
    param title: text of message
    param exclude: list files with not include to list for show user - may be default images by example
    '''
    id_user = event.query.user_id
    listf=await list_files4selection(directory, exclude)
    if listf:
        del_list = await unv_select_conversation(id_user, event, title, _('Готово'), listf)
        if del_list:
            if await delete_files(directory,del_list):
                await event.respond(_('Файлы удалены.'))
    else:
        await event.respond(_('Нет файлов'))

async def ui_get_files(event, directory, title, exclude = None):
    '''
    Show user dialog for download files

    param event: bot event handled id
    param directory: dir - where delete files
    param title: text of message
    param exclude: list files with not include to list for show user - may be default images by example
    '''
    id_user = event.query.user_id
    listf=await list_files4selection(directory, exclude)
    if listf:
        rep_list = await unv_select_conversation(id_user, event, title, _('Готово'), listf)
        if rep_list:
            for repf in rep_list:
                try:
                    path = safe_path(directory, repf)
                except ValueError:
                    continue
                if path.is_file() and not path.is_symlink():
                    await bot.send_file(id_user, str(path))
                await asyncio.sleep(0.5)
    else:
        await event.respond(_('Нет файлов'))

async def show_files(event, flist): # I think no need
    '''
    Show files

    param event: bot event handled id 
    param flist: list of files
    '''
    message = ''
    

    for file in flist:
        message =  message + f'{file}\n'

    await event.respond(message)
       
async def get_image(event_bot):
    '''
    Get and load image, logo, etc...

    param event_bot: bot event handled id
    '''
    logging.debug("Call get_image() function")
    fmsg=''   
    support_img=['jpeg','jpg','gif','png','webp']
    all_entries = os.listdir('images/')
    for file in all_entries:
        fmsg=fmsg+file+'\n'
    message=_("Сейчас загружены следующие файлы:\n") + fmsg + _("\n📎 Загрузите файл с изображнием.\n\n" \
        "Поддержиаются следующие типы файлов:\n" \
        "jpeg, jpg, gif, png, webp размером не более 5МБ")
    await event_bot.respond(message)

    @bot.on(events.NewMessage(from_users=event_bot.query.user_id))
    async def bot_handler_f_bot(event):
        if event.sender_id != event_bot.query.user_id:
            return
        dl=False      
        if event.message.photo: 
            dl=True
        if event.message.document:
            if 'image/' in (event.message.document.mime_type or ''):
                dl=True
        download_path = None
        try:
            file_size = getattr(event.message.file, "size", None)
            if file_size and file_size > sts.MAX_UPLOAD_BYTES:
                await event.respond(_("⚠️Файл слишком большой."))
                return
            if not dl:
                await event.respond(_("⚠️Данный тип файла не поддерживается, попробуйте другой файл!"))
                return
            download_path = IMAGE_DIR / f"upload-{uuid4().hex}"
            downloaded = await event.message.download_media(file=str(download_path))
            if not downloaded or Path(downloaded).stat().st_size > sts.MAX_UPLOAD_BYTES:
                await event.respond(_("⚠️Файл слишком большой."))
                return
            kind = filetype.guess(downloaded)
            if kind is None or kind.extension not in support_img:
                await event.respond(_("⚠️Данный тип файла не поддерживается, попробуйте другой файл!"))
                return
            extension = kind.extension
            final_path = IMAGE_DIR / f"{uuid4().hex}.{extension}"
            Path(downloaded).replace(final_path)
            await event.respond(_("Данные загружены в бот."))
        except (OSError, ValueError):
            logging.exception("Image upload failed")
            await event.respond(_("⚠️Не удалось загрузить изображение."))
        finally:
            if download_path:
                Path(download_path).unlink(missing_ok=True)
            bot.remove_event_handler(bot_handler_f_bot)
            await create_menu_files(event_bot)
        
async def simple_conversation(id_user, event_bot, question_number, question_id, cur_question): #OLD NOT USE
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
            await conv.send_message(_("Вопрос ")+f"{question_number}:\n{cur_question}")
            #WAIT ANSWER SIMLPE HERE
            response = await conv.get_response(timeout=sts.TIMEOUT_FOR_ANSWER)
            resp_text = response.text
            if not resp_text or len(resp_text) > 4096:
                await conv.send_message(_("⚠️Ответ должен содержать от 1 до 4096 символов."))
                conv.cancel()
                return False
            logging.info("Received answer for user %s (%d chars)", id_user, len(resp_text))
            answers[question_id+1].append(resp_text)
        except TimeoutError as error:
            logging.debug("Answer timeout for user %s after %s seconds", id_user, sts.TIMEOUT_FOR_ANSWER)
            message=_("⚠️Отведенное время ") + f"{sts.TIMEOUT_FOR_ANSWER}" + _(" секунд на ответ истекло.\n"\
                                    "Результаты не будут сохранены.\n"\
                                    "Пожалуйста пройдите опрос заново.\n"\
                                    "Для этого  в ≡Меню выберете Старт\n")
            await conv.send_message(message)
            conv.cancel()        
            return False
        
        conv.cancel()
        return answers      
    
async def unv_simple_conversation(id_user, event_bot, message):
    '''
    simple_conversation - Dialog for simple question, only text filed
    
    param id_user: dialog for telegram user - id_user
    param event_bot: parent entity
    param message: message to user

    return user text
    '''

    async with bot.conversation(id_user) as conv:
        def my_press_event(id_user):
            return events.CallbackQuery(func=lambda e: e.sender_id == id_user) #FIXME Need or not use pattern for get button?
        try:
            await conv.send_message(message)
            #WAIT ANSWER SIMLPE HERE
            response = await conv.get_response(timeout=sts.TIMEOUT_FOR_ANSWER)
            answer = response.text or ""
            if not answer or len(answer) > 4096:
                await conv.send_message(_("⚠️Ответ должен содержать от 1 до 4096 символов."))
                conv.cancel()
                return False
            logging.info("Received answer for user %s (%d chars)", id_user, len(answer))
        except TimeoutError as error:
            logging.debug("Answer timeout for user %s after %s seconds", id_user, sts.TIMEOUT_FOR_ANSWER)
            message=_("⚠️Отведенное на ответ время ") + f"{sts.TIMEOUT_FOR_ANSWER}" + _(" секунд истекло.")
            await conv.send_message(message)
            conv.cancel()        
            return False
        
        conv.cancel()
        return answer

async def onlyone_conversation(id_user, event_bot, question_number, question_id, cur_question): #OLD NOT USE
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
            str_qst=_("Вопрос ") + f"{question_number}:\n{cur_question}"
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
            logging.debug("Received a valid single-choice selection for question %s", question_id)
            answers[question_id+1].append(answ_v[1])
        except TimeoutError as error:
            logging.debug("Answer timeout for user %s after %s seconds", id_user, sts.TIMEOUT_FOR_ANSWER)
            message=_("⚠️Отведенное время ") + f"{sts.TIMEOUT_FOR_ANSWER}" + _(" секунд на ответ истекло.\n"\
                                    "Результаты не будут сохранены.\n"\
                                    "Пожалуйста пройдите опрос заново.\n"\
                                    "Для этого  в ≡Меню выберете Старт\n")
            await conv.send_message(message)
            conv.cancel()
            return False
        
    conv.cancel()        
    return answers      

async def unv_onlyone_conversation(id_user, event_bot, message, list_items):
    '''
    Onlyone_conversation - Dialog for select only one option 

    param id_user: dialog for telegram user - id_user
    param event_bot: parent entity
    param message:message to user
    param list_items: list variants

    return selected variant
    '''
    sender = await event_bot.get_sender()
    sender_id = sender.id
    #sender_id = await event_bot.get_sender().id
    button=[]
    bdata=''
    answ_v=[]

    async with bot.conversation(id_user) as conv:
        def my_press_event(id_user):
            return events.CallbackQuery(func=lambda e: e.sender_id == id_user) #FIXME Need or not use pattern for get button?
        try:
            button.clear()
            for variant in list_items:
                bdata=f'VARIANT_{variant}'
                button.append([Button.inline(f'🔹 {variant}', bdata)])   
            await conv.send_message(message, buttons=button)            
            #Нandle respond
            handle = conv.wait_event(my_press_event(sender_id),timeout=sts.TIMEOUT_FOR_ANSWER) #FIXME Need or not use pattern for get button?
            event_res = await handle 
            button_pressed = event_res.data.decode('utf-8')
            if not button_pressed.startswith('VARIANT_'):
                return False
            answ_v = button_pressed.removeprefix('VARIANT_')
            if answ_v not in list_items:
                return False
            logging.debug("Received a valid single-choice selection")
        except TimeoutError as error:
            logging.debug("Answer timeout for user %s after %s seconds", id_user, sts.TIMEOUT_FOR_ANSWER)
            message=_("⚠️Отведенное на ответ время ") + f"{sts.TIMEOUT_FOR_ANSWER}" + _(" секунд истекло.")
            await conv.send_message(message)
            conv.cancel()
            return False
        
    conv.cancel()        
    return answ_v

async def select_conversation(id_user, event_bot, question_number, question_id, cur_question): #OLD NOT USE
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
            str_qst=_("Вопрос ") + f"{question_number}:\n{cur_question}"
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
                logging.debug("Received a valid multi-choice selection for question %s", question_id)

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
                button.append([ Button.inline(_('Ответить'), bdata)])
                await bot.edit_message(event_res.query.user_id, event_res.query.msg_id,str_qst, buttons=button)
        except TimeoutError as error:
            logging.debug("Answer timeout for user %s after %s seconds", id_user, sts.TIMEOUT_FOR_ANSWER)
            message=_("⚠️Отведенное время ") + f"{sts.TIMEOUT_FOR_ANSWER}" + _(" секунд на ответ истекло.\n"\
                                    "Результаты не будут сохранены.\n"\
                                    "Пожалуйста пройдите опрос заново.\n"\
                                    "Для этого  в ≡Меню выберете Старт\n")
            await conv.send_message(message)
            conv.cancel()
            return False

    conv.cancel()            
    return answers    

async def unv_select_conversation(id_user, event_bot, message, end_name_btn, list_items):
    '''
    Select_conversation - Dialog for multi select option 

    param id_user: dialog for telegram user - id_user
    param event_bot: parent entity
    param message:message to user
    param list_items: list variants
    param: end_name_btn name last buttom in select dialog

    return list selected variants
    '''
    sender = await event_bot.get_sender()
    sender_id = sender.id
    #sender_id = await event_bot.get_sender().id
    button=[]
    bdata=''
    result=[]

    async with bot.conversation(id_user) as conv:
        def my_press_event(id_user):
            return events.CallbackQuery(func=lambda e: e.sender_id == id_user) #FIXME Need or not use pattern for get button?
        try:
            #sender_id = await event_bot.get_sender().id
            sender = await event_bot.get_sender()
            sender_id = sender.id
            button.clear()

            for variant in list_items:
                bdata=f'VARIANT_{variant}'
                button.append([ Button.inline(f'🔘 {variant}', bdata)])
            await conv.send_message(message, buttons=button)
            
            while True:
                #Нandle respond
                handle = conv.wait_event(my_press_event(sender_id),timeout=sts.TIMEOUT_FOR_ANSWER) #FIXME Need or not use pattern for get button?
                event_res = await handle 
                button_pressed = event_res.data.decode('utf-8')                
                if button_pressed == 'ANSWER':           
                    break     

                if not button_pressed.startswith('VARIANT_'):
                    continue
                cur_sel_var = button_pressed.removeprefix('VARIANT_')
                if cur_sel_var not in list_items:
                    continue
                logging.debug("Updated multi-choice selection")
                
                if cur_sel_var in result:
                    result.remove(cur_sel_var)
                else:   
                    result.append(cur_sel_var)
                # Create new buttons with selected option
                button.clear()
                for variant in list_items:
                    bdata=f'VARIANT_{variant}'
                    if variant in result:
                        emoji='🟢'
                    else:
                        emoji='🔘'
                    button.append([ Button.inline(f'{emoji} {variant}', bdata)])
                
                bdata='ANSWER'
                button.append([ Button.inline(end_name_btn, bdata)])
                await bot.edit_message(event_res.query.user_id, event_res.query.msg_id, message, buttons=button)
        except TimeoutError as error:
            logging.debug("Answer timeout for user %s after %s seconds", id_user, sts.TIMEOUT_FOR_ANSWER)
            message=_("⚠️Отведенное на ответ время ") + f"{sts.TIMEOUT_FOR_ANSWER}" + _(" секунд истекло.")
            await conv.send_message(message)
            conv.cancel()
            return False

    conv.cancel()            
    return result

async def check_user_run_anketa(id_user, event_bot, menu):
    '''
    Test user already answer or not

    param id_user: Id of user in Telegram
    param event_bot: bot event handled id
    param menu: Show or not basic menu - True or False

    '''    
    async with dbm.DatabaseBot(sts.db_name) as db:
        res = await db.db_exist_id_user(id_user)
    
    logging.debug("Existing answer check for user %s: %s", id_user, bool(res))

    # if user already answer     
    if res:
        keyboard = [Button.inline(_("Да"), b"/yes"), Button.inline(_("Нет"), b"/no")]
        prompt = await event_bot.respond(
            _("⚠️Вы уже отвечали на вопросы.\nЖелаете пройти опрос снова?\n♨️Предыдущие ответы будут потеряны.\n"),
            parse_mode='md',
            buttons=keyboard,
        )
        prompt_id = getattr(prompt, "id", None)

        @bot.on(events.CallbackQuery())
        async def callback_yn(event):
            if event.sender_id != id_user:
                return
            if prompt_id is not None and event.message_id != prompt_id:
                return
            button_data = event.data.decode()
            if button_data not in ('/yes', '/no'):
                return
            logging.info("Existing-answer prompt handled for user %s", id_user)
            if button_data == '/no':
                await event_bot.respond(_("До свидания.\n\n"))
            else:
                async with dbm.DatabaseBot(sts.db_name) as db:
                    await db.db_del_user_answers(id_user)
                await run_anketa(id_user, event_bot, menu)
            bot.remove_event_handler(callback_yn)
            return 0
    else:
        await run_anketa(id_user, event_bot, menu)       
        return 2
        
async def run_anketa(id_user, event_bot, menu):
    '''
    Run main process for anketting

    param id_user: Id of user in Telegram
    param event_bot: bot event handled id
    param menu: Show or not basic menu - True or False
    '''
    user_ent = await bot.get_entity(id_user)
    nickname = user_ent.username or ""
    first_name = user_ent.first_name or ""
    if not nickname:
        nickname = first_name

    question_id=0
    question_number=1
    path_to_file=''
    answers=defaultdict(list)
    res=defaultdict(list)
    
    logging.debug("Starting questionnaire for user %s", id_user)

    if sts.timeout_warning:
        message=_("⚠️На каждый ответ отводится ") + f"{sts.TIMEOUT_FOR_ANSWER}" + _(" секунд.\n\n")
        await event_bot.respond(message)
    #Show Header
    for cur_question,type_qst in type_questions.items():
        if type_qst == sts.TYPES_OF_QUESTONS[sts.HEADER]: # header
            if all_questions[cur_question]:
                path_to_file = await exist_file(all_questions[cur_question][0])
            if path_to_file:
                await bot.send_file(id_user,file=path_to_file, caption=escape(str(cur_question)), parse_mode="html")
                path_to_file=''                           
            else:
                await bot.send_message(id_user, escape(str(cur_question)), parse_mode="html")
            break
    #Show question 
    for cur_question,variants  in all_questions.items():
        if type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.SIMPLE]: # simple questinon
            #res = await simple_conversation(id_user, event_bot, question_number, question_id, cur_question)
            message = _("Вопрос ") + f"{question_number}:\n{cur_question}"
            answ = await unv_simple_conversation(id_user, event_bot, message)
            logging.debug("Completed simple question %d", question_number)
            res[question_id+1].append(answ)
            logging.debug("Completed select question %d", question_number)
            question_number = question_number + 1
        elif type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.SELECT]: # select questinon
            message = _("Вопрос ") + f"{question_number}:\n{cur_question}"
            answ = await unv_select_conversation(id_user, event_bot, message, _('Ответить'), variants)
            logging.debug("Completed single-choice question %d", question_number)
            i=1
            for var in variants:
                if var in answ:
                    res[question_id+1].append(str(i))
                i = i + 1
            res[question_id+1].sort()
            #res = await select_conversation(id_user, event_bot, question_number, question_id, cur_question)
            logging.debug("Completed single-choice question %d", question_number)
            question_number = question_number + 1
        elif type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.ONLYONE]: # onlyone questinon
            #res = await onlyone_conversation(id_user, event_bot, question_number, question_id, cur_question)
            message = _("Вопрос ") + f"{question_number}:\n{cur_question}"
            answ = await unv_onlyone_conversation(id_user, event_bot, message, variants)
            logging.debug("Completed single-choice question %d", question_number)
            res[question_id+1]=str(variants.index(answ)+1)
            logging.debug("Stored answer for question %d", question_number)
            question_number = question_number + 1
        elif type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.HEADER] or \
             type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.FOOTER] or \
             type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.REPORT]:            
            question_id=question_id+1
            continue
        elif type_questions.get(cur_question) == sts.TYPES_OF_QUESTONS[sts.TEXT]: # text
            cur_question = re.sub(r"ID4T_\d+_", "", cur_question)
            await bot.send_message(id_user, escape(str(cur_question)), parse_mode="html")
            question_id=question_id+1
            continue

        logging.debug("Questionnaire progress: %d questions", question_id + 1)
        question_id=question_id+1
        if res:
            answers.update(res)
        else:
            return False         
    #Show footer
    for cur_question,type_qst in type_questions.items():
        if type_qst == sts.TYPES_OF_QUESTONS[sts.FOOTER]: # footer
            if all_questions[cur_question]:
                path_to_file = await exist_file(all_questions[cur_question][0])                
            if path_to_file:
                await bot.send_file(id_user,file=path_to_file, caption=escape(str(cur_question)), parse_mode="html")
                path_to_file=''
            else:
                await bot.send_message(id_user, escape(str(cur_question)), parse_mode="html")
            break

    logging.debug("Collected answers for user %s", id_user)

    if answers:
        # Write Answers to DB
        async with dbm.DatabaseBot(sts.db_name) as db:     
                await db.db_add_answer(id_user, first_name, nickname, answers)
        #message=f"🔆 Вы ответили на все вопросы.\nРезультаты сохранены.\nДля повторного прохождения опроса\nнажмите кнопку Старт\n"

        #await bot.send_message(id_user, message)

        dt = datetime.now().strftime('%d%m%Y_%H%M%S')
        fname = str(REPORT_DIR / f"rpt_{id_user}_{dt}.pdf")
        logging.debug(f"Gen pdf filename: {fname}")
        await gen_pdf(answers,fname)
        message=_("📊 Ваш отчет")
        await bot.send_file( id_user, fname, caption=message, parse_mode="html" )
        #await asyncio.sleep(1) # Delay for user after send report and show menu
        if menu: 
            await create_admin_menu(menu, event_bot)

        return True
    
    return False

async def main_frontend():
    ''' 
    Create handlers for basic loop 
    '''
    
    #global all_questions

    @bot.on(events.NewMessage())
    async def bot_handler_nm_bot(event_bot):
        menu_level = 0
        if not event_bot.is_private or event_bot.sender_id is None:
            return
        id_user = event_bot.sender_id
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
        logging.debug("Get callback event for user[%s]", id_user)
       
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
            await send_excel_report(event_bot_choice)
            await create_admin_menu(menu_level, event_bot_choice)
        elif button_data == '/am_questions':
            await get_qusetion_data(event_bot_choice)
        elif button_data == '/am_show_questions':
            await show_qusetions(event_bot_choice)
        elif button_data == '/am_files':
             await create_menu_files(event_bot_choice)
             #await get_image(event_bot_choice)   
        elif button_data == '/am_add_admins':
            await add_admins(event_bot_choice)
        elif button_data == '/am_del_admins':
            await del_admins(event_bot_choice)
        elif button_data == '/am_show_admins':
            await show_admins(event_bot_choice)
        elif button_data.startswith('DEL_ADMIN_'):
            # Delete admin
            data = button_data
            try:
                admin_id_delete = int(data.removeprefix('DEL_ADMIN_'))
            except ValueError:
                await event_bot_choice.answer("Invalid administrator", alert=True)
                return
            if admin_id_delete not in sts.Admins or admin_id_delete in sts.Admin_ids:
                await event_bot_choice.answer("Administrator cannot be removed", alert=True)
                return
            async with dbm.DatabaseBot(sts.db_name) as db:
                await db.db_del_admins(admin_id_delete)
            logging.info("Administrator %s removed", admin_id_delete)
            sts.Admins.pop(admin_id_delete, None)
            message=_("🏁Админ ") + f"{admin_id_delete}" +_(" удален🏁")
            await event_bot_choice.respond(message)
            await create_admin_menu(menu_level, event_bot_choice)
        elif button_data == '/fm_list_images':
            exclude=[]
            exclude.append(sts.def_report_logo)
            await ui_list_files(event_bot_choice, 'images/', _('Список текущих изображений:\n'), exclude)
            await create_menu_files(event_bot_choice)
        elif button_data == '/fm_upl_images':
             await get_image(event_bot_choice)
             #await create_menu_files(event_bot_choice)
        elif button_data == '/fm_del_images':
            exclude=[]
            exclude.append(sts.def_report_logo)
            await ui_del_files(event_bot_choice, 'images/', _('Выберете файлы для удаления:'), exclude)
            await create_menu_files(event_bot_choice)  
        elif button_data == '/fm_list_reports':
            await ui_list_files(event_bot_choice, 'reports/', _('Список текущих отчетов:\n'))
            await create_menu_files(event_bot_choice)
        elif button_data == '/fm_del_reports':
            await ui_del_files(event_bot_choice, 'reports/', _('Выберете файлы для удаления:'))
            await create_menu_files(event_bot_choice)  
        elif button_data == '/fm_down_reports':
            await ui_get_files(event_bot_choice, 'reports/', _('Выберете файлы для получения:'))
            await create_menu_files(event_bot_choice)
        elif button_data == '/fm_list_qst':
            await ui_list_files(event_bot_choice, 'questionfiles/', _('Список файлов с вопросами:\n'))
            await create_menu_files(event_bot_choice)
        elif button_data == '/fm_del_qst':
            await ui_del_files(event_bot_choice, 'questionfiles/', _('Выберете файлы для удаления:'))
            await create_menu_files(event_bot_choice)
        elif button_data == '/fm_down_qst':
            await ui_get_files(event_bot_choice, 'questionfiles/', _('Выберете файлы для получения:'))
            await create_menu_files(event_bot_choice)
        elif button_data == '/fm_to_adm_menu':
            await create_admin_menu(0,event_bot_choice)

    return bot

async def main():
    ''' 
    Main function - start and initialize Bot
    
    '''

    print("Start anketa Bot...")
    
    # Check for Admin and get user_id, clear and create new dict Admins for 
    # full data about Admin
   
    sts.Admins.clear()
    if sts.Admin_ids:
        sts.Admins.update({admin_id: ("", "") for admin_id in sts.Admin_ids})
    else:
        raise RuntimeError("No administrator IDs configured")


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

        logging.info("Loaded %d database administrators", len(adm))

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
        logging.debug("Loaded report settings from validated questionnaire")
        

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

if os.path.isdir(localedir):
    translate = gettext.translation('anketa', localedir, [sts.Lang])
    _ = translate.gettext
else: 
    logging.info(f"No locale dir found for support langs: {localedir} \n Use default lang: Russian")
    def _(message): return message


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
