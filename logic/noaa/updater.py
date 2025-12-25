import os
from .catalog import NoaaEncCell
from .downloader import NoaaEncDownloader
from .importer import NoaaEncImporter
from .validator import NoaaEncValidator


class NoaaUpdater:

    def __init__(
        self,
        log_callback=None,
        settings=None,
        db_manager=None,
    ):
        self.log = log_callback or print
        self.settings = settings
        self.db_manager = db_manager

    def tr(self, message):
        return QCoreApplication.translate("S57Settings", message)
    def update_cell(self, cell: NoaaEncCell, target_dir: str = None):
        """
        Mise à jour complète d'une cellule NOAA ENC.
        """
        self.log(self.tr("➡ Début mise à jour cellule {}").format(cell.id))

        # 1️⃣ Préparer le répertoire de destination
        if target_dir is None:
            target_dir = os.path.join(os.getcwd(), "noaa_cells")
        os.makedirs(target_dir, exist_ok=True)
        self.log(self.tr("📂 Répertoire de travail : {}").format(target_dir))

        # 2️⃣ Télécharger le fichier ZIP
        try:
            self.log(self.tr("⬇ Téléchargement de la cellule : {}...").format(cell.id))
            zip_path = self.downloader.download_cell(cell, target_dir)
            self.log(self.tr("✔ Téléchargé :  {}").format(zip_path))
        except Exception as e:
            self.log(self.tr("❌ Erreur téléchargement : {}").format(str(e)))
            return

        # 3️⃣ Valider le ZIP
        try:
            self.log(self.tr("🔍 Validation du ZIP…"))
            self.validator.validate_zip(zip_path)
            self.log(self.tr("✔ ZIP valide"))
        except Exception as e:
            self.log(self.tr("❌ Erreur validation : {}").format(str(e)))
            return

        # 4️⃣ Importer le S-57
        try:
            self.log(self.tr("📥 Import S-57…"))
            self.importer.import_S57_file(zip_path, target_dir)
            self.log(self.tr("✔ Import réussi"))
        except Exception as e:
            self.log(self.tr("❌ Erreur import : {}").format(str(e)))
            return

        self.log(self.tr("✅ Cellule {} mise à jour avec succès").format(cell.id))
