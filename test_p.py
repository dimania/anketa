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
        return df.to_string(index=False,header=False,justify='left')
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

def main():
    ss={}
    ss['u_id1'] = ['u_nick'],['u_fname']
    ss2={}
    ss2['u_id2'] = ['u_nick2'],['u_fname2']
    ss3={}
    ss3k='u_id2'
    ss3_0='u_nick3'
    ss3_1='u_fname3'

    ss3[ss3k]=[ss3_0],[ss3_1]
    print(f"ss3->{ss3}")

    for user_id,nicks in ss.items():
        print(f'{user_id}->{nicks[1]}\n')

    #ss.clear()
    ss.update(ss2)
    print(f"ss->{ss} {len(ss)}")

    if ss2:
        print('ss2 True')
    else:
        print('ss2 false')


    exit(0)

    filename='test_formats/Анкета.docx'
    
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
        print(text_content)
    
    
    print("-------------------------------")
    
    qlist = [item.strip() for item in text_content.split('\n')]
    qlist = list(filter(None, qlist))
    i=0
    for str in qlist:
        print(f"[{i}]{str}")
        i=i+1


if __name__ == '__main__':
    main()
