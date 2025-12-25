# -*- coding: utf-8 -*-
"""
NOAA ENC Downloader
------------------
Télécharge des cellules ENC depuis le catalogue NOAA.
Gère :
- les URLs
- le téléchargement sécurisé
- le cache local
- vérification basique
"""

import os
import requests
from pathlib import Path
from typing import Optional
from .catalog import NoaaEncCell


class NoaaEncDownloader:
    """
    Gestionnaire de téléchargement des fichiers ENC NOAA.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        :param cache_dir: répertoire local pour stocker les fichiers téléchargés
        """
        if cache_dir is None:
            cache_dir = os.path.join(os.path.expanduser("~"), ".s57manager", "noaa_enc")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # Téléchargement d'une cellule
    # ---------------------------------------------------------------

    def download_cell(self, cell: NoaaEncCell, force: bool = False) -> Path:
        """
        Télécharge une cellule ENC NOAA.

        :param cell: NoaaEncCell à télécharger
        :param force: ignorer le cache et forcer le téléchargement
        :return: chemin local du fichier téléchargé (ZIP)
        """
        if cell.zip_url is None:
            raise ValueError(self.tr("Cellule {} n'a pas d'URL de téléchargement.").format(cell.id))

        filename = f"{cell.id}.zip"
        dest_path = self.cache_dir / filename

        if dest_path.exists() and not force:
            return dest_path

        # téléchargement
        response = requests.get(cell.zip_url, stream=True)
        response.raise_for_status()

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return dest_path

    # ---------------------------------------------------------------
    # Téléchargement multiple
    # ---------------------------------------------------------------

    def download_cells(self, cells: list[NoaaEncCell], force: bool = False) -> list[Path]:
        """
        Télécharge plusieurs cellules NOAA.

        :param cells: liste de NoaaEncCell
        :param force: ignorer le cache
        :return: liste des chemins locaux
        """
        local_paths = []
        for cell in cells:
            path = self.download_cell(cell, force=force)
            local_paths.append(path)
        return local_paths
