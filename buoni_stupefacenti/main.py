import httpx
import datetime
import subprocess
import os
import shutil
import platform
from datetime import date
from pathlib import Path

import flet as ft
from pdf import creaPdf

from dotenv import load_dotenv
load_dotenv()

def last_day_of_month(any_day: datetime.date):
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    primoGiorno = datetime.datetime.strftime(any_day, "%d/%m/%Y")
    ultimoGiorno = datetime.datetime.strftime(next_month - datetime.timedelta(days=next_month.day), "%d/%m/%Y")
    return primoGiorno, ultimoGiorno

def loginFarmarete():
    with httpx.Client(timeout=None, follow_redirects=True, verify=False) as client:
        response = client.get("https://www.farmarete.it/api/shared/AppVersion")
        version = response.json()["version"]

        cookies = response.headers['Set-Cookie'].split(";")[0].split("=")
        cookies = {cookies[0]: cookies[1]}        

        json_data = {
            'username': os.getenv("FARMARETE_USERNAME"),
            'password': os.getenv("FARMARETE_PASSWORD"),
            'version': version,
        }

        response = client.post('https://www.farmarete.it/api/auth/login', json=json_data)

        print(client.headers, cookies, response.json())

    return client.headers, cookies, response.json()

def idBuoniAcquisto(client:httpx.Client, anno:int, mese:int, cookies, headers):
    primoGiorno, ultimoGiorno = last_day_of_month(datetime.date(anno, mese, 1))
    url = f"https://www.farmarete.it/api/stupeOrdini/elencoordini?pageSize=50&currentPage=0&sortField=dataInserimento&sortDirection=desc&searchText=&searchDateFrom={primoGiorno}&searchDateTo={ultimoGiorno}&searchStato=3,5,8,6,2,9,10&searchMagazzini=2,3&idFarmaciaAdminFiltro=0"
    response = client.get(url, cookies=cookies, headers=headers)
    print(response)
    ordiniEffettuati = response.json()
    idOrdine = [str(i["idOrdine"]) for i in ordiniEffettuati["items"]]
    print(ordiniEffettuati["nItems"], idOrdine)
    return idOrdine, ordiniEffettuati["nItems"]

def creaCartella(base_path: Path, anno: str, mese: str):
    path_cartella = base_path / anno / mese
    path_cartella.mkdir(parents=True, exist_ok=True)
    (path_cartella / "ordineFirmato").mkdir(exist_ok=True)
    (path_cartella / "ordineControFirmato").mkdir(exist_ok=True)
    return path_cartella

def download(pathPDF: Path, response):
    with open(pathPDF, "wb") as f:
        f.write(response.content)
    
def aperturaFile(pathCartella: Path, nomeFile: str):
    pathFile = pathCartella / nomeFile
    subprocess.Popen([str(pathFile)], shell=True)

def buoniAcquisto(anno: int, mese: int, openFile=False):
    headers, cookies, token = loginFarmarete()
    base_path = Path(os.getcwd()) / "documenti"
    with httpx.Client(timeout=None, follow_redirects=True, verify=False, headers=headers, cookies=cookies) as client:
        headers["Authorization"] = "Bearer " + token["token"]["token"]
        idOrdine, numeroOrdini = idBuoniAcquisto(client=client, anno=anno, mese=mese, cookies=cookies, headers=headers)
        pathCartella = creaCartella(base_path, str(anno), str(mese))

        for ordine_id in idOrdine:
            url = f"https://www.farmarete.it/api/shared/getUseOnceToken?contentId={ordine_id}"
            response = client.get(url, cookies=cookies, headers=headers)
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
            subprocess.Popen([str(pathPDFUnito)], shell=True)
        else:
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
    numeroOrdiniButton = ft.IconButton(icon=ft.icons.DOWNLOAD, on_click=ordini)

    page.add(ft.Row(
        controls=[
            annoTextField,
            meseTextField,
            numeroOrdiniButton
        ]
    ))

ft.app(main)