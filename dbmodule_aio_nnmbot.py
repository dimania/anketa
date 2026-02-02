'''
 Telegram Bot for filter films from NNMCLUB channel
 version 0.6
 Module dbmodule_nnmbot.py use aiosqlite Dbatabase functions  
'''

from datetime import datetime
import json
import logging
import os.path
import asyncio
import aiosqlite

import settings as sts

class DatabaseBot:

    def __init__(self, db_file):
        self.db_file = db_file
        self.lock = asyncio.Lock()

    async def __aenter__(self):
        self.dbm = await aiosqlite.connect(self.db_file)
        self.dbm.row_factory = aiosqlite.Row
        await self.dbm.execute("PRAGMA foreign_keys = ON")
        await self.dbm.commit()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.dbm.close()
   
    async def db_create( self ):
        ''' Creta DB if not exist '''

        # Create basic table Films
        await self.dbm.execute('''PRAGMA journal_mode=WAL''')  # Активация WAL

        await self.dbm.execute('''
        CREATE TABLE IF NOT EXISTS Questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        date TEXT
        )
        ''')
        # Ctreate table Users
        await self.dbm.execute('''
        CREATE TABLE IF NOT EXISTS Answers (
        id_user TEXT NOT NULL PRIMARY KEY,
        name_user TEXT NOT NULL,
        nick_user TEXT NOT NULL,
        question_id TEXT NOT NULL,
        answer_user TEXT NOT NULL,
        date TEXT NOT NULL
        )
        ''')
       

        await self.dbm.commit()

        return None

    async def db_modify(self, *args):
        ''' Update or insert data in db - common function'''

        global FAIL_MODIFY #for test raice condition - remove in prod
        for i in range(sts.RETRIES_DB_LOCK):
            try:
                async with self.lock:
                    async with self.dbm.execute(args[0],args[1]) as cursor:
                        await self.dbm.commit()
                        logging.debug(f"SQL MODIFY: result={str(cursor.rowcount)}" )
                        return cursor
            except aiosqlite.OperationalError as error:        
                logging.info(f"Retry modify records in db:{i} Error:{error}") 
                await asyncio.sleep(0.1)                  
            except aiosqlite.IntegrityError as error:               
                logging.error(f"DB Modify Error is: {error}")
                return -1            
        else: 
            logging.error(f"Error MODIFY data in DB! Retries pass:{i}")
            FAIL_MODIFY = FAIL_MODIFY + 1  #for test raice condition - remove in prod
            return None           
            
    async def db_add_answer(self, id_user, name_user, nick_user, question_id, answer_user):
        ''' Add new answer to database '''
        cur_date = datetime.now()

        cursor = await self.db_modify("INSERT INTO Answers (id_user, name_user, nick_user, question_id, answer_user, date) VALUES(?, ?, ?, ?, ?, ? )",\
                                ( id_user, name_user, nick_user, question_id, answer_user,cur_date ))
        if cursor: 
            #return str(cursor.lastrowid)
            return 'Ok'
        else:
            return None
    
    async def db_add_questions(self, question):
        ''' Add question to database '''
        cur_date = datetime.now()

        cursor = await self.db_modify("INSERT INTO Questions (question, date) VALUES(?, ? )",\
                                ( question,cur_date ))
        if cursor: 
            return str(cursor.lastrowid)
        else:
            return None
                        
    async def db_update_answer(self, id_user, name_user, nick_user, answer_user ):
        ''' Update Answer in database '''
        cur_date = datetime.now()
      
        cursor = await self.db_modify("UPDATE Films SET answer_user=?, date=? WHERE id_user = ?", \
                            (answer_user, cur_date ))
        if cursor:              
            logging.debug(f"SQL UPDATE FILM: id={id_user} result={str(cursor.rowcount)}" )
            return str(cursor.rowcount)
        else:
            return None

    async def db_exist_id_user(self, id_user):
        ''' Test exist user in database '''
        cursor = await self.dbm.execute("SELECT id FROM Answers WHERE id_user = ?", (id_user,))
        return await cursor.fetchone()

    async def get_last_answer_id(self, id_user):
        ''' Test exist user in database '''
        #SELECT column_name FROM table_name ORDER BY id_column DESC LIMIT 1;
        cursor = await self.dbm.execute("SELECT answer_id FROM Answers WHERE id_user = ? ORDER BY id DESC LIMIT 1", (id_user,))
        return await cursor.fetchone()
        
    async def db_info(self, id_user):
        ''' Get Info database: all records '''        
        cursor = await self.dbm.execute("SELECT COUNT(*) FROM Answers" )
        
        return await cursor.fetchall()

    async def db_list_all(self):
        ''' List all records form database '''
        cursor = await self.dbm.execute("SELECT name_user, nick_user, answer FROM Answers")
        return  await cursor.fetchall()

 