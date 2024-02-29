from flask import Flask, render_template, request, url_for,redirect,flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import User
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import date, datetime, timedelta
import utenti_dao
import raccolte_dao
import donatori_dao
import re

from PIL import Image

RACCOLTA_IMG_WIDTH = 500
N_words_in_paragraph_home_page=40
N_words_in_paragraph_profilo=25

app=Flask(__name__)
app.config['SECRET_KEY'] = 'secret key di GetFund'

login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/')
def home_page():
    raccolte = raccolte_dao.get_raccolte() #ottengo tutte le raccolte sia aperte che chiuse, con nessun tipo di ordinamento nei campi
    raccolte_mod=[dict(row) for row in raccolte] #risultato modificabile
    raccolte_aperte_ordinate=[]
    
    #bisogna filtrare le raccolte per capire quali sono aperte e ordinarle per tempo di chiusura crescente
    
    for raccolta in raccolte_mod:
        if raccolta['cifra_totale_donata'] is None:
            raccolta['cifra_totale_donata'] = 0 #inizializzo in cui delle raccolte non abbiano ricevuto delle donazioni
        if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') > datetime.now():    #seleziono quelle ancora aperte
            raccolte_aperte_ordinate.append(raccolta)
        
    raccolte_aperte_ordinate = sorted(raccolte_aperte_ordinate, key=lambda x: datetime.strptime(x['timestamp_chiusura'], '%Y-%m-%d %H:%M').strftime("%Y-%m-%d %H:%M"), reverse=False)

    for raccolta in raccolte_aperte_ordinate:
        differenza=datetime.strptime(raccolta['timestamp_chiusura'], "%Y-%m-%d %H:%M")-datetime.now()
        raccolta['giorni_mancanti']=differenza.days
        raccolta['ore_mancanti']=differenza.seconds//3600   #quoziente dalla divisione di 1 ora (3600 secondi)
        raccolta['minuti_mancanti']= (differenza.seconds%3600)//60  #resto dalla divisione per 1 ora (3600 secondi) e ricavo quoziente dalla divisione per 1 minuto(60 secondi)

        raccolta['descrizione'] = (' '.join(raccolta['descrizione'].split()[:N_words_in_paragraph_home_page]))+'...'
        if raccolta['cifra_totale_donata']>=raccolta['obiettivo']:
            raccolta['progress_bar'] = '100%'
        else:
            percentuale_avanzamento = (raccolta['cifra_totale_donata'] / raccolta['obiettivo']) * 100
            raccolta['progress_bar'] = f"{percentuale_avanzamento:.0f}%"

    return render_template('homepage.html', raccolte=raccolte_aperte_ordinate)



@app.route('/registrazione')
def registrazione_page():
    return render_template('registrazione.html')

@login_manager.user_loader
def load_user(user_id):
    db_user = utenti_dao.get_user_by_id(user_id)
    user= User(id=db_user['id'], nome=db_user['nome'], cognome=db_user['cognome'], email=db_user['email'], hash=db_user['hash'])
    return user

@app.route('/registrazione', methods=['POST'])
def registrazione_form():
    new_user_from_form=request.form.to_dict()

    user_in_db = utenti_dao.find_user(new_user_from_form.get('email'))

    if user_in_db:
        flash('C\'è già un utente registrato con questa email', 'danger')
        return redirect(url_for('registrazione_page'))
    
    if new_user_from_form['nome'] == '':
        app.logger.error('Il campo nome non può essere vuoto')
        return redirect(url_for('registrazione_page'))
    
    if new_user_from_form['cognome'] == '':
        app.logger.error('Il campo cognome non può essere vuoto')
        return redirect(url_for('registrazione_page'))
    
    if new_user_from_form['email'] == '':
        app.logger.error('Il campo email non può essere vuoto')
        return redirect(url_for('registrazione_page'))
    if new_user_from_form['hash'] == '':
        app.logger.error('Il campo nuova password non può essere vuoto')
        return redirect(url_for('registrazione_page'))
    if new_user_from_form['hash2'] == '':
        app.logger.error('Il campo conferma password non può essere vuoto')
        return redirect(url_for('registrazione_page'))
    
    if new_user_from_form['hash2'] != new_user_from_form['hash']:
        flash('Le due password non coincidono.', 'danger')
        return redirect(url_for('registrazione_page'))
    
    new_user_from_form['hash']=generate_password_hash(new_user_from_form['hash'])

    success=utenti_dao.new_user(new_user_from_form)
    if success:
        flash('Utente creato correttamente', 'success')
        return redirect(url_for('home_page'))
    else:
        flash('Errore nella creazione del utente: riprova!', 'danger')
        return redirect(url_for('registrazione_page'))

@app.route('/login', methods=['POST'])
def login():
    user_form=request.form.to_dict()
    user_db=utenti_dao.find_user(user_form['email'])
    if not user_db or not check_password_hash(user_db['hash'],user_form['hash']):
        flash('Credenziali non valide, riprova', 'danger')
        return redirect(url_for('home_page'))
    new=User(id=user_db['id'],nome=user_db['nome'],cognome=user_db['cognome'],email=user_db['email'],hash=user_db['hash'])
    login_user(new,True)
    flash('Bentornato ' + user_db['nome'] + '!', 'success')
    return redirect(url_for('home_page'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home_page'))

@app.route('/raccolta_fondi_<int:id>')
def singola_raccolta_fondi(id):
    raccolta= raccolte_dao.get_raccolta(id)
    if not raccolta:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Raccolta non trovata')
        return redirect(url_for('home_page'))
    raccolta_dict=dict(raccolta)    #modificabile
    if raccolta_dict['cifra_totale_donata'] is None:
        raccolta_dict['cifra_totale_donata'] = 0    #in caso di raccolte senza aver ricevuto donazioni

    if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():    #raccolta chiusa
        raccolta_dict['bottone_dona_attivo'] = False
    else:
        raccolta_dict['bottone_dona_attivo'] = True

    raccolta_dict['timestamp_chiusura']=datetime.strptime(raccolta['timestamp_chiusura'], "%Y-%m-%d %H:%M").strftime("%d-%m-%Y %H:%M")
    raccolta_dict['timestamp_creazione']=datetime.strptime(raccolta['timestamp_creazione'], "%Y-%m-%d %H:%M").strftime("%d-%m-%Y %H:%M")

    if raccolta_dict['cifra_totale_donata']>=raccolta_dict['obiettivo']:
        raccolta_dict['progress_bar'] = '100%'
    else:
        percentuale_avanzamento = (raccolta_dict['cifra_totale_donata'] / raccolta_dict['obiettivo']) * 100
        raccolta_dict['progress_bar'] = f"{percentuale_avanzamento:.0f}%"
    


    utente = utenti_dao.get_user_by_id(raccolta['id_utente'])   #organizzatore della raccolta fondi
    if not utente:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Utente non trovato')
        return redirect(url_for('home_page'))
    donatori=donatori_dao.get_donatori_by_id_raccolta(raccolta['id'])

    return render_template('singola_raccolta_fondi.html',utente=utente,raccolta=raccolta_dict,donatori=donatori)

@app.route('/raccolta_fondi_<int:id>/donazione')
def donazione(id):
    raccolta= raccolte_dao.get_raccolta(id)
    if not raccolta:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Raccolta non trovata')
        return redirect(url_for('home_page'))
    utente = utenti_dao.get_user_by_id(raccolta['id_utente'])
    if not utente:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Utente non trovata')
        return redirect(url_for('home_page'))
    
    if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():
        flash('La raccolta fondi è terminata, non è possibile effettuare donazioni', 'danger')
        return redirect(url_for('singola_raccolta_fondi',id=id)) #la raccolta esiste a questo punto del codice, quindi reindirizzo alla pagina della singola raccolta fondi
    return render_template('donazione.html',raccolta=raccolta,utente=utente)


@app.route('/donazione_form', methods=['POST'])
def donazione_form():
    donazione_form=request.form.to_dict()

    if 'id_raccolta' not in donazione_form or not donazione_form['id_raccolta'].isdigit:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Errore durante la donazione, riprova!')
        return redirect('home_page')
    
    raccolta= raccolte_dao.get_raccolta(donazione_form['id_raccolta'])

    if raccolta is None:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error("Errore durante la donazione, riprova!")
        return redirect('home_page')

    if float(donazione_form['cifra_donata']) < float(raccolta['donazione_min']) or float(donazione_form['cifra_donata']) > float(raccolta['donazione_max']):
        app.logger.error('La cifra donata non è compatibile con le specifiche imposte dal gestore della raccolta fondi')
        return redirect(url_for('donazione',id=raccolta['id']))
    
    if donazione_form['nome'] == '':
        app.logger.error('Il campo nome non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))
    
    if donazione_form['cognome'] == '':
        app.logger.error('Il campo cognome non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))
    
    if donazione_form['indirizzo'] == '':
        app.logger.error('Il campo indirizzo non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))

    if donazione_form['email'] == '':
        app.logger.error('Il campo email non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))

    if donazione_form['nome_intestatario'] == '':
        app.logger.error('Il campo nome intestatario non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))
    if donazione_form['cognome_intestatario'] == '':
        app.logger.error('Il campo cognome intestatario non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))

    if donazione_form['numero_carta'] == '':
        app.logger.error('Il campo numero carta non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))
    
    if donazione_form['data_scadenza'] == '':
        app.logger.error('Il campo data scadenza non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))
    
    if donazione_form['cvv'] == '':
        app.logger.error('Il campo cvv non può essere vuoto.')
        return redirect(url_for('donazione',id=raccolta['id']))

    if 'anonimato' in donazione_form and donazione_form['anonimato'] == 'on':
        donazione_form['nome'] = None
        donazione_form['cognome'] = None


    if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():
        flash('La raccolta fondi è terminata, la donazione non è stata effettuata', 'danger')
        return redirect(url_for('home_page'))
    
    success=donatori_dao.add_donatore(donazione_form)

    if success:
        flash('Donazione ricevuta!','success')
        app.logger.info('Donazione ricevuta!')
        return redirect(url_for('singola_raccolta_fondi',id=raccolta['id']))
    else:
        flash('Errore durante la donazione, riprova!','danger')
        app.logger.error("Errore durante la donazione, riprova!")
        return redirect('home_page')


@app.route('/creazione_raccolta_fondi')
def creazione_raccolta_fondi():
    return render_template('creazione_raccolta_fondi.html',data_min=date.today(), data_max=date.today()+timedelta(days=14))

@app.route('/creazione_raccolta_fondi_form', methods=['POST'])
@login_required
def creazione_raccolta_fondi_form():
    creazione_raccolta_fondi_form=request.form.to_dict()
    
    if creazione_raccolta_fondi_form['titolo'] == '':
        app.logger.error('Il campo titolo non può essere vuoto.')
        return redirect(url_for('creazione_raccolta_fondi'))
    
    if creazione_raccolta_fondi_form['descrizione'] == '':
        app.logger.error('Il campo descrizione non può essere vuoto.')
        return redirect(url_for('creazione_raccolta_fondi'))
        
    if creazione_raccolta_fondi_form['obiettivo'] == '' or not re.match(r'^\d*\.?\d*$', creazione_raccolta_fondi_form['obiettivo']):
        app.logger.error('Il campo obiettivo è errato.')
        return redirect(url_for('creazione_raccolta_fondi'))

    if creazione_raccolta_fondi_form['donazione_min'] == '' or not re.match(r'^\d*\.?\d*$', creazione_raccolta_fondi_form['donazione_min']):
        app.logger.error('Il campo donazione minima è errato.')
        return redirect(url_for('creazione_raccolta_fondi'))
    
    if creazione_raccolta_fondi_form['donazione_max'] == '' or not re.match(r'^\d*\.?\d*$', creazione_raccolta_fondi_form['donazione_max']):
        app.logger.error('Il campo donazione massima è errato.')
        return redirect(url_for('creazione_raccolta_fondi'))
    
    if float(creazione_raccolta_fondi_form['donazione_max']) < float(creazione_raccolta_fondi_form['donazione_min']):
        flash('La donazione minima è più grande della donazione massima.','danger')
        app.logger.error('La donazione minima è più grande della donazione massima.')
        return redirect(url_for('creazione_raccolta_fondi'))

    if float(creazione_raccolta_fondi_form['donazione_min']) > float(creazione_raccolta_fondi_form['obiettivo']):
        flash("E' opportuno che la donazione minima non sia maggiore dell'obiettivo",'danger')
        app.logger.error("E' opportuno che la donazione minima non sia maggiore dell'obiettivo")
        return redirect(url_for('creazione_raccolta_fondi'))
    
    if not (creazione_raccolta_fondi_form['tipo'] == 'normale' or creazione_raccolta_fondi_form['tipo'] == 'lampo'):
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Errore durante la pubblicazione, riprova!.')
        return redirect(url_for('creazione_raccolta_fondi'))

    creazione_raccolta_fondi_form['id_utente']=int(current_user.id)
    creazione_raccolta_fondi_form['timestamp_creazione'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if creazione_raccolta_fondi_form['tipo'] == 'normale':
        if not datetime.strptime(creazione_raccolta_fondi_form['timestamp_chiusura'], '%Y-%m-%d') or datetime.strptime(creazione_raccolta_fondi_form['timestamp_chiusura'], '%Y-%m-%d').date() < date.today() or datetime.strptime(creazione_raccolta_fondi_form['timestamp_chiusura'], "%Y-%m-%d").date() > (datetime.now().date()+timedelta(days=14)):
            app.logger.error('Data errata.')    #la data o non è formattata correttamente come risultato da form, o non rispetta i vincoli dei 14 giorni o si tenta di creare una raccolta che termina in giorni passati
            return redirect(url_for('creazione_raccolta_fondi'))
        else:
            if not datetime.strptime(creazione_raccolta_fondi_form['ora_chiusura'], '%H:%M'):
                app.logger.error('Orario errato') #l'orario non è formattato correttamente
                return redirect(url_for('creazione_raccolta_fondi'))
            creazione_raccolta_fondi_form['timestamp_chiusura']= datetime.strptime(creazione_raccolta_fondi_form['timestamp_chiusura'] + ' ' + creazione_raccolta_fondi_form['ora_chiusura'], '%Y-%m-%d %H:%M').strftime("%Y-%m-%d %H:%M")
            if datetime.strptime(creazione_raccolta_fondi_form['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():
                flash('Creazione raccolta fondi negata. Non puoi far terminare la raccolta nel passato','danger')
                app.logger.error('Data errata.') #controllo che la raccolta non termini nel passato (prima ho fatto il controllo solo sul giorno, non su giorno + orario)
                return redirect(url_for('creazione_raccolta_fondi'))

    elif creazione_raccolta_fondi_form['tipo'] == 'lampo':
        creazione_raccolta_fondi_form['timestamp_chiusura']=(datetime.now()+timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")

    raccolta_image = request.files['immagine']
    if raccolta_image:

        # Open the user-provided image using the Image module
        img = Image.open(raccolta_image)

        # Get the width and height of the image
        width, height = img.size

        # Calculate the new height while maintaining the aspect ratio based on the desired width
        new_height = height/width * RACCOLTA_IMG_WIDTH

        # Define the size for thumbnail creation with the desired width and calculated height
        size = RACCOLTA_IMG_WIDTH, new_height
        img.thumbnail(size, Image.Resampling.LANCZOS)

        # Extracting file extension from the image filename
        ext = raccolta_image.filename.split('.')[-1]
        # Getting the current timestamp in seconds
        secondi = int(datetime.now().timestamp())       

        # Saving the image with a unique filename in the 'static' directory
        img.save('static/@' + current_user.email.lower() + '-' + str(secondi) + '.' + ext)

        # Updating the 'immagine_post' field in the post dictionary with the image filename
        creazione_raccolta_fondi_form['immagine'] = '@' + current_user.email.lower() + '-' + str(secondi) + '.' + ext

    success = raccolte_dao.add_raccolta(creazione_raccolta_fondi_form)
    if success:
        flash('Raccolta fondi creata correttamente','success')
        app.logger.info('Raccolta creata correttamente')
    else:
        flash('Errore durante la creazione della raccolta fondi, riprova!','danger')
        app.logger.error('Errore nella creazione della raccolta: riprova!')    

    return redirect(url_for('home_page'))

@app.route('/raccolte_fondi_passate')
def raccolte_fondi_passate():
    raccolte = raccolte_dao.get_raccolte() #ottengo tutte le raccolte sia aperte che chiuse, con nessun tipo di ordinamento nei campi
    raccolte_mod=[dict(row) for row in raccolte] #risultato modificabile
    raccolte_filtrate=[]
    
    #bisogna filtrare le raccolte per capire quali sono chiuse e ordinarle per obiettivo raggiunto
    
    for raccolta in raccolte_mod:
        if raccolta['cifra_totale_donata'] is None:
            raccolta['cifra_totale_donata'] = 0.0
        if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now() and raccolta['cifra_totale_donata'] >= raccolta['obiettivo']:
            raccolte_filtrate.append(raccolta) #inserisco prima nella lista le raccolte chiuse che hanno raggiunto l'obiettivo
    
    for raccolta in raccolte_mod:
        if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now() and raccolta['cifra_totale_donata'] < raccolta['obiettivo']:
            raccolte_filtrate.append(raccolta) #inserisco successivamente nella lista le raccolte chiuse che NON hanno raggiunto l'obiettivo

    for raccolta in raccolte_filtrate:
        raccolta['timestamp_chiusura']=datetime.strptime(raccolta['timestamp_chiusura'], "%Y-%m-%d %H:%M").strftime("%d-%m-%Y %H:%M")
        raccolta['descrizione'] = (' '.join(raccolta['descrizione'].split()[:N_words_in_paragraph_home_page]))+'...'
        if raccolta['cifra_totale_donata']>=raccolta['obiettivo']:
            raccolta['progress_bar'] = '100%'
        else:
            percentuale_avanzamento = (raccolta['cifra_totale_donata'] / raccolta['obiettivo']) * 100
            raccolta['progress_bar'] = f"{percentuale_avanzamento:.0f}%"

    return render_template('raccolte_passate.html', raccolte=raccolte_filtrate)


@app.route('/profilo')
@login_required
def profilo():
    utente=utenti_dao.get_user_by_id(int(current_user.id))
    raccolte_utente=raccolte_dao.get_raccolte_by_id_utente(int(current_user.id))
    portafoglio_virtuale=0.0

    raccolte_mod=[dict(row) for row in raccolte_utente]
    for raccolta in raccolte_mod:
        if raccolta['cifra_totale_donata'] is None:
            raccolta['cifra_totale_donata'] = 0.0
        if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now() and float(raccolta['cifra_totale_donata']) >= float(raccolta['obiettivo']):
            portafoglio_virtuale += float(raccolta['cifra_totale_donata'])  #se la raccolta è chiusa e ha raggiunto l'obiettivo

        if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():
            raccolta['modificabile'] = False
        else:
            raccolta['modificabile'] = True

        raccolta['timestamp_chiusura']=datetime.strptime(raccolta['timestamp_chiusura'], "%Y-%m-%d %H:%M").strftime("%d-%m-%Y %H:%M")
        raccolta['descrizione'] = (' '.join(raccolta['descrizione'].split()[:N_words_in_paragraph_profilo]))+'...'
        raccolta['cifra_totale_donata'] = float(raccolta['cifra_totale_donata'])
        raccolta['obiettivo'] = float(raccolta['obiettivo'])
    return render_template('profilo.html', utente=utente, raccolte=raccolte_mod, portafoglio_virtuale=portafoglio_virtuale)

@app.route('/cancella_raccolta_<int:id>')
@login_required
def cancella_raccolta(id):
    raccolta = raccolte_dao.get_raccolta(id)
    if not raccolta:
        flash('Errore durante la cancellazione della raccolta, riprova!','danger')
        app.logger.error("Errore durante la cancellazione della raccolta")
    if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():
        flash('Cancellazione della raccolta fondi negata, nel frattempo si è chiusa','danger')
        app.logger.error("La raccolta nel frattempo si è chiusa")
        return redirect(url_for('profilo'))
    
    if current_user.id != raccolta['id_utente']:
        flash('Errore durante la cancellazione della raccolta, riprova!','danger')
        app.logger.error('Errore nella cancellazione della raccolta, riprova!')
        return redirect(url_for('home_page'))
    success = raccolte_dao.delete_raccolta(id)
    if success:
        flash('Raccolta fondi cancellata correttamente','success')
        app.logger.info('Raccolta cancellata correttamente')
    else:
        flash('Errore durante la cancellazione della raccolta, riprova!','danger')
        app.logger.error('Errore nella cancellazione della raccolta: riprova!')   
    return redirect(url_for('profilo'))


@app.route('/modifica_raccolta_<int:id>')
@login_required
def modifica_raccolta(id):
    raccolta = raccolte_dao.get_raccolta(id)

    if not raccolta:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error("Raccolta non trovata")
        return redirect(url_for('home_page'))
    
    if current_user.id != raccolta['id_utente']:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Errore nella modifica della raccolta, riprova!')
        return redirect(url_for('home_page'))
    

    if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():
        flash('La raccolta fondi nel frattempo si è chiusa', 'danger')
        app.logger.error("La raccolta nel frattempo si è chiusa")
        return redirect(url_for('profilo'))

    data_min=date.today()
    data_max= (datetime.strptime(raccolta['timestamp_creazione'], "%Y-%m-%d %H:%M")+timedelta(days=14)).strftime("%Y-%m-%d")

    bottone_lampo_abilitato=False
    if datetime.strptime(raccolta['timestamp_creazione'], '%Y-%m-%d %H:%M')+timedelta(minutes=5) > datetime.now():   #se la raccolta è lampo in teoria questa condizione è verificata, perchè altrimenti la raccolta è chiusa e non saremmo arrivati a questo punto del codice
        bottone_lampo_abilitato=True

    data_chiusura=datetime.strptime(raccolta['timestamp_chiusura'], "%Y-%m-%d %H:%M").strftime("%Y-%m-%d")
    ora_chiusura=datetime.strptime(raccolta['timestamp_chiusura'], "%Y-%m-%d %H:%M").strftime("%H:%M")
    return render_template('modifica_raccolta.html',data_min=data_min, data_max=data_max, bottone_lampo_abilitato=bottone_lampo_abilitato,raccolta=raccolta, data_chiusura=data_chiusura, ora_chiusura=ora_chiusura)
    

    
@app.route('/modifica_raccolta_fondi_form', methods=['POST'])
@login_required
def modifica_raccolta_fondi_form():

    modifica_raccolta_fondi_form=request.form.to_dict()
    
    #controllo possibili errori dovuti a qualcosa di strano o sessioni scadute
    if modifica_raccolta_fondi_form['id'] == '' or not modifica_raccolta_fondi_form['id'].isdigit:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Errore, riprova!.')
        return redirect(url_for('home_page'))
    
    raccolta = raccolte_dao.get_raccolta(int(modifica_raccolta_fondi_form['id']))

    if not raccolta:
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error("Raccolta non trovata")
        return redirect(url_for('home_page'))

    if raccolta['id_utente'] != int(current_user.id):
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Errore, riprova!.')
        return redirect(url_for('home_page'))

    if datetime.strptime(raccolta['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():
        flash('La raccolta fondi nel frattempo si è chiusa', 'danger')
        app.logger.error("La raccolta nel frattempo si è chiusa")
        return redirect(url_for('profilo'))
    
    if not (modifica_raccolta_fondi_form['tipo'] == 'normale' or modifica_raccolta_fondi_form['tipo'] == 'lampo'):
        flash('Qualcosa è andato storto, riprova!', 'danger')
        app.logger.error('Errore, riprova!.')
        return redirect(url_for('home_page'))
    
    if raccolta['tipo'] =='normale' and modifica_raccolta_fondi_form['tipo'] == 'lampo':
        if datetime.strptime(raccolta['timestamp_creazione'], '%Y-%m-%d %H:%M')+timedelta(minutes=5) < datetime.now():
            flash('Non puoi cambiare il tipo della raccolta, perchè altrimenti terminerebbe. Sessione scaduta!', 'danger')
            app.logger.error('Non puoi cambiare il tipo della raccolta, perchè altrimenti terminerebbe. Sessione scaduta!')
            return redirect(url_for('modifica_raccolta',id=raccolta['id']))

    #controllo che i campi inseriti nel form siano corretti
    if modifica_raccolta_fondi_form['titolo'] == '':
        app.logger.error('Il campo titolo non può essere vuoto.')
        return redirect(url_for('modifica_raccolta',id=raccolta['id']))
    
    if modifica_raccolta_fondi_form['descrizione'] == '':
        app.logger.error('Il campo descrizione non può essere vuoto.')
        return redirect(url_for('modifica_raccolta',id=raccolta['id']))
        
    if modifica_raccolta_fondi_form['obiettivo'] == '' or not re.match(r'^\d*\.?\d*$', modifica_raccolta_fondi_form['obiettivo']):
        app.logger.error('Il campo obiettivo è errato.')
        return redirect(url_for('modifica_raccolta',id=raccolta['id']))

    if modifica_raccolta_fondi_form['donazione_min'] == '' or not re.match(r'^\d*\.?\d*$', modifica_raccolta_fondi_form['donazione_min']):
        app.logger.error('Il campo donazione minima è errato.')
        return redirect(url_for('modifica_raccolta',id=raccolta['id']))
    
    if modifica_raccolta_fondi_form['donazione_max'] == '' or not re.match(r'^\d*\.?\d*$', modifica_raccolta_fondi_form['donazione_max']):
        app.logger.error('Il campo donazione massima è errato.')
        return redirect(url_for('modifica_raccolta',id=raccolta['id']))
    
    if float(modifica_raccolta_fondi_form['donazione_max']) < float(modifica_raccolta_fondi_form['donazione_min']):
        flash('La donazione minima è più grande della donazione massima.','danger')
        app.logger.error('La donazione minima è più grande della donazione massima.')
        return redirect(url_for('modifica_raccolta',id=raccolta['id']))

    if float(modifica_raccolta_fondi_form['donazione_min']) > float(modifica_raccolta_fondi_form['obiettivo']):
        flash("E' opportuno che la donazione minima non sia maggiore dell'obiettivo",'danger')
        app.logger.error("E' opportuno che la donazione minima non sia maggiore dell'obiettivo")
        return redirect(url_for('creazione_raccolta_fondi'))

    modifica_raccolta_fondi_form['id_utente']=int(current_user.id)
    modifica_raccolta_fondi_form['timestamp_creazione'] = raccolta['timestamp_creazione']
    
    if modifica_raccolta_fondi_form['tipo'] == 'normale':
        if not datetime.strptime(modifica_raccolta_fondi_form['timestamp_chiusura'], '%Y-%m-%d') or datetime.strptime(modifica_raccolta_fondi_form['timestamp_chiusura'], '%Y-%m-%d').date() < datetime.strptime(modifica_raccolta_fondi_form['timestamp_creazione'], '%Y-%m-%d %H:%M').date() or datetime.strptime(modifica_raccolta_fondi_form['timestamp_chiusura'], "%Y-%m-%d").date() > (datetime.strptime(modifica_raccolta_fondi_form['timestamp_creazione'], "%Y-%m-%d %H:%M").date()+timedelta(days=14)):
            app.logger.error('Data errata.')
            return redirect(url_for('modifica_raccolta',id=raccolta['id']))
        else:
            if not datetime.strptime(modifica_raccolta_fondi_form['ora_chiusura'], '%H:%M'):
                app.logger.error('Orario errato')
                return redirect(url_for('modifica_raccolta',id=raccolta['id']))
            
            modifica_raccolta_fondi_form['timestamp_chiusura']= datetime.strptime(modifica_raccolta_fondi_form['timestamp_chiusura'] + ' ' + modifica_raccolta_fondi_form['ora_chiusura'], '%Y-%m-%d %H:%M').strftime("%Y-%m-%d %H:%M")
            if datetime.strptime(modifica_raccolta_fondi_form['timestamp_chiusura'], '%Y-%m-%d %H:%M') < datetime.now():
                app.logger.error('Data errata.')
                return redirect(url_for('creazione_raccolta_fondi'))

    elif modifica_raccolta_fondi_form['tipo'] == 'lampo':
        modifica_raccolta_fondi_form['timestamp_chiusura']=(datetime.strptime(raccolta['timestamp_creazione'], '%Y-%m-%d %H:%M')+timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")


    if 'immagine_vuota' in modifica_raccolta_fondi_form and modifica_raccolta_fondi_form['immagine_vuota'] == 'on':
        modifica_raccolta_fondi_form['immagine'] = None
    else:
        raccolta_image = request.files['immagine']
        if raccolta_image:

            # Open the user-provided image using the Image module
            img = Image.open(raccolta_image)

            # Get the width and height of the image
            width, height = img.size

            # Calculate the new height while maintaining the aspect ratio based on the desired width
            new_height = height/width * RACCOLTA_IMG_WIDTH

            # Define the size for thumbnail creation with the desired width and calculated height
            size = RACCOLTA_IMG_WIDTH, new_height
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Extracting file extension from the image filename
            ext = raccolta_image.filename.split('.')[-1]
            # Getting the current timestamp in seconds
            secondi = int(datetime.now().timestamp())       

            # Saving the image with a unique filename in the 'static' directory
            img.save('static/@' + current_user.email.lower() + '-' + str(secondi) + '.' + ext)

            # Updating the 'immagine_post' field in the post dictionary with the image filename
            modifica_raccolta_fondi_form['immagine'] = '@' + current_user.email.lower() + '-' + str(secondi) + '.' + ext
        else:
            modifica_raccolta_fondi_form['immagine'] = raccolta['immagine']

    success = raccolte_dao.update_raccolta(modifica_raccolta_fondi_form)
    if success:
        flash('Raccolta modificata correttamente','success')
        app.logger.info('Raccolta modificata correttamente')
    else:
        flash('Errore nella modifica della raccolta: riprova!','danger')
        app.logger.error('Errore nella modifica della raccolta: riprova!')    

    return redirect(url_for('home_page'))