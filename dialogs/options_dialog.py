from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsSettings, QgsProviderRegistry
import os
import shutil
from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QMessageBox
import psycopg2
from qgis.PyQt import QtWidgets, uic
import os

# Charge le .ui et renvoie la classe et le baseclass
ui_path = os.path.join(os.path.dirname(__file__), "options_dialog.ui")
OptionsDialogUI, BaseDialog = uic.loadUiType(ui_path)

class OptionsDialog(BaseDialog, OptionsDialogUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)  # Important ! Expose tous les widgets

        # Maintenant tous les widgets du .ui sont accessibles
        # Exemple : btnInstallSymbols, comboPgConn, radioGpkg, etc.

        # Connexions des boutons
        self.btnBrowseGpkg.clicked.connect(self.chooseGpkg)
        self.buttonBox.accepted.connect(self.saveSettings)
        self.buttonBox.rejected.connect(self.reject)
        self.radioGpkg.toggled.connect(self.updateGui)
        self.radioPostgis.toggled.connect(self.updateGui)

        # Autres initialisations
        self.populatePostgisConnections()
        self.updateGui()


    def populatePostgisConnections(self):
        """Remplit la combo avec toutes les connexions PostGIS existantes dans QGIS"""
        from qgis.core import QgsProviderRegistry
        registry = QgsProviderRegistry.instance()
        pg_conns = registry.providerMetadata("postgres").connectionNames()
        self.comboPgConn.clear()
        self.comboPgConn.addItems(pg_conns)

        # Charger la connexion précédemment sélectionnée
        s = QgsSettings()
        current_conn = s.value("S57Manager/pg_conn", "")
        index = self.comboPgConn.findText(current_conn)
        if index >= 0:
            self.comboPgConn.setCurrentIndex(index)

    def updateGui(self):
        """Active/désactive les champs selon le mode choisi"""
        is_gpkg = self.radioGpkg.isChecked()
        self.lineGpkgPath.setEnabled(is_gpkg)
        self.btnBrowseGpkg.setEnabled(is_gpkg)
        self.comboPgConn.setEnabled(self.radioPostgis.isChecked())

    def chooseGpkg(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choisir le répertoire du GeoPackage ENC",
            "",
            QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        )

        if folder:
            # On stocke uniquement le dossier
            self.lineGpkgPath.setText(folder)


    def saveSettings(self):
        """Enregistre les options dans QgsSettings"""
        s = QgsSettings()
        if self.radioGpkg.isChecked():
            s.setValue("S57Manager/storage", "gpkg")
            s.setValue("S57Manager/gpkg_path", self.lineGpkgPath.text())
        else:
            s.setValue("S57Manager/storage", "postgis")
            # stocke uniquement le nom de connexion QGIS
            s.setValue("S57Manager/pg_conn", self.comboPgConn.currentText())
        self.accept()
    


    def install_default_styles_action(self):
        """Installe la symbologie par défaut dans la base PostGIS sélectionnée"""

        # Récupère la connexion QGIS choisie
        conn_name = self.comboPgConn.currentText()
        if not conn_name:
            QMessageBox.warning(self, self.tr("Connexion manquante"), self.tr("Veuillez choisir une connexion PostGIS."))
            return

        # Récupérer la chaîne de connexion complète depuis QGIS
        from qgis.core import QgsDataSourceUri
        registry = QgsProviderRegistry.instance()
        uri = QgsDataSourceUri()
        uri.setConnectionFromString(conn_name)
        conn_str = f"host={uri.host()} port={uri.port()} dbname={uri.database()} user={uri.username()} password={uri.password()}"

        # Chemin du dump SQL dans le plugin
        plugin_dir = os.path.dirname(__file__)
        dump_file = os.path.join(plugin_dir, "dumplayers.sql")

        if not os.path.exists(dump_file):
            QMessageBox.critical(self, "Erreur", f"Fichier SQL introuvable : {dump_file}")
            return

        try:
            # Exécuter le dump SQL
            self.load_layerstyles(dump_file, conn_str)
            QMessageBox.information(self, "Succès", self.tr("La symbologie par défaut a été installée dans la base PostGIS."))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'installer les styles :\n{str(e)}")


    def load_layerstyles(self,dump_file, conn_str):
        with open(dump_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()
