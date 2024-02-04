import sqlite3

def get_user(email):
    query = 'SELECT * FROM utenti WHERE email = ?'
    with sqlite3.connect('db.db') as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        try:
            return cursor.execute(query, (email,)).fetchone()
        finally:
            cursor.close()

def register_user(user):
    query = 'INSERT INTO utenti(email, password, Tipo) VALUES (?,?,?)'

    with sqlite3.connect('db.db') as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        try:
            cursor.execute(query, (user['email'], user['password'], user['Tipo']))
            connection.commit()
            return True
        except Exception as e:
            print('Error', str(e))
            connection.rollback()
            return False
        finally:
            cursor.close()