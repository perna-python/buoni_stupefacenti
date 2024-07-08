import PyPDF2
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def creaPdf(anno: str, mese: str, base_path: Path):
    logger.info(f"Creazione PDF per l'anno: {anno}, mese: {mese}")

    # Percorsi delle cartelle
    contro_firmato_path = base_path / anno / mese / "ordineControFirmato"
    firmato_path = base_path / anno / mese / "ordineFirmato"

    # Liste dei file PDF
    listaPdfControFirmato = [file for file in contro_firmato_path.iterdir() if file.suffix == ".pdf"]
    listaPdfFirmato = [file for file in firmato_path.iterdir() if file.suffix == ".pdf"]
    listaPdfPath = sorted(listaPdfControFirmato + listaPdfFirmato, key=lambda file: file.name)
    logger.info(f"Trovati {len(listaPdfFirmato)} firmati e {len(listaPdfControFirmato)} contro firmati")

    # Crea un oggetto PdfFileWriter per scrivere il nuovo file PDF
    pdfWriter = PyPDF2.PdfWriter()

    # Aggiungi pagine dai file PDF di origine al nuovo file
    for file_path in listaPdfPath:
        logger.info(f"Aggiungo pagina da {file_path}")
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                pdfWriter.add_page(page)

    # Percorso per il nuovo file PDF unificato
    output_file_path = base_path / anno / mese / 'stupefacenti.pdf'
    with open(output_file_path, 'wb') as outputFile:
        pdfWriter.write(outputFile)
        logger.info(f"PDF unificato creato in {output_file_path}")

    return output_file_path