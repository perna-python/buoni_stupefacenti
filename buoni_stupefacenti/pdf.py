import PyPDF2
import os
from pathlib import Path

def creaPdf(anno: str, mese: str, base_path: Path):
    # Percorsi delle cartelle
    contro_firmato_path = base_path / anno / mese / "ordineControFirmato"
    firmato_path = base_path / anno / mese / "ordineFirmato"

    # Liste dei file PDF
    listaPdfControFirmato = [file for file in contro_firmato_path.iterdir() if file.suffix == ".pdf"]
    listaPdfFirmato = [file for file in firmato_path.iterdir() if file.suffix == ".pdf"]
    listaPdf = sorted(listaPdfControFirmato + listaPdfFirmato)

    # Lista dei percorsi dei file PDF
    listaPdfPath = [
        file if "ControFirmato" in file.stem else file
        for file in listaPdf
    ]

    # Crea un oggetto PdfFileWriter per scrivere il nuovo file PDF
    pdfWriter = PyPDF2.PdfWriter()

    # Aggiungi pagine dai file PDF di origine al nuovo file
    for file_path in listaPdfPath:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                pdfWriter.add_page(page)

    # Percorso per il nuovo file PDF unificato
    output_file_path = base_path / anno / mese / 'stupefacenti.pdf'
    with open(output_file_path, 'wb') as outputFile:
        pdfWriter.write(outputFile)

    return output_file_path