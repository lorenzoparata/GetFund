import sqlite3

def get_donatori_by_id_raccolta(id_raccolta):
    query="SELECT * FROM DONATORI WHERE id_raccolta=?"
    connection=sqlite3.connect('db/db.db')
    connection.row_factory=sqlite3.Row
    cursor=connection.cursor()
    cursor.execute(query,(id_raccolta,))
    result=cursor.fetchall()
    cursor.close()
    connection.close()
    return result


def add_donatore(donatore):
    
    connection=sqlite3.connect('db/db.db')
    connection.row_factory= sqlite3.Row
    cursor=connection.cursor()
    success=False
    query='INSERT INTO DONATORI(nome,cognome,cifra_donata,id_raccolta) VALUES(?,?,?,?)'
    try:
        cursor.execute(query,(donatore['nome'],donatore['cognome'],donatore['cifra_donata'],donatore['id_raccolta']))
        connection.commit()
        success=True
    except Exception as e:
        print('Error', str(e))
        connection.rollback()
    cursor.close()
    connection.close()
    return success