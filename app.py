import datetime
import os
import re
from flask import Flask, abort, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_required,
    logout_user,
    login_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash

import utenti_dao
import annunci_dao
import prenotazioni_dao

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
app.config["UPLOAD_FOLDER"] = os.path.join(app.static_folder, "uploads")

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
    if not db_user:
      return None

    return User(
        email=db_user["email"], password=db_user["password"], tipo=int(db_user["Tipo"])
    )


@app.route("/", methods=["GET"])
def index():
    order = request.args.get("order", "prezzo").lower()
    order_list = ["prezzo", "locali"]
    return render_template(
        "index.html",
        annunci=annunci_dao.get_annunci(
            request.args.get("limit", 0), order_list.index(order)
        ),
        order=order,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.to_dict()

        if "email" not in user or not re.fullmatch(
            r"[^@]+@[^@]+\.[^@]+", user.get("email")
        ):
            flash("Email non valida", "Errore")
            return render_template("register.html")

        if "password" not in user or len(user.get("password")) == 0:
            flash("Password mancante", "Errore")
            return render_template("register.html")

        user["Tipo"] = 1 if user.get("Tipo") == "on" else 0

        user["password"] = generate_password_hash(user["password"])

        if utenti_dao.register_user(user):
            return redirect(url_for("login"), code=307)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_form = request.form.to_dict()
        user_db = utenti_dao.get_user(user_form["email"])

        if user_db is not None and check_password_hash(user_db["password"], user_form["password"]):
            user = User(
                email=user_db["email"],
                password=user_db["password"],
                tipo=user_db["tipo"],
            )
            login_user(user, True)
            return redirect(url_for("index"))
        flash("Email o password errata", "Errore")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/annunci/<id>", methods=["GET", "POST"])
def ann(id):
    if request.method == "POST" and current_user.is_authenticated:
        form = request.form.to_dict()

        if "data" not in form:
            flash("Campo data necessario rimosso", "Errore")

        if "fascia_oraria" not in form:
            flash("Fascia oraria non selezionata", "Errore")

        form["id_annuncio"] = id
        form["email_utente"] = current_user.email
        if "data" in form and "fascia_oraria" in form:
            prenotazioni_dao.insert_prenotazione(prenotazioni_dao.from_form(form))

    if current_user.is_authenticated:
        lista_giorni = [
            (datetime.date.today() + datetime.timedelta(days=x)) for x in range(1, 8)
        ]
        prenotazioni = prenotazioni_dao.get_prenotazioni_by_annuncio(id)
        lista_giorni = [
            {
                "match": giorno.isoformat(),
                "giorno": giorno.strftime("%d/%m"),
                "fasce": {
                    fascia: True
                    for fascia in prenotazioni_dao.Prenotazione.fasce_orarie
                },
            }
            for giorno in lista_giorni
        ]
        for prenotazione in prenotazioni:
            for giorno in lista_giorni:
                if giorno["match"] == prenotazione.data:
                    giorno["fasce"][prenotazione.fascia_oraria] = False

        return render_template(
            "annuncio.html",
            annuncio=annunci_dao.get_annuncio_by_id(id),
            giorni=lista_giorni,
            prenotazione=prenotazioni_dao.get_prenotazione_if_not_rejected(
                current_user.email, id
            ),
        )
    return render_template("annuncio.html", annuncio=annunci_dao.get_annuncio_by_id(id))


@app.route("/annunci/add", methods=["GET", "POST"])
@login_required
def add_ann():
    if current_user.tipo == 0:
        abort(403)

    if request.method == "POST":
        form = request.form.to_dict()

        if "titolo" not in form or len(form["titolo"]) == 0:
            flash("Titolo mancante", "Errore")
            return redirect(request.url)

        if "indirizzo" not in form or len(form["indirizzo"]) == 0:
            flash("Indirizzo mancante", "Errore")
            return redirect(request.url)

        if "tipo" not in form or not (0 <= int(form["tipo"]) <= 3):
            if "tipo" not in form:
                flash("Tipo mancante", "Errore")
            else:
                flash("Valore campo `Tipo` fuori range", "Errore")
            return redirect(request.url)

        if "locali" not in form or not (1 <= int(form["tipo"]) <= 5):
            if "locali" not in form:
                flash("Numero di locali mancante", "Errore")
            else:
                flash("Valore campo `Locali` fuori range", "Errore")
            return redirect(request.url)

        if "descrizione" not in form or len(form["descrizione"]) == 0:
            flash("Descrizione mancante", "Errore")
            return redirect(request.url)

        if "prezzo" not in form or len(form["prezzo"]) == 0:
            flash("Prezzo mancante", "Errore")
            return redirect(request.url)

        form["id_locatore"] = current_user.email
        immagini = [
            immagine
            for immagine in request.files.getlist("immagini")
            if not immagine.filename == ""
        ]

        if not 1 <= len(immagini) <= 5 or immagini[0].filename == "":
            if len(immagini) > 5:
                flash("Inserire al massimo 5 immagini", "Errore")
            else:
                flash("Inserire almeno una immagine", "Errore")
            return redirect(request.url)

        if annunci_dao.insert_annuncio(
            annunci_dao.from_form(form), immagini, app.config["UPLOAD_FOLDER"]
        ):
            return redirect(url_for("index"))
        else:
            flash("Qualcosa è andato storto", "Errore")

    return render_template("add_ann.html")


@app.route("/annunci/<id>/edit", methods=["GET", "POST"])
@login_required
def edit_ann(id):
    if current_user.tipo == 0:
        abort(403)

    if request.method == "POST":
        annuncio_pre = annunci_dao.get_annuncio_by_id(id)
        form = request.form.to_dict()
        immagini_selection = request.form.getlist("immagini_selection")
        form["id"] = id
        form["indirizzo"] = annuncio_pre.indirizzo
        form["id_locatore"] = current_user.email
        immagini_to_del = [
            immagine
            for immagine in annuncio_pre.immagini
            if immagine not in immagini_selection
        ]

        annuncio = annunci_dao.from_form(form)
        annuncio.immagini = [
            immagine
            for immagine in annuncio_pre.immagini
            if immagine in immagini_selection
        ]

        immagini = [
            immagine
            for immagine in request.files.getlist("immagini")
            if not immagine.filename == ""
        ]

        if "titolo" not in form or len(form["titolo"]) == 0:
            flash("Titolo mancante", "Errore")
            return redirect(request.url)

        if "tipo" not in form or not (0 <= int(form["tipo"]) <= 3):
            if "tipo" not in form:
                flash("Tipo mancante", "Errore")
            else:
                flash("Valore campo `Tipo` fuori range", "Errore")
            return redirect(request.url)

        if "locali" not in form or not (1 <= int(form["tipo"]) <= 5):
            if "locali" not in form:
                flash("Numero di locali mancante", "Errore")
            else:
                flash("Valore campo `Locali` fuori range", "Errore")
            return redirect(request.url)

        if "descrizione" not in form or len(form["descrizione"]) == 0:
            flash("Descrizione mancante", "Errore")
            return redirect(request.url)

        if "prezzo" not in form or len(form["prezzo"]) == 0:
            flash("Prezzo mancante", "Errore")
            return redirect(request.url)

        if not (1 <= (len(immagini) + len(annuncio.immagini)) <= 5):
            if (len(immagini) + len(annuncio.immagini)) == 0:
                flash("È richiesta la presenza di almeno un'immagine", "Errore")
            else:
                flash("Troppe immagini inserite", "Errore")
            return redirect(request.url)

        if annunci_dao.edit_annuncio(
            annuncio, immagini, app.config["UPLOAD_FOLDER"], immagini_to_del
        ):
            return redirect(url_for("index"))
        else:
            flash("Qualcosa è andato storto", "Errore")

    return render_template("edit_ann.html", annuncio=annunci_dao.get_annuncio_by_id(id))


@app.route("/profilo")
@login_required
def profilo():
    if current_user.tipo == 1:
        return render_template(
            "profilo.html",
            prenotazioni=prenotazioni_dao.get_prenotazioni_by_locatore(
                current_user.email
            ),
            annunci=annunci_dao.get_annunci_by_locatore(current_user.email),
        )
    return render_template(
        "profilo.html",
        prenotazioni=prenotazioni_dao.get_prenotazioni(current_user.email),
    )


@app.route("/prenotazione/<id>/delete")
@login_required
def delete_prenotazione(id):
    if not prenotazioni_dao.delete_prenotazione(id, current_user.email):
        flash("Qualcosa è andato storto nell'eliminazione della prenotazione", "Errore")
    else:
        flash("Prenotazione eliminata con successo", "Successo")

    return redirect(request.referrer)


@app.route("/prenotazione/insert", methods=["POST"])
@login_required
def insert_prenotazione():
    prenotazione = prenotazioni_dao.from_form(request.form.to_dict())
    if not prenotazioni_dao.insert_prenotazione(prenotazione=prenotazione):
        flash("Qualcosa è andato storto nell'inserimento della prenotazione", "Errore")
    else:
        flash("Prenotazione inserita con successo", "Successo")

    return redirect(request.url)


@app.route("/prenotazione/<id>/confirm")
@login_required
def confirm_prenotazione(id):
    if not prenotazioni_dao.update_status_prenotazione(id, current_user.email, 1, None):
        flash("Qualcosa è andato storto nella conferma della prenotazione", "Errore")
    else:
        flash("Prenotazione confermata con successo", "Successo")

    return redirect(request.referrer)


@app.route("/prenotazione/<id>/reject", methods=["POST"])
@login_required
def reject_prenotazione(id):
    if not prenotazioni_dao.update_status_prenotazione(
        id, current_user.email, 2, request.form.get("motivo_rifiuto", "")
    ):
        flash("Qualcosa è andato storto nel rifiuto della prenotazione", "Errore")
    else:
        flash("Prenotazione rifiutata con successo", "Successo")

    return redirect(request.referrer)
