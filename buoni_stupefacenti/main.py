import httpx
import datetime
import subprocess
import os
import platform
from datetime import date
from pathlib import Path
import logging

import flet as ft
from pdf import creaPdf

from config import FARMARETE_USERNAME, FARMARETE_PASSWORD

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def last_day_of_month(any_day: datetime.date):
    logger.info(f"Calcolo l'ultimo giorno per il mese di {any_day}")
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    primoGiorno = datetime.datetime.strftime(any_day, "%d/%m/%Y")
    ultimoGiorno = datetime.datetime.strftime(next_month - datetime.timedelta(days=next_month.day), "%d/%m/%Y")
    return primoGiorno, ultimoGiorno

def loginFarmarete():
    logger.info("Login in Farmarete")
    with httpx.Client(timeout=None, follow_redirects=True, verify=False) as client:
        response = client.get("https://www.farmarete.it/api/shared/AppVersion")
        version = response.json()["version"]

        json_data = {
            'username': FARMARETE_USERNAME,
            'password': FARMARETE_PASSWORD,
            'version': version,
        }

        response = client.post('https://www.farmarete.it/api/auth/login', json=json_data)
        logger.info("Login response: %s", response.json())

    return client.headers, response.json()

def idBuoniAcquisto(client:httpx.Client, anno:int, mese:int, headers):
    logger.info(f"Ricerca degli ID degli ordini dell'anno {anno}, mese {mese}")
    primoGiorno, ultimoGiorno = last_day_of_month(datetime.date(anno, mese, 1))
    url = f"https://www.farmarete.it/api/stupeOrdini/elencoordini?pageSize=50&currentPage=0&sortField=dataInserimento&sortDirection=desc&searchText=&searchDateFrom={primoGiorno}&searchDateTo={ultimoGiorno}&searchStato=3,5,8,6,2,9,10&searchMagazzini=2,3&idFarmaciaAdminFiltro=0"
    response = client.get(url, headers=headers)
    ordiniEffettuati = response.json()
    idOrdine = [str(i["idOrdine"]) for i in ordiniEffettuati["items"]]
    logger.info(f"Numero di ordini: {ordiniEffettuati["nItems"]}, ID ordini: {idOrdine}")
    return idOrdine, ordiniEffettuati["nItems"]

def creaCartella(base_path: Path, anno: str, mese: str):
    logger.info(f"Creazione cartella per anno: {anno}, mese: {mese}")
    path_cartella = base_path / anno / mese
    path_cartella.mkdir(parents=True, exist_ok=True)
    (path_cartella / "ordineFirmato").mkdir(exist_ok=True)
    (path_cartella / "ordineControFirmato").mkdir(exist_ok=True)
    return path_cartella

def download(pathPDF: Path, response):
    logger.info(f"Download file in {pathPDF}")
    with open(pathPDF, "wb") as f:
        f.write(response.content)
    
def aperturaFile(pathCartella: Path, nomeFile: str):
    logger.info(f"Apertura del file {nomeFile}")
    pathFile = pathCartella / nomeFile
    subprocess.Popen([str(pathFile)], shell=True)

def buoniAcquisto(anno: int, mese: int, openFile=False):
    logger.info(f"Processando gli ordine dell' anno {anno}, mese {mese}")
    headers, token = loginFarmarete()
    base_path = Path(os.getcwd()) / "documenti"
    with httpx.Client(timeout=None, follow_redirects=True, verify=False, headers=headers) as client:
        headers["Authorization"] = "Bearer " + token["token"]["token"]
        idOrdine, numeroOrdini = idBuoniAcquisto(client=client, anno=anno, mese=mese, headers=headers)
        pathCartella = creaCartella(base_path, str(anno), str(mese))

        for ordine_id in idOrdine:
            logger.info(f"Processando l'ID ordine {ordine_id}")
            url = f"https://www.farmarete.it/api/shared/getUseOnceToken?contentId={ordine_id}"
            response = client.get(url, headers=headers)
            token = response.json()["token"]

            # ordine firmato
            responseFirmato = client.get(f"https://www.farmarete.it/api/stupeordini/StampaOrdineFirmato?stato=F&token={token}")
            nomeFileFirmato = f"{ordine_id}Firmato.pdf"
            pathPDFFirmato = pathCartella / "ordineFirmato" / nomeFileFirmato
            download(pathPDF=pathPDFFirmato, response=responseFirmato)

            # ordine contro firmato
            responseControFirmato = client.get(f"https://www.farmarete.it/api/stupeordini/StampaOrdineFirmato?stato=C&token={token}")
            nomeFileControFirmato = f"{ordine_id}ControFirmato.pdf"
            pathPDFControFirmato = pathCartella / "ordineControFirmato" / nomeFileControFirmato
            download(pathPDF=pathPDFControFirmato, response=responseControFirmato)

        pathPDFUnito = creaPdf(anno=str(anno), mese=str(mese), base_path=base_path)

        if platform.system() == "Windows":
            logger.info("Apertura file PDF unito su Windows")
            subprocess.Popen([str(pathPDFUnito)], shell=True)
        else:
            logger.info("Apertura file PDF unito su Mac")
            subprocess.call(["open", str(pathPDFUnito)])

        if openFile:
            # apertura file Firmato
            for file in (pathCartella / "ordineFirmato").glob("*.pdf"):
                aperturaFile(pathCartella=pathCartella / "ordineFirmato", nomeFile=file.name)

            # apertura file contro Firmato
            for file in (pathCartella / "ordineControFirmato").glob("*.pdf"):
                aperturaFile(pathCartella=pathCartella / "ordineControFirmato", nomeFile=file.name)
                
def main(page: ft.Page):
    def ordini(e):
        buoniAcquisto(anno=int(annoTextField.value), mese=int(meseTextField.value))
    
    def meseValue():
        mese = int(date.today().month)
        return "12" if mese == 1 else str(mese - 1)
    
    def annoValue():
        anno = int(date.today().year)
        return str(anno - 1) if int(date.today().month) == 1 else str(anno)

    annoTextField =ft.TextField(label="anno", value=annoValue())
    meseTextField =ft.TextField(label="mese", value=meseValue())
    numeroOrdiniButton = ft.IconButton(icon=ft.Icons.DOWNLOAD, on_click=ordini)

    page.add(ft.Row(
        controls=[
            annoTextField,
            meseTextField,
            numeroOrdiniButton
        ]
    ))

ft.app(main)