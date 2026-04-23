import sqlite3
import time
import uuid


class User_LTM_db():
    # -----------------------------
    # 1. Connect / Create DB
    # -----------------------------
    def get_curser(self):
        conn = sqlite3.connect("db/user.db",check_same_thread=False)
        cursor = conn.cursor()
        return conn, cursor

    # -----------------------------
    # 2. Check if table exists
    # -----------------------------
    def create_table_if_not_exists(self):
        conn, cursor = self.get_curser()
        cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='LTM'
        """)

        table = cursor.fetchone()

        if table is None:
            print("Creating LTM table...")
            cursor.execute("""
            CREATE TABLE LTM (
                user TEXT NOT NULL,
                LTM TEXT
            )
            """)
            conn.commit()
        else:
            print("Table already exists")
        conn.close()

    # -----------------------------
    # 3. Insert Chat
    # -----------------------------
    def create_LTM(self, user, LTM):
        conn, cursor = self.get_curser()

        cursor.execute("""
        INSERT INTO LTM (user, LTM)
        VALUES (?, ?)
        """, (user, LTM))

        conn.commit()
        conn.close()

    # -----------------------------
    # 4. Get All LTMs for User
    # -----------------------------
    def get_user_LTM(self, user):
        conn, cursor = self.get_curser()

        self.create_table_if_not_exists()

        cursor.execute("""
        SELECT LTM
        FROM LTM
        WHERE user = ?
        """, (user,))

        record_li = cursor.fetchall()
        if len(record_li) == 0:
            self.create_LTM(user, "")
            cursor.execute("""
                    SELECT LTM
                    FROM LTM
                    WHERE user = ?
                    """, (user,))
            record_li = cursor.fetchall()

        conn.close()

        return record_li

    def update_LTM(self, user, LTM):
        conn, cursor = self.get_curser()
        cursor.execute("""
        UPDATE LTM
        SET LTM = ?
        WHERE user = ?
        """, (LTM, user))

        conn.commit()

        # optional: check if update happened
        if cursor.rowcount == 0:
            print("No chat found with this thread_id")
        else:
            print("Chat name updated successfully")
        conn.close()


class User_chat_db():
    # -----------------------------
    # 1. Connect / Create DB
    # -----------------------------
    def get_curser(self):
        conn = sqlite3.connect("db/user.db",check_same_thread=False)
        cursor = conn.cursor()
        return conn, cursor

    # -----------------------------
    # 2. Check if table exists
    # -----------------------------
    def create_table_if_not_exists(self):
        conn, cursor = self.get_curser()
        cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='chats'
        """)

        table = cursor.fetchone()

        if table is None:
            print("Creating chats table...")
            cursor.execute("""
            CREATE TABLE chats (
                thread_id TEXT PRIMARY KEY,
                user TEXT NOT NULL,
                chatname TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()
        else:
            print("Table already exists")
        conn.close()

    # -----------------------------
    # 3. Insert Chat
    # -----------------------------
    def create_chat(self, thread_id, user, chatname):
        conn, cursor = self.get_curser()
        self.create_table_if_not_exists()

        cursor.execute("""
        INSERT INTO chats (thread_id, user, chatname)
        VALUES (?, ?, ?)
        """, (thread_id, user, chatname))

        conn.commit()
        conn.close()
        print("record inserted")

    # -----------------------------
    # 4. Get All Chats for User
    # -----------------------------
    def get_user_chats(self, user):
        conn, cursor = self.get_curser()
        cursor.execute("""
        SELECT thread_id, chatname, created_at
        FROM chats
        WHERE user = ?
        ORDER BY created_at DESC
        """, (user,))

        thread_li = cursor.fetchall()

        cursor.close()

        return thread_li

    # -----------------------------
    # 5. Get Single Chat
    # -----------------------------
    def get_chat(self, thread_id):
        conn, cursor = self.get_curser()
        cursor.execute("""
        SELECT * FROM chats WHERE thread_id = ?
        """, (thread_id,))
        all_chat = cursor.fetchone()
        print(list(all_chat))
        cursor.close()

        return all_chat

    def update_chatname(self, thread_id, new_chatname):
        conn, cursor = self.get_curser()
        cursor.execute("""
        UPDATE chats
        SET chatname = ?
        WHERE thread_id = ?
        """, (new_chatname, thread_id))

        conn.commit()

        # optional: check if update happened
        if cursor.rowcount == 0:
            print("No chat found with this thread_id")
        else:
            print("Chat name updated successfully")
        cursor.close()



# ===== MOCK DB =====
class user_db():
    def get_curser(self):
        conn = sqlite3.connect("db/user.db",check_same_thread=False)
        cursor = conn.cursor()
        return conn, cursor

    def create_table_if_not_exists(self):
        conn, cursor = self.get_curser()
        cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='users'
        """)

        table = cursor.fetchone()

        if table is None:
            self.init_db()
        else:
            print("Table already exists")
        cursor.close()

    def get_db(self):
        conn = sqlite3.connect("db/user.db",check_same_thread=False)
        conn.row_factory = sqlite3.Row  # return dict-like rows
        return conn


    def init_db(self):
        conn = self.get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                token TEXT
            )
        """)
        conn.commit()
        conn.close()


    # init_db()

    def create_user(self, username, password, token):
        id = str(int(time.time()))
        conn = self.get_db()
        try:
            conn.execute(
                "INSERT INTO users (id, username, password, TOKEN) VALUES (?, ?, ?, ?)",
                (id, username, password, token)
            )
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()


    def check_user(self, username, password=''):
        conn = self.get_db()
        user = conn.execute(
            "SELECT count(*) as count FROM users WHERE username = ? and password = ?",
            (username, password,)
        ).fetchone()
        print(user['count'])
        conn.close()
        return user

    def check_token(self, token):
        conn = self.get_db()
        user = conn.execute(
            "SELECT username FROM users WHERE token=? ",
            (token,)
        ).fetchone()
        conn.close()
        if user:
            print("user token", user['username'])
            return user['username']
        else:
            return None

    def get_user(self, username, password=''):
        conn = self.get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? and password = ?",
            (username, password,)
        ).fetchone()
        print("get user", user)
        conn.close()
        return user


    def update_user(self, username, token):
        idd = str(int(time.time()))
        conn = self.get_db()
        conn.execute(
            "UPDATE users SET id = ?, TOKEN = ? WHERE username = ?",
            (idd, token, username)
        )
        conn.commit()
        conn.close()


    def delete_user(self):
        conn = self.get_db()
        conn.execute(
            "DELETE FROM users"
        )
        conn.commit()
        conn.close()
    # delete_user()
