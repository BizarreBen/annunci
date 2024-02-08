import sqlite3
import annunci_dao

db_location = "db.db"


class Prenotazione:
    fasce_orarie = ["9-12", "12-14", "14-17", "17-20"]

    def __init__(
        self,
        id_prenotazione,
        id_annuncio,
        email_utente,
        fascia_oraria,
        data,
        virtuale,
        status,
        motivo_rifiuto,
        annuncio: annunci_dao.Annuncio = None,
    ):
        self.id_prenotazione = int(id_prenotazione)
        self.id_annuncio = int(id_annuncio)
        self.email_utente = email_utente
        self.fascia_oraria = self.fasce_orarie[int(fascia_oraria)]
        self.data = data
        self.virtuale = int(virtuale) == 1
        self.status = int(status)
        self.annuncio = annuncio
        self.motivo_rifiuto = motivo_rifiuto

    def to_tuple(self):
        return (
            self.id_annuncio,
            self.email_utente,
            self.fasce_orarie.index(self.fascia_oraria),
            self.data,
            self.virtuale,
            self.status,
            self.motivo_rifiuto,
        )

    def __repr__(self) -> str:
        return f"<Prenotazione: {self.id_annuncio}, {self.email_utente}, {self.fascia_oraria}, {self.data}, {self.data}>"


def from_form(formdict: dict):
    return Prenotazione(
        id_prenotazione=-1,
        id_annuncio=formdict["id_annuncio"],
        email_utente=formdict["email_utente"],
        fascia_oraria=formdict["fascia_oraria"],
        data=formdict["data"],
        virtuale=formdict.get("virtuale", "off") == "on",
        status=int(formdict.get("status", "0")),
        motivo_rifiuto=formdict.get("motivo_rifiuto", ""),
				annuncio=annunci_dao.get_annuncio_by_id(formdict["id_annuncio"])
    )


def get_prenotazioni(email, limit=0):
    query = f"SELECT * FROM prenotazioni INNER JOIN annunci ON annunci.Id = prenotazioni.id_annuncio WHERE email_utente == ? AND JULIANDAY(data) >= JULIANDAY(DATE('now')) {' LIMIT ?' if limit > 0 else ''}"

    with sqlite3.connect(db_location) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            cursor.execute(query, (email, limit) if limit > 0 else (email,))
            return [
                Prenotazione(
                    prenotazione["id"],
                    prenotazione["id_annuncio"],
                    prenotazione["email_utente"],
                    prenotazione["fascia_oraria"],
                    prenotazione["data"],
                    prenotazione["virtuale"],
                    prenotazione["status"],
                    prenotazione["motivo_rifiuto"],
                    annunci_dao.Annuncio(
                        prenotazione["id_annuncio"],
                        prenotazione["Titolo"],
                        prenotazione["Indirizzo"],
                        prenotazione["Tipo"],
                        prenotazione["Locali"],
                        prenotazione["Descrizione"],
                        prenotazione["Prezzo"],
                        prenotazione["Arredata"],
                        prenotazione["Id_Locatore"],
                        prenotazione["Visibile"],
                        prenotazione["Immagini"],
                    ),
                )
                for prenotazione in cursor.fetchall()
            ]
        except Exception as e:
            print("Error", e)
            return []
        finally:
            cursor.close()


def get_prenotazioni_by_locatore(email, limit=0):
    query = f"SELECT * FROM prenotazioni INNER JOIN annunci ON annunci.Id = prenotazioni.id_annuncio WHERE annunci.id_locatore == ? ORDER BY prenotazioni.status{' LIMIT ?' if limit > 0 else ''}"

    with sqlite3.connect(db_location) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            cursor.execute(query, (email, limit) if limit > 0 else (email,))
            return [
                Prenotazione(
                    prenotazione["id"],
                    prenotazione["id_annuncio"],
                    prenotazione["email_utente"],
                    prenotazione["fascia_oraria"],
                    prenotazione["data"],
                    prenotazione["virtuale"],
                    prenotazione["status"],
                    prenotazione["motivo_rifiuto"],
                    annunci_dao.Annuncio(
                        prenotazione["id_annuncio"],
                        prenotazione["Titolo"],
                        prenotazione["Indirizzo"],
                        prenotazione["Tipo"],
                        prenotazione["Locali"],
                        prenotazione["Descrizione"],
                        prenotazione["Prezzo"],
                        prenotazione["Arredata"],
                        prenotazione["Id_Locatore"],
                        prenotazione["Visibile"],
                        prenotazione["Immagini"],
                    ),
                )
                for prenotazione in cursor.fetchall()
            ]
        except Exception as e:
            print("Error", e)
            return []
        finally:
            cursor.close()


def get_prenotazione(email, annuncio_id):
    query = f"SELECT * FROM prenotazioni INNER JOIN annunci ON annunci.Id = prenotazioni.id_annuncio WHERE id_annuncio = ? AND email_utente == ? AND JULIANDAY(data) >= JULIANDAY(DATE('now'))"

    with sqlite3.connect(db_location) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            cursor.execute(query, (annuncio_id, email))
            prenotazione = cursor.fetchone()
            if cursor.rowcount == 0:
                return None
            return Prenotazione(
                prenotazione["id"],
                prenotazione["id_annuncio"],
                prenotazione["email_utente"],
                prenotazione["fascia_oraria"],
                prenotazione["data"],
                prenotazione["virtuale"],
                prenotazione["status"],
                annunci_dao.Annuncio(
                    prenotazione["id_annuncio"],
                    prenotazione["Titolo"],
                    prenotazione["Indirizzo"],
                    prenotazione["Tipo"],
                    prenotazione["Locali"],
                    prenotazione["Descrizione"],
                    prenotazione["Prezzo"],
                    prenotazione["Arredata"],
                    prenotazione["Id_Locatore"],
                    prenotazione["Visibile"],
                    prenotazione["Immagini"],
                ),
            )
        except Exception as e:
            print("Error", e)
            return None
        finally:
            cursor.close()


def get_prenotazione_if_not_rejected(email, annuncio_id):
    query = f"SELECT * FROM prenotazioni INNER JOIN annunci ON annunci.Id = prenotazioni.id_annuncio WHERE id_annuncio = ? AND email_utente == ? AND JULIANDAY(data) >= JULIANDAY(DATE('now')) AND prenotazioni.status != 2"

    with sqlite3.connect(db_location) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            cursor.execute(query, (annuncio_id, email))
            prenotazione = cursor.fetchone()
            if prenotazione == None:
                return None
            return Prenotazione(
                prenotazione["id"],
                prenotazione["id_annuncio"],
                prenotazione["email_utente"],
                prenotazione["fascia_oraria"],
                prenotazione["data"],
                prenotazione["virtuale"],
                prenotazione["status"],
                prenotazione["motivo_rifiuto"],
                annunci_dao.Annuncio(
                    prenotazione["id_annuncio"],
                    prenotazione["Titolo"],
                    prenotazione["Indirizzo"],
                    prenotazione["Tipo"],
                    prenotazione["Locali"],
                    prenotazione["Descrizione"],
                    prenotazione["Prezzo"],
                    prenotazione["Arredata"],
                    prenotazione["Id_Locatore"],
                    prenotazione["Visibile"],
                    prenotazione["Immagini"],
                ),
            )
        except Exception as e:
            print("Error 6", e)
            return None
        finally:
            cursor.close()


def get_prenotazioni_by_annuncio(id):
    query = f"SELECT * FROM prenotazioni WHERE id_annuncio == ? AND JULIANDAY(data) >= JULIANDAY(DATE('now')) AND status == 1"

    with sqlite3.connect(db_location) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            cursor.execute(query, (id,))
            return [
                Prenotazione(
                    prenotazione["id"],
                    prenotazione["id_annuncio"],
                    prenotazione["email_utente"],
                    prenotazione["fascia_oraria"],
                    prenotazione["data"],
                    prenotazione["virtuale"],
                    prenotazione["status"],
                    prenotazione["motivo_rifiuto"],
                )
                for prenotazione in cursor.fetchall()
            ]
        except Exception as e:
            print("Error 4", e)
            return []
        finally:
            cursor.close()


def insert_prenotazione(prenotazione: Prenotazione):
    query = """
            INSERT INTO prenotazioni(
                id_annuncio,
                email_utente,
                fascia_oraria,
                data,
                virtuale,
                status,
                motivo_rifiuto
            ) VALUES (?,?,?,?,?,?,?)
            """

    with sqlite3.connect(db_location) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(query, prenotazione.to_tuple())
            connection.commit()
            return True
        except Exception as e:
            print("Error 3", e)
            connection.rollback()
            return False
        finally:
            cursor.close()


def delete_prenotazione(id, email):
    query = """
            DELETE FROM prenotazioni WHERE id == ? AND email_utente == ?
            """

    with sqlite3.connect(db_location) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(query, (id, email))
            if cursor.rowcount == 0:
                raise Exception("No delete")
            connection.commit()
            return True
        except Exception as e:
            print("Error", e)
            connection.rollback()
            return False
        finally:
            cursor.close()


def update_status_prenotazione(id, email, status, motivo_rifiuto):
    query = """
            UPDATE prenotazioni SET status = ?, motivo_rifiuto = ? WHERE id = ? AND EXISTS (SELECT Id_locatore FROM annunci WHERE Id == id_annuncio AND Id_locatore == ?)
            """

    with sqlite3.connect(db_location) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(query, (status, motivo_rifiuto, id, email))
            if cursor.rowcount == 0:
                raise Exception("No update")
            connection.commit()
            return True
        except Exception as e:
            print("Error", e)
            connection.rollback()
            return False
        finally:
            cursor.close()
