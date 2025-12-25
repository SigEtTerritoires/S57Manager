# -*- coding: utf-8 -*-
"""
NOAA ENC Validator
------------------
Validation technique des fichiers ENC NOAA :
- présence du ZIP
- validité de l'archive
- présence du fichier .000 (S-57)
- extraction contrôlée
"""

import zipfile
from pathlib import Path
from typing import Optional


class NoaaEncValidationError(Exception):
    """Erreur de validation ENC NOAA"""
    pass


class NoaaEncValidator:
    """
    Validateur technique des cellules ENC NOAA.
    """

    def __init__(self, extract_dir: Optional[str] = None):
        """
        :param extract_dir: répertoire d'extraction des ENC
        """
        if extract_dir is None:
            extract_dir = Path.home() / ".s57manager" / "noaa_extract"
        self.extract_dir = Path(extract_dir)
        self.extract_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # Validation ZIP
    # ---------------------------------------------------------------

    def validate_zip(self, zip_path: Path) -> None:
        """
        Vérifie que le fichier ZIP est valide.

        :param zip_path: chemin du ZIP
        :raises NoaaEncValidationError:
        """
        if not zip_path.exists():
            raise NoaaEncValidationError(f"Fichier introuvable : {zip_path}")

        if not zipfile.is_zipfile(zip_path):
            raise NoaaEncValidationError(f"Archive ZIP invalide : {zip_path}")

    # ---------------------------------------------------------------
    # Inspection du contenu
    # ---------------------------------------------------------------

    def find_s57_file(self, zip_path: Path) -> str:
        """
        Recherche le fichier .000 (ENC S-57) dans l'archive.

        :param zip_path: chemin du ZIP
        :return: nom du fichier .000
        """
        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                if name.lower().endswith(".000"):
                    return name

        raise NoaaEncValidationError(
            f"Aucun fichier S-57 (.000) trouvé dans {zip_path.name}"
        )

    # ---------------------------------------------------------------
    # Extraction contrôlée
    # ---------------------------------------------------------------

    def extract_cell(self, zip_path: Path, overwrite: bool = False) -> Path:
        """
        Extrait la cellule ENC NOAA.

        :param zip_path: archive ZIP NOAA
        :param overwrite: écraser une extraction existante
        :return: chemin du dossier extrait
        """
        self.validate_zip(zip_path)

        cell_name = zip_path.stem
        target_dir = self.extract_dir / cell_name

        if target_dir.exists():
            if not overwrite:
                return target_dir
        else:
            target_dir.mkdir(parents=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(target_dir)

        # validation post-extraction
        s57_file = self.find_extracted_s57(target_dir)
        if s57_file is None:
            raise NoaaEncValidationError(
                f"Aucun fichier .000 après extraction de {zip_path.name}"
            )

        return target_dir

    # ---------------------------------------------------------------
    # Validation post-extraction
    # ---------------------------------------------------------------

    

    def find_extracted_s57(self, folder) -> Optional[Path]:
        """
        Recherche un fichier .000 dans un dossier extrait.

        :param folder: dossier extrait (str ou Path)
        :return: chemin du fichier .000 ou None
        """
        folder = Path(folder)

        for file in folder.rglob("*.000"):
            return file

        return None
