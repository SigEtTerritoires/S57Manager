from pathlib import Path
from typing import Optional

from .validator import NoaaEncValidator, NoaaEncValidationError
from ..importer import S57Importer
from ..settings import S57Settings

class NoaaEncImportError(Exception):
    """Erreur lors de l'import NOAA ENC"""
    pass


class NoaaEncImporter:
    """
    Importateur NOAA ENC basé sur S57Manager.
    """

    def __init__(self, settings: S57Settings, db_manager):
        self.settings = settings
        self.db_manager = db_manager
        self.validator = NoaaEncValidator()

    # ---------------------------------------------------------
    # Import principal depuis ZIP
    # ---------------------------------------------------------

    def import_zip(self, zip_path: Path, target: str = "postgis", overwrite: bool = False):
        """
        Importe une cellule ENC NOAA depuis un ZIP.
        """
        try:
            extract_dir = self.validator.extract_cell(zip_path, overwrite=overwrite)
        except NoaaEncValidationError as e:
            raise NoaaEncImportError(str(e))

        s57_file = self.validator.find_extracted_s57(extract_dir)
        if not s57_file:
            raise NoaaEncImportError(self.tr("Fichier S-57 introuvable après extraction : {}").format(zip_path.name))

        self.import_s57_file(s57_file, target=target, overwrite=overwrite)

    # ---------------------------------------------------------
    # Import S-57 générique
    # ---------------------------------------------------------

    def import_extracted_directory(
        self,
        directory: Path,
        parent=None,
        progress=None,
    ):
        """
        Import d'un dossier ENC NOAA déjà extrait
        (contient un ou plusieurs fichiers .000)
        """
        importer = S57Importer(
            settings=self.settings,
            db_manager=self.db_manager,
        )

        importer.import_directory(
            str(directory),
            parent=parent,
            progress=progress,
        )
