import sqlite3

def get_raccolte():
    query="SELECT RACCOLTE.id, titolo, descrizione, immagine, obiettivo, donazione_min, donazione_max, id_utente, tipo, timestamp_creazione, timestamp_chiusura, SUM(cifra_donata) AS cifra_totale_donata FROM RACCOLTE LEFT OUTER JOIN DONATORI ON RACCOLTE.id=id_raccolta GROUP BY RACCOLTE.id, titolo, descrizione, immagine, obiettivo, donazione_min, donazione_max, id_utente, tipo, timestamp_creazione, timestamp_chiusura"
    connection=sqlite3.connect('db/db.db')
    connection.row_factory=sqlite3.Row
    cursor=connection.cursor()
    cursor.execute(query)
    result=cursor.fetchall()
    cursor.close()
    connection.close()
    return result


def get_raccolta(id):
    query="SELECT RACCOLTE.id, titolo, descrizione, immagine, obiettivo, donazione_min, donazione_max, id_utente, tipo, timestamp_creazione, timestamp_chiusura, SUM(cifra_donata) AS cifra_totale_donata FROM RACCOLTE LEFT OUTER JOIN DONATORI ON RACCOLTE.id=id_raccolta WHERE RACCOLTE.id = ?"
    connection=sqlite3.connect('db/db.db')
    connection.row_factory=sqlite3.Row
    cursor=connection.cursor()
    cursor.execute(query,(id,))
    result=cursor.fetchone()
    cursor.close()
    connection.close()
    return result

def add_raccolta(raccolta):
    conn = sqlite3.connect('db/db.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    success = False
    if 'immagine' in raccolta:
        query = 'INSERT INTO RACCOLTE(titolo,descrizione,immagine,obiettivo,donazione_min,donazione_max,id_utente,tipo,timestamp_creazione,timestamp_chiusura) VALUES(?,?,?,?,?,?,?,?,?,?)'
        cursor.execute(query,(raccolta['titolo'],raccolta['descrizione'],raccolta['immagine'],raccolta['obiettivo'],raccolta['donazione_min'],raccolta['donazione_max'],raccolta['id_utente'],raccolta['tipo'],raccolta['timestamp_creazione'],raccolta['timestamp_chiusura']))
    else:
        query = 'INSERT INTO RACCOLTE(titolo,descrizione,obiettivo,donazione_min,donazione_max,id_utente,tipo,timestamp_creazione,timestamp_chiusura) VALUES(?,?,?,?,?,?,?,?,?)'
        cursor.execute(query,(raccolta['titolo'],raccolta['descrizione'],raccolta['obiettivo'],raccolta['donazione_min'],raccolta['donazione_max'],raccolta['id_utente'],raccolta['tipo'],raccolta['timestamp_creazione'],raccolta['timestamp_chiusura']))
    try:
        conn.commit()
        success = True
    except Exception as e:
        print('ERROR', str(e))
        conn.rollback()

    cursor.close()
    conn.close()

    return success


def get_raccolte_by_id_utente(id_utente):
    query="SELECT RACCOLTE.id, titolo, descrizione, immagine, obiettivo, donazione_min, donazione_max, id_utente, tipo, timestamp_creazione, timestamp_chiusura, SUM(cifra_donata) AS cifra_totale_donata FROM RACCOLTE LEFT OUTER JOIN DONATORI ON RACCOLTE.id=id_raccolta WHERE id_utente=? GROUP BY RACCOLTE.id, titolo, descrizione, immagine, obiettivo, donazione_min, donazione_max, id_utente, tipo, timestamp_creazione, timestamp_chiusura"
    connection=sqlite3.connect('db/db.db')
    connection.row_factory=sqlite3.Row
    cursor=connection.cursor()
    cursor.execute(query,(id_utente,))
    result=cursor.fetchall()
    cursor.close()
    connection.close()
    return result


def delete_raccolta(id_raccolta):
    connection=sqlite3.connect('db/db.db')
    connection.row_factory=sqlite3.Row
    cursor=connection.cursor()
    success=False
    try:
        # Inizia la transazione
        connection.execute('BEGIN TRANSACTION')

        # Esegui le operazioni della transazione
        cursor.execute("DELETE FROM DONATORI WHERE id_raccolta=?",(id_raccolta,))
        cursor.execute("DELETE FROM RACCOLTE WHERE id=?",(id_raccolta,))

        # Commit della transazione
        connection.commit()
        success=True
    except sqlite3.Error as e:
        # Rollback in caso di errore
        print('ERROR', str(e))
        connection.rollback()
    cursor.close()
    connection.close()
    
    return success


def update_raccolta(new_raccolta):
    connection=sqlite3.connect('db/db.db')
    connection.row_factory=sqlite3.Row
    cursor=connection.cursor()
    success=False
    query="UPDATE RACCOLTE SET titolo=?, descrizione=?, immagine=?, obiettivo=?, donazione_min=?, donazione_max=?, tipo=?, timestamp_chiusura=? WHERE id=?"
    try:
        cursor.execute(query,(new_raccolta['titolo'], new_raccolta['descrizione'], new_raccolta['immagine'], new_raccolta['obiettivo'], new_raccolta['donazione_min'], new_raccolta['donazione_max'], new_raccolta['tipo'], new_raccolta['timestamp_chiusura'], new_raccolta['id']))
        connection.commit()
        success=True
    except sqlite3.Error as e:
        # Rollback in caso di errore
        print('ERROR', str(e))
        connection.rollback()

    cursor.close()
    connection.close()    

    return success