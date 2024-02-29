import sqlite3

def get_user_by_id(id_utente):
    query = 'SELECT * FROM UTENTI WHERE id=?'
    connection = sqlite3.connect('db/db.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute(query, (id_utente,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result

def new_user(nuovo_utente):
    query = 'INSERT INTO UTENTI(nome,cognome,email,hash) VALUES(?,?,?,?)'
    connection=sqlite3.connect('db/db.db')
    connection.row_factory= sqlite3.Row
    cursor=connection.cursor()
    success=False

    try:
        cursor.execute(query,(nuovo_utente['nome'],nuovo_utente['cognome'],nuovo_utente['email'],nuovo_utente['hash']))
        connection.commit()
        success=True
    except Exception as e:
        print('Error', str(e))
        connection.rollback()

    cursor.close()
    connection.close()
    return success

def find_user(email_utente):
    query='SELECT * FROM UTENTI WHERE email=?'
    connection = sqlite3.connect('db/db.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute(query, (email_utente,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result

