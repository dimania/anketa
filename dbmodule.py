'''
 Telegram Bot Anketing
 version 0.1
 Module dbmodule.py use aiosqlite Dbatabase functions  
'''

from datetime import datetime
#import json
import logging
#import os.path
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

        # Create basic table Questions
        await self.dbm.execute('''PRAGMA journal_mode=WAL''')  # Активация WAL

        await self.dbm.execute('''
        CREATE TABLE IF NOT EXISTS Admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INT NOT NULL UNIQUE,
        admin_nickname TEXT,
        admin_firstname TEXT,
        date TEXT
        )
        ''')
        await self.dbm.execute('''
        CREATE TABLE IF NOT EXISTS Questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INT NOT NULL UNIQUE,
        question_type TEXT,
        question TEXT NOT NULL,
        date TEXT
        )
        ''')

        await self.dbm.execute('''
        CREATE TABLE IF NOT EXISTS VariantsA (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INT,
        variant_id INT,                                            
        variant TEXT NOT NULL,
        date TEXT
        )
        ''')
        
        #,
        #FOREIGN KEY (question_id) REFERENCES Questions(id)

        # Ctreate table Answers
        await self.dbm.execute('''
        CREATE TABLE IF NOT EXISTS Answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_user TEXT NOT NULL,
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

        for i in range(sts.RETRIES_DB_LOCK):
            try:
                async with self.lock:
                    async with self.dbm.execute(args[0],args[1]) as cursor:
                        await self.dbm.commit()
                        logging.debug(f"SQL MODIFY: result={str(cursor.rowcount)}" )
                        break 
            except aiosqlite.OperationalError as error:        
                logging.info(f"Retry modify records in db:{i} Error:{error}") 
                await asyncio.sleep(0.1)                  
            except aiosqlite.IntegrityError as error:               
                logging.error(f"DB Modify Error is: {error}")
                return -1            
        else: 
            logging.error(f"Error MODIFY data in DB! Retries pass:{i}")
            return None           
        
        return cursor

    async def db_add_answer(self, id_user, name_user, nick_user, answers):
        ''' Add new answer to database '''
        cur_date = datetime.now()

        for ans in answers:
            cursor = await self.db_modify("INSERT INTO Answers (id_user, name_user, nick_user, question_id, answer_user, date) VALUES(?, ?, ?, ?, ?, ? )",\
                                ( id_user, name_user, nick_user, ans, dict(answers).get(ans),cur_date ))
        if cursor: 
            #return str(cursor.lastrowid)
            return True
        else:
            return False

    async def db_rewrite_new_questions(self, questions, type_questions):#FIXME dont write variants
        ''' Rewrite question on database from Array '''
        cur_date = datetime.now()
        #clear Previous Tables
        cursor = await self.dbm.execute("DELETE FROM Questions")
        cursor = await self.dbm.execute("DELETE FROM Answers")
        cursor = await self.dbm.execute("DELETE FROM VariantsA")
        await self.dbm.commit()
        #load new questions in the table Questions
        question_id=1
        for qst_one in questions:
            qst_type=type_questions.get(qst_one)
            cursor = await self.db_modify("INSERT INTO Questions (question_id, question_type, question, date) VALUES(?, ?, ?, ? )",\
                                    ( question_id, qst_type, qst_one,cur_date ))
            variant_id=1
            for variant in questions.get(qst_one):
                 if variant:
                    cursor = await self.db_modify("INSERT INTO VariantsA (question_id, variant_id, variant, date) VALUES(?, ?, ?, ? )",\
                                    ( question_id, variant_id, variant, cur_date ))
                    variant_id=variant_id+1
            question_id=question_id+1            
       
        if cursor: 
            return str(cursor.lastrowid)
        else:
            return None
                        
    async def db_load_questions(self):
        ''' Load all question in Array '''
        new_questions={}
        new_questions_type={}
        val=[]
        cursor = await self.dbm.execute("SELECT question_id, question_type, question FROM Questions")
        rows = await cursor.fetchall()
        logging.debug(f"Get questions len: {len(rows)}")

        if not rows: return False,False

        for row in rows:
            cursor = await self.dbm.execute("SELECT variant FROM VariantsA Where question_id = ?", (dict(row).get('question_id'),))
            rows_var = await cursor.fetchall()

            for row_variant in rows_var:
                # variants answer to list values dict        
                val.append(dict(row_variant).get('variant')) 
                
            new_questions[dict(row).get('question')]=val
            val=[]
            new_questions_type[dict(row).get('question')]=dict(row).get('question_type')

        logging.info(f"Get questions from db: {new_questions}")
        return new_questions_type, new_questions
    
    async def db_load_admins(self):
        ''' Load all question in Array '''
        new_admins=[]
        cursor = await self.dbm.execute("SELECT admin_id, admin_nickname, admin_firstname, date FROM Admins")
        rows = await cursor.fetchall()
        logging.debug(f"Get questions rows: {rows}")

        if rows:
            return rows
        else: 
            return False

    async def db_add_admins(self, new_admins):
        ''' Add admin in database 
            new_admin - dict key - user_id, vals - array [nickname][firstname]
        '''
        cur_date = datetime.now()
        
        #add new admins
        for admin_id, names in new_admins.items():
            cursor = await self.db_modify("INSERT INTO Admins (admin_id, admin_nickname, admin_firstname, date) VALUES(?, ?, ?, ? )",\
                                    ( admin_id,  names[0],  names[1], cur_date ))
        if cursor: 
            return str(cursor.lastrowid)
        else:
            return False
         
    async def db_del_admins(self, admin_id):
        ''' Remove admin from database for  admin_id'''
        cursor = await self.dbm.execute("DELETE FROM Admins WHERE admin_id = ?", (admin_id,))
        await self.dbm.commit()
        return await cursor.fetchall()

    async def db_update_answer(self, id_user, answer_user ): #NOTUSE
        ''' Update Answer in database '''
        cur_date = datetime.now()
      
        cursor = await self.db_modify("UPDATE Films SET answer_user=?, date=? WHERE id_user = ?", \
                            (answer_user, cur_date ))
        if cursor:              
            logging.debug(f"SQL UPDATE ANSWER: id={id_user} result={str(cursor.rowcount)}" )
            return str(cursor.rowcount)
        else:
            return None

    async def db_exist_id_user(self, id_user):
        ''' Test exist user in database '''
        cursor = await self.dbm.execute("SELECT id FROM Answers WHERE id_user = ?", (id_user,))
        return await cursor.fetchone()

    async def get_last_answer_id(self, id_user):#NOTUSE
        ''' Test exist user in database '''
        #SELECT column_name FROM table_name ORDER BY id_column DESC LIMIT 1;
        cursor = await self.dbm.execute("SELECT answer_id FROM Answers WHERE id_user = ? ORDER BY id DESC LIMIT 1", (id_user,))
        return await cursor.fetchone()
        
    async def db_info(self): #NOTUSE
        ''' Get Info database: all records '''        
        cursor = await self.dbm.execute("SELECT COUNT(*) FROM Answers" )
        
        return await cursor.fetchall()

    async def get_info_by_users(self):
        ''' List all users who answer for stats'''
        cursor = await self.dbm.execute("SELECT DISTINCT name_user, nick_user FROM Answers")
        rows =   await cursor.fetchall()
        logging.debug(f"Get users rows: {rows}")

        if not rows: 
            return False
        else: 
            return rows

    async def get_info_for_report(self):
        ''' List all records form database for report'''
        
        cursor = await self.dbm.execute("SELECT name_user, nick_user, question_id, answer_user, date FROM Answers")
        rows =   await cursor.fetchall()
        #logging.debug(f"Get data for reports: {rows}")

        if rows: 
            return rows
        else:
            return False

    async def db_del_user_answers(self, id_user):
        '''Delete all answers for user from database '''
        cursor = await self.dbm.execute("DELETE FROM Answers WHERE id_user = ?", (id_user,))
        await self.dbm.commit()
        return await cursor.fetchall()

