import sqlite3
import traceback
from PIL import Image
import os
from werkzeug.utils import secure_filename

db_location = 'db.db'

class Annuncio():
    tipi = ['Casa indipendente', 'Appartamento', 'Loft', 'Villa']
    def __init__(self, id, titolo, indirizzo, tipo, locali, descrizione, prezzo, arredata, id_locatore, visibile, immagini):
        self.id = int(id)
        self.titolo = titolo
        self.indirizzo = indirizzo
        self.tipo = self.tipi[int(tipo)]
        self.locali = locali if int(locali) < 5 else '5+'
        self.descrizione = descrizione
        self.prezzo = prezzo
        self.arredata = not int(arredata) == 0
        self.id_locatore = id_locatore
        self.visibile = not int(visibile) == 0
        self.immagini = immagini.split('|')
    
    def to_tuple(self):
        return (
            self.titolo,
            self.indirizzo,
            self.tipi.index(self.tipo),
            5 if self.locali == '5+' else int(self.locali),
            self.descrizione,
            self.prezzo,
            1 if self.arredata else 0,
            self.id_locatore,
            1 if self.visibile else 0,
            '|'.join(self.immagini)
        )
    
    def __repr__(self) -> str:
        return f'''
                <Annuncio 
                {self.id},
                {self.titolo},
                {self.indirizzo},
                {self.tipo},
                {self.locali},
                {self.descrizione},
                {self.prezzo},
                {self.arredata},
                {self.id_locatore},
                {self.visibile},
                {self.immagini}
                >
                '''

def from_form(formdict: dict):
    return Annuncio(
        id=formdict.get('id', -1),
        titolo=formdict.get('titolo'),
        indirizzo=formdict.get('indirizzo'),
        tipo=formdict.get('tipo'),
        locali=formdict.get('locali'),
        descrizione=formdict.get('descrizione'),
        prezzo=formdict.get('prezzo'),
        arredata='1' if formdict.get('arredata') else '0',
        id_locatore=formdict.get('id_locatore'),
        visibile='1' if formdict.get('visibile') else '0',
        immagini='',
    )

def get_annuncio_by_id(id):
    query = f"SELECT * FROM annunci WHERE id == ?"

    with sqlite3.connect(db_location) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            cursor.execute(query, id)
            ann = cursor.fetchone()
            return Annuncio(ann['Id'], ann['Titolo'], ann['Indirizzo'], ann['Tipo'], ann['Locali'], ann['Descrizione'], ann['Prezzo'], ann['Arredata'], ann['Id_Locatore'], ann['Visibile'], ann['Immagini'])
        except Exception as e:
            print('Error 2', e)
            return None
        finally:
            cursor.close()
    

def get_annunci(limit = 0, order = 0):
    orders = ['prezzo DESC', 'locali ASC']
    query = f"SELECT * FROM annunci WHERE visibile == 1 ORDER BY { orders[order] }{' LIMIT ?' if limit > 0 else ''}"

    with sqlite3.connect(db_location) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            cursor.execute(query, (limit,) if limit > 0 else ())
            data = [Annuncio(ann['Id'], ann['Titolo'], ann['Indirizzo'], ann['Tipo'], ann['Locali'], ann['Descrizione'], ann['Prezzo'], ann['Arredata'], ann['Id_Locatore'], ann['Visibile'], ann['Immagini']) for ann in cursor.fetchall()]
            return data
        except Exception as e:
            print('Error', e)
            return []
        finally:
            cursor.close()

def get_annunci_by_locatore(email):
    query = f"SELECT * FROM annunci WHERE Id_locatore == ?"

    with sqlite3.connect(db_location) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            cursor.execute(query, (email,))
            data = [Annuncio(ann['Id'], ann['Titolo'], ann['Indirizzo'], ann['Tipo'], ann['Locali'], ann['Descrizione'], ann['Prezzo'], ann['Arredata'], ann['Id_Locatore'], ann['Visibile'], ann['Immagini']) for ann in cursor.fetchall()]
            return data
        except Exception as e:
            print('Error', e)
            return []
        finally:
            cursor.close()

def insert_annuncio(annuncio: Annuncio, immagini, filepath):
    query = '''
            INSERT INTO annunci(
            Titolo,
            Indirizzo,
            Tipo,
            Locali,
            Descrizione,
            Prezzo,
            Arredata,
            Id_Locatore,
            Visibile,
            Immagini
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            '''
    
    query_update =  '''
                    UPDATE annunci SET Immagini = ? WHERE Id = ?
                    '''
    
    with sqlite3.connect(db_location) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(query, annuncio.to_tuple())
            annuncio.id = cursor.lastrowid # id matching

            for immagine in immagini:
                immagine.save(os.path.join(filepath, f'{annuncio.id}{secure_filename(immagine.filename)}'))
            annuncio.immagini = [f'{annuncio.id}{secure_filename(immagine.filename)}' for immagine in immagini]
            cursor.execute(query_update, ('|'.join(annuncio.immagini), annuncio.id))
            connection.commit()
            return True
        except Exception as e:
            print('Error 1', e)
            print(traceback.format_exc())
            connection.rollback()
            return False
        finally:
            cursor.close()

def edit_annuncio(annuncio: Annuncio, immagini, filepath, immagini_to_del):
    query = f'''
            UPDATE annunci SET
            Titolo = ?,
            Indirizzo = ?,
            Tipo = ?,
            Locali = ?,
            Descrizione = ?,
            Prezzo = ?,
            Arredata = ?,
            Id_Locatore = ?,
            Visibile = ?,
            Immagini = ?
            WHERE Id == ?
            '''
    
    with sqlite3.connect(db_location) as connection:
        cursor = connection.cursor()
        try:
            if len(immagini) > 0 and not immagini[0] == '':
                for immagine in immagini:
                    immagine.save(os.path.join(filepath, f'{annuncio.id}{secure_filename(immagine.filename)}'))
                annuncio.immagini.extend([f'{annuncio.id}{secure_filename(immagine.filename)}' for immagine in immagini])
            cursor.execute(query, annuncio.to_tuple() + (annuncio.id,))
            connection.commit()

            for immagine in immagini_to_del:
                if secure_filename(immagine) not in annuncio.immagini:
                    path = os.path.join(filepath, secure_filename(immagine))
                    if os.path.isfile(path):
                        os.remove(path)

            return True
        except Exception as e:
            print('Error 1', e)
            print(traceback.format_exc())
            connection.rollback()
            return False
        finally:
            cursor.close()
