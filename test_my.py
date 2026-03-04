#
# ENV TZ=America/Los_Angeles
# ENV TZ=Europe/Moscow
# RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
#
import io
import re
import logging
import asyncio
import os.path
import sys
import gettext
import json
import filetype
from datetime import datetime

import filetype
import docx
import pandas as pd
import numpy as np
import math
from collections import defaultdict
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
   

    # Init collums for question
    for qst in  all_questions.keys():
        data_ws2[qst]=[]

    
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
            data['answer_user'].append(all_questions.get(key_q)[int(answer_cur)-1])
            data_ws2[key_q].append(all_questions.get(key_q)[int(answer_cur)-1])
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
    workbook = writer.book
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

def is_text_file(filename, blocksize=512):
    """
    Heuristically checks if a file is a text file by reading the first block.
    """
    # Empty files are considered text
    if os.path.getsize(filename) == 0:
        print('tset1')
        return True

    with open(filename, 'rb') as f:
        block = f.read(blocksize)
    print(block)
    # A file is binary if it contains a null byte
    if b'\x00' in block:
        print('tset2')
        return False

    # Check the ratio of non-text characters (e.g., control codes)
    # The definition of "text characters" can vary, but ASCII printable
    # characters plus common whitespace is a good start.
    text_chars = bytes(range(32, 127)) + b'\n\r\t\b'
    # Use a translation table to count non-text characters efficiently
    non_text_count = block.translate(None, text_chars)

    # If more than 30% of the buffer consists of non-text characters, consider it binary
    if len(non_text_count) / len(block) > 0.3:
        print('tset3')
        return False
        
    return True

def is_utf8_text_file(file_path):
    """Checks if a file can be entirely decoded as UTF-8 text."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file.read()
        return True
    except UnicodeDecodeError:
        # This exception is raised if the file contains byte sequences 
        # that are invalid for UTF-8 encoding.
        return False
    except Exception as e:
        # Handle other potential exceptions (e.g., file not found, permission errors)
        print(f"An error occurred: {e}")
        return False

def get_excel_text(filename, sheet_name=0):
    """
    Reads data from an Excel file into a pandas DataFrame.
    sheet_name can be an integer (0 for the first sheet) or a string ('Sheet1').
    """
    try:
        df = pd.read_excel(filename, sheet_name=sheet_name, header=None )
        # Convert the DataFrame to a string representation (e.g., for printing or writing to a text file)
        #return df.to_string(index=False,header=False,justify='left')
        return df.to_dict(orient='split', index=False)
    except Exception as e:
        return f"Error reading Excel file: {e}"

def get_word_text(filename):
    """
    Extracts all text from a .docx file.
    """
    document = docx.Document(filename)
    full_text = []
    for paragraph in document.paragraphs:
        full_text.append(paragraph.text)
    # Join paragraphs with a newline character
    return '\n'.join(full_text)
    #return full_text

def get_oldword_text(filename): #FIXME Its dont work
    """
    Extracts all text from old a .doc file.
    """
    # OLD word file - .doc
       # Convert the document and extract text
       
    #text = docx2txt.process(filename) 
    #return text
    pass
    return None
    
def get_txt_text(filename):
    '''
    Docstring для get_txt_text
    Get data fron text file 
    :param filename: Описание
    '''
    with open(filename, 'r', encoding="utf-8") as file:
                #text = text + [for line in file.readlines()]
                text=file.read()
    
    return text

def conversion_example():
    @bot.on(events.NewMessage(pattern='/test'))  
    async def worklogs(event):        
        chat_id = event.message.chat.id    
        sender = await event.get_sender()
        sender_id = sender.id

        
        async with bot.conversation(chat_id) as conv:
            
            
            def my_press_event(user_id):
                return events.CallbackQuery(func=lambda e: e.sender_id == user_id)

            buttons = [[Button.inline('Yes'), Button.inline('No')]]
            await conv.send_message('To be or not no be? Answer yes|no, or write your own opinion', buttons=buttons)
        
            tasks = [conv.wait_event(my_press_event(sender_id)), conv.get_response()]
            done, pendind = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            event = done.pop().result()
            
            if type(event) is events.callbackquery.CallbackQuery.Event:
                selected = event.data.decode('utf-8')
                print(f'Got button: "{selected}"')
            elif type(event) is tl.patched.Message: 
                message = event.text
                print(f'Got text message: "{message}"')

def test_ret_arrays():
    ad={}
    ad['u_id1'] = ['u_nick','u_fname']
    ad['u_id2'] = 'u_nick','u_fname'
    ad1=[]
    ad1=['u_nick1','u_fname1']
    return ad,ad1

def main():
    ss={}
    ss['u_id1'] = 'u_nick','u_fname'
    ss2={}
    ss2['u_id2'] = 'u_nick2','u_fname2'
    ss3={}
    ss3k='12345'
    ss3_0='u_nick3'
    ss3_1='u_fname3'
    ad=[]
    ad1=[]
    ss3[1]=['1','2','4']

    all_questions = {   
                    "text_q1":[],
                    "text multi select here":[],
                    "text_q2":['variant1','variant2','variant3','variant4'],
                    "text_q3":['variant1'],
                    "text only one here":[],
                    "text_q4":['variant1','variant2','variant3'],
                    "text_q5":[],
                    "🔆 Вы ответили на все вопросы.\nРезультаты сохранены.\nДля повторного прохождения опроса\nнажмите кнопку Старт\n":['congratulation.jpg'],
                    "header is header!":['logo.jpg']
                }
    type_questions = {  "header is header!":"header",
                    "text_q1":"simple",
                    "text multi select here":"text",
                    "text_q2":"select",
                    "text_q3":"onlyone",
                    "text only one here":"text",
                    "text_q4":"onlyone",
                    "text_q5":"simple",
                    "🔆 Вы ответили на все вопросы.\nРезультаты сохранены.\nДля повторного прохождения опроса\nнажмите кнопку Старт\n":"footer"
                }

    i = 3
    data=defaultdict(list)
    data[0]=' '
    temp_dict={}
    for qst,type in type_questions.items():
        #variants=all_questions[cur_question]
        print(f"cur={qst} - > var={type}\n")
        if type == 'header':
            print(f"FROM ALL QST={all_questions[qst]}\n")
            val=all_questions.pop(qst)
            temp_dict[qst]=val
    #all_questions[add_qst]=val
    new_dict = {**temp_dict, **all_questions}
    print(f"new all_qst {all_questions}\n{new_dict}")

    exit(0)



    ad,ad1 = test_ret_arrays()
    #print(f"ad={ad}\nad1={ad1}\n")

    asss="VARIANT_1_1"
    axxx="ANSWER_1_1"
    print(axxx.find('ANSWER_'))

    #exit(0)
    print(f"Append ss->{ss['u_id1'].append('wwwww')}")

    print(f"Orig ss->{list(ss)[0]}")
    key=list(ss)[0]
    print(f"Orig ss->{ss.get(key)[1]}")
    #for user_id,nicks in ss.items():
    #    print(f'{user_id}->{ nicks[1] }\n')
    exit(0)
    #ss.clear()
    ss.update(ss2)
    #print(f"Update ss to ss2  ->{ss} {len(ss)}")
    ss.update(ss3)

    #print(f"Update ss to ss2 ss3 ->{ss} {len(ss)}")

    aa='12345'
    bb=str(aa)
    #ss.pop(str(aa))

    #print(f"After pop ss->{ss} {len(ss)}")

    if ss2:
        #print('ss2 True')
        pass
    else:
        #print('ss2 false')
        pass


    

    filename='questionfiles/Анкета2.xls'
    
    root,ext = os.path.splitext(filename)
    
    kind = filetype.guess(filename)
    
    #if kind is None:
    #    print('Cannot guess file type!')
    #    return 1

    #print('File extension: %s' % kind.extension)
    #print('File MIME type: %s' % kind.mime)

    if ext == '.txt' and is_utf8_text_file(filename):
        text_content = get_txt_text(filename)
        print(text_content)
    elif kind is None:
        print('Cannot guess file type!')
        return 1
    elif kind.extension == 'docx': 
        text_content = get_word_text(filename)
        print(text_content)
    elif kind.extension == 'doc':
        text_content = get_oldword_text(filename)
        print(text_content)
    elif kind.extension == 'xlsx' or kind.extension == 'xls':
        text_content = get_excel_text(filename)
        #print(text_content)
    
    
    print("-------------------------------")
    list_q={}
    val=[]
    for item in text_content['data']:
        #item - one question and variants answers if exist
        nan_list=pd.isna(item)
        i=False
        # variants answer to list values dict        
        for x, y in zip(item,nan_list):
            if not y and i:
                val.append(x) 
            i=True
        
        list_q[item[0]]=val
        val=[]
    print(list_q)

    for key in list_q:
        print(f'{key}:\n')
        if list_q.get(key):
            print('Exist variants')
        else:
            print('Not Exist variants')
        for val in list_q.get(key):
            print(f'{val} ')

    exit(0)


    qlist = [item.strip() for item in text_content.split('\n')]    
    qlist = list(filter(None, qlist))
    i=0
    for string in qlist:
        print(f"[{i}]{string}")
        i=i+1

#'name_user':   ['Murhuhu',    'Murhuhu',  '',         '',         '',          'Murhuhu',   '',             'Murhuhu',  '',     'Murhuhu'], 
#'nick_user':   ['murhuhu',    'murhuhu',  '',         '',         '',          'murhuhu',   '',             'murhuhu',  '',     'murhuhu'], 
#'question':    ['text_q1',    'text_q2',  '',         '',         '',          'text_q3',   '',             'text_q4',  '',     'text_q5'], 
#'answer_user': ['test1',      'variant1', 'variant2', 'variant4', 'variant1',  'variant2',  'test5'], 
#'date':        ['19.02.2026', '',         '',         '',         '19.02.2026','',          '19.02.2026',    '',         '19.02.2026', '19.02.2026'], 
#'time':        ['14:53',      '',         '',         '',         '14:53',     '',           '14:53',        '',            '14:53',    '14:53']
{
    'text_q1':   ['test1'], 
    'name_user': ['Murhuhu',    '',         ''], 
    'nick_user': ['murhuhu',    '',         ''], 
    'date':      ['19.02.2026', '',         ''], 
    'time':      ['14:53',      '',         ''], 
    'text_q2':   ['variant1',   'variant2', 'variant4'], 
    'text_q3':   ['variant1'], 
    'text_q4':   ['variant2'], 
    'text_q5':   ['test5']
}

{'name_user': ['Murhuhu', '', ''], 
 'nick_user': ['murhuhu', '', ''], 
 'date': ['19.02.2026', '', ''], 
 'time': ['14:53', '', ''], 
 'text_q1': ['test1'], 
 'text_q2': ['variant1', 'variant2', 'variant4'], 
 'text_q3': ['', '', 'variant1'], 
 'text_q4': ['', '', 'variant2'], 
 'text_q5': ['', '', 'test5']}

            
if __name__ == '__main__':
    main()
