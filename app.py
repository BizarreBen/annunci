import datetime
import os
from flask import Flask, render_template, request, redirect, send_from_directory, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, logout_user, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import utenti_dao
import annunci_dao
import prenotazioni_dao

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, email, password, tipo):
        self.email = email
        self.password = password
        self.tipo = tipo
    
    def get_id(self):
        return self.email

@login_manager.user_loader
def load_user(email):
    db_user = utenti_dao.get_user(email)

    return User(email=db_user['email'],
                password=db_user['password'],
                tipo=int(db_user['Tipo']))

@app.route('/', methods = ['GET'])
def index():
    order = request.args.get('order', 'prezzo').lower()
    order_list = ['prezzo', 'locali']
    return render_template('index.html', annunci=annunci_dao.get_annunci(request.args.get('limit', 0), order_list.index(order)), order=order)

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form.to_dict()
        print(user)

        user['password'] = generate_password_hash(user['password'])

        if utenti_dao.register_user(user):
            return redirect(url_for('login'), code=307)

    return render_template('register.html')


@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_form = request.form.to_dict()
        user_db = utenti_dao.get_user(user_form['email'])

        if user_db and check_password_hash(user_db['password'], user_form['password']):
            user = User(email=user_db['email'], password=user_db['password'], tipo=user_db['tipo'])
            login_user(user, True)
            return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/annunci/<id>', methods = ['GET', 'POST'])
def ann(id):
    if request.method == 'POST' and current_user.is_authenticated:
        form = request.form.to_dict()
        form['id_annuncio'] = id
        form['email_utente'] = current_user.email
        prenotazioni_dao.insert_prenotazione(prenotazioni_dao.from_form(form))

    if current_user.is_authenticated:
        lista_giorni = [(datetime.date.today() + datetime.timedelta(days=x)) for x in range(1, 8)]
        prenotazioni = prenotazioni_dao.get_prenotazioni_by_annuncio(id)
        lista_giorni = [{'match': giorno.isoformat(), 'giorno': giorno.strftime('%d/%m'), 'fasce' : {fascia: True for fascia in prenotazioni_dao.Prenotazione.fasce_orarie}} for giorno in lista_giorni]
        for prenotazione in prenotazioni:
            for giorno in lista_giorni:
                if giorno['match'] == prenotazione.data:
                    giorno['fasce'][prenotazione.fascia_oraria] = False
        
        return render_template('annuncio.html', annuncio=annunci_dao.get_annuncio_by_id(id), giorni=lista_giorni, prenotazione=prenotazioni_dao.get_prenotazione_if_not_rejected(current_user.email, id))
    return render_template('annuncio.html', annuncio=annunci_dao.get_annuncio_by_id(id))

@app.route('/annunci/add', methods = ['GET', 'POST'])
@login_required
def add_ann():
    if current_user.tipo == 0:
        app.logger.error('forbidden')
        return redirect('index', code = 401)
    
    if request.method == 'POST':
        form = request.form.to_dict()
        form['id_locatore'] = current_user.email
        immagini = [immagine for immagine in request.files.getlist('immagini') if not immagine.filename == '']
        
        if not 1 <= len(immagini) <= 5 or immagini[0].filename == '':
            app.logger.error('file number outside limits')
            return redirect(request.url)
        
        if annunci_dao.insert_annuncio(annunci_dao.from_form(form), immagini, app.config['UPLOAD_FOLDER']):
            return redirect(url_for('index'))

    return render_template('add_ann.html')

@app.route('/annunci/<id>/edit', methods = ['GET', 'POST'])
@login_required
def edit_ann(id):
    if current_user.tipo == 0:
        app.logger.error('forbidden')
        return redirect('index', code = 401)
    
    if request.method == 'POST':
        annuncio_pre = annunci_dao.get_annuncio_by_id(id)
        form = request.form.to_dict()
        immagini_selection = request.form.getlist('immagini_selection')
        form['id'] = id
        form['indirizzo'] = annuncio_pre.indirizzo
        form['id_locatore'] = current_user.email
        immagini_to_del = [immagine for immagine in annuncio_pre.immagini if immagine not in immagini_selection]

        annuncio = annunci_dao.from_form(form)
        annuncio.immagini = [immagine for immagine in annuncio_pre.immagini if immagine in immagini_selection]

        immagini = [immagine for immagine in request.files.getlist('immagini') if not immagine.filename == '']
        
        if not len(immagini) - len(immagini_to_del) <= 5:
            app.logger.error('file number outside limits')
            return redirect(request.url)
        
        if annunci_dao.edit_annuncio(annuncio, immagini, app.config['UPLOAD_FOLDER'], immagini_to_del):
            return redirect(url_for('index'))
    
    return render_template('edit_ann.html', annuncio=annunci_dao.get_annuncio_by_id(id))

@app.route('/profilo')
@login_required
def profilo():
    if current_user.tipo == 1:
        return render_template('profilo.html', prenotazioni=prenotazioni_dao.get_prenotazioni_by_locatore(current_user.email), annunci=annunci_dao.get_annunci_by_locatore(current_user.email))
    return render_template('profilo.html', prenotazioni=prenotazioni_dao.get_prenotazioni(current_user.email))

@app.route('/prenotazione/<id>/delete')
@login_required
def delete_prenotazione(id):
    if not prenotazioni_dao.delete_prenotazione(id, current_user.email):
        flash('no del')
    else:
        flash('deleted')

    return redirect(request.referrer)

@app.route('/prenotazione/insert', methods = ['POST'])
@login_required
def insert_prenotazione():
    prenotazione = prenotazioni_dao.from_form(request.form.to_dict())
    if not prenotazioni_dao.insert_prenotazione(prenotazione=prenotazione):
        flash('no insert')
    else:
        flash('inserted')

    return redirect(request.url)

@app.route('/prenotazione/<id>/confirm')
@login_required
def confirm_prenotazione(id):
    prenotazioni_dao.update_status_prenotazione(id, current_user.email, 1)

    return redirect(request.referrer)

@app.route('/prenotazione/<id>/reject')
@login_required
def reject_prenotazione(id):
    prenotazioni_dao.update_status_prenotazione(id, current_user.email, 2)

    return redirect(request.referrer)