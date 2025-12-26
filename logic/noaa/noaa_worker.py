from qgis.PyQt.QtCore import QObject, pyqtSignal
from pathlib import Path

from .catalog import NoaaEncCell
from .downloader import NoaaEncDownloader
from .importer import NoaaEncImporter
from ..settings import S57Settings
from qgis.PyQt.QtCore import QCoreApplication
class NoaaWorker(QObject):
    progress = pyqtSignal(str)       # messages log
    step_progress = pyqtSignal(int)  # barre de progression globale
    finished = pyqtSignal(bool, str,str) # succès, message final

    def __init__(
        self,
        cell: NoaaEncCell,
        target_dir: str,
        settings: S57Settings,
        db_manager,
        target: str,
        overwrite: bool = False,
    ):
        super().__init__()
        self.cell = cell
        self.target_dir = target_dir
        self.target = target
        self.overwrite = overwrite
        self.cancelled = False
        self.settings = settings
        self.db_manager = db_manager

        self.downloader = NoaaEncDownloader()
        self.importer = NoaaEncImporter(
            settings=self.settings,
            db_manager=self.db_manager,
        )
    def tr(self, message):
        return QCoreApplication.translate("S57Settings", message)
    def run(self):
        try:
            self.progress.emit(self.tr("Téléchargement de la cellule {}…").format(self.cell.id))
            zip_path = self.downloader.download_cell(self.cell, self.target_dir)

            self.progress.emit(self.tr("Décompression de {}…").format(zip_path.name))
            extract_dir = self.importer.validator.extract_cell(
                zip_path,
                overwrite=self.overwrite,
            )

            self.progress.emit(self.tr("Import des fichiers S-57 dans QGIS…"))

            self.importer.import_extracted_directory(
                extract_dir,
                parent=None,
                progress=self,
            )

            self.progress.emit(self.tr("Import de {} terminé").format(self.cell.id))
            self.finished.emit(True,self.tr("Cellule {} importée avec succès").format(self.cell.id),self.cell.id)


        except Exception as e:
            self.finished.emit(False, self.tr("Erreur : {}").format(str(e)),"")
    def append_log(self, message: str):
        self.progress.emit(message)

    def set_progress(self, value: int):
        self.step_progress.emit(value)

