# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication, QSettings, QStandardPaths, Qt
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QListWidgetItem
from qgis.PyQt import uic
from qgis.core import QgsMessageLog, QgsApplication
import os
import shutil
import io
import psycopg2
from osgeo import ogr
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtSql import QSqlDatabase
from .logic.settings import S57Settings
from .logic.db_manager import DBManager
from .logic.importer import S57Importer
from .logic.display import S57Display
from qgis.PyQt.QtWidgets import (
    QDialog,  QTreeWidgetItem, QPushButton,
    QVBoxLayout, QLineEdit, QLabel, QWidget,QTreeWidget
)
from osgeo import gdal
from .gui.progress_dialog import ProgressDialog
from .outils_dialog import OutilsDialog

from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsProject, QgsMapLayerType
from qgis.PyQt.QtCore import QTranslator
from PyQt5.QtCore import  QCoreApplication, QLocale
from qgis.PyQt.QtGui import QIcon
from . import resources_rc


class S57ManagerPlugin:
    def __init__(self, iface):
        # Charger le traducteur AVANT initGui
        locale = QLocale.system().name()
        plugin_path = os.path.dirname(__file__)
        self.translator = QTranslator()
        self.translator.load(f"i18n/S57Manager_{locale}.qm", plugin_path)
        QCoreApplication.installTranslator(self.translator)
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.settings = S57Settings()
        self.db_manager = DBManager(self.settings)
        self.importer = S57Importer(self.settings, self.db_manager)
        self.display = S57Display(self.settings,self.db_manager, iface)
    # 🔸 Fonction de traduction
    def tr(self, message):
        return QCoreApplication.translate("S57ManagerPlugin", message)
    def initGui(self):
        # --- 🌐 Chargement traduction ---
        locale = QSettings().value('locale/userLocale')[0:2]  # ex: "en", "fr"
        self.translator = QTranslator()
        qm_path = os.path.join(self.plugin_dir, f"i18n/S57Manager_{locale}.qm")
        if os.path.exists(qm_path) and self.translator.load(qm_path):
            QCoreApplication.installTranslator(self.translator)        
        self.options_action = QAction(QIcon(":/S57Manager/icons/settings.png"),self.tr('Options S57'), self.iface.mainWindow())
 
        self.options_action.triggered.connect(self.open_options)

        self.import_action = QAction(QIcon(":/S57Manager/icons/import.png"),self.tr('Importer S57'), self.iface.mainWindow())
        self.import_action.triggered.connect(self.open_import)

        self.display_action = QAction(QIcon(":/S57Manager/icons/display.png"),self.tr('Afficher couches S57'), self.iface.mainWindow())
        self.display_action.triggered.connect(self.open_display)

        self.iface.addPluginToMenu('S57 Manager', self.options_action)
        self.iface.addPluginToMenu('S57 Manager', self.import_action)
        self.iface.addPluginToMenu('S57 Manager', self.display_action)
        self.action_outils = QAction(QIcon(":/S57Manager/icons/outils.png"),self.tr("Outils ENC"), self.iface.mainWindow())
        self.action_outils.triggered.connect(self.open_outils_dialog)
        self.iface.addPluginToMenu("&S57 Manager", self.action_outils)

    def unload(self):
        self.iface.removePluginMenu('S57 Manager', self.options_action)
        self.iface.removePluginMenu('S57 Manager', self.import_action)
        self.iface.removePluginMenu('S57 Manager', self.display_action)
        self.iface.removePluginMenu('S57 Manager', self.action_outils)

    def open_options(self):
        """Ouvre le dialogue Options S57 avec test de connexion PostGIS"""

        ui_path = os.path.join(os.path.dirname(__file__), 'gui', 'options_dialog.ui')
        dialog = uic.loadUi(ui_path)

        # ----------------------------------------------------------------------
        # Valeurs actuelles
        # ----------------------------------------------------------------------
        mode = self.settings.storage_mode()
        if mode == 'gpkg':
            dialog.radioGpkg.setChecked(True)
        else:
            dialog.radioPostgis.setChecked(True)

        # Le champ texte contient déjà le chemin enregistré
        dialog.lineGpkgPath.setText(self.settings.gpkg_path())

        # PostGIS : connection enregistrée
        dialog.comboPgConn.setEditText(self.settings.postgis_conn())

        # ----------------------------------------------------------------------
        # Bouton Installer la librairie SVG
        # ----------------------------------------------------------------------
        dialog.btnInstallSymbols.clicked.connect(
            lambda: self.install_svg_library_action(dialog)
        )

        # Installer symbologie → désactivé au départ
        dialog.btnInstallStyles.setEnabled(False)

        # ----------------------------------------------------------------------
        # Remplir le combo avec les connexions PostGIS existantes
        # ----------------------------------------------------------------------
        s = QSettings()
        connections = []

        for k in s.allKeys():
            if k.startswith("PostgreSQL/connections/") and k.endswith("/host"):
                name = k.split("/")[2]
                connections.append(name)

        dialog.comboPgConn.clear()
        dialog.comboPgConn.addItems(connections)

        # Sélectionner la connexion actuelle si elle existe
        current_conn = self.settings.postgis_conn()
        index = dialog.comboPgConn.findText(current_conn)
        if index >= 0:
            dialog.comboPgConn.setCurrentIndex(index)

        # ----------------------------------------------------------------------
        # Bouton "..." → choisir un dossier GPKG
        # ----------------------------------------------------------------------
        def on_browse_gpkg():
            folder = QFileDialog.getExistingDirectory(
                dialog,
                self.tr("Choisir un répertoire pour les GeoPackages")
            )
            if folder:
                dialog.lineGpkgPath.setText(folder)

        dialog.btnBrowseGpkg.clicked.connect(on_browse_gpkg)
        # ----- Bouton OK -----
        def on_ok():
            
            if dialog.radioGpkg.isChecked():
                folder = dialog.lineGpkgPath.text().strip()

                if not folder or not os.path.isdir(folder):
                    QMessageBox.warning(dialog, "S57Manager", self.tr("Veuillez choisir un dossier valide."))
                    return

                # Chemins attendus
                enc_path    = os.path.join(folder, "ENC.gpkg")
                points_path = os.path.join(folder, "pointsENC.gpkg")
                lines_path  = os.path.join(folder, "linesENC.gpkg")
                polys_path  = os.path.join(folder, "polysENC.gpkg")

                try:
                    # Créer les GPKG absents
                    ensure_gpkg_exists(enc_path)
                    ensure_gpkg_exists(points_path)
                    ensure_gpkg_exists(lines_path)
                    ensure_gpkg_exists(polys_path)

                except Exception as e:
                    QMessageBox.critical(dialog, "S57Manager",
                                         self.tr("Erreur lors de la création des GeoPackages :\n{}").format(str(e)))
                    return

                # Enregistrer les paramètres
                self.settings.set_storage_mode("gpkg")
                self.settings.set_gpkg_path(folder)
                update_install_styles_button()
                QMessageBox.information(dialog, "S57Manager",
                                        self.tr("Mode GeoPackage configuré avec succès.\n Les GeoPackages nécessaires ont été vérifiés/créés."))
                return

 

            else:
                self.settings.set_storage_mode('postgis')
                selected_name = dialog.comboPgConn.currentText()
                conn_string = get_postgis_conn_string(selected_name)
                if not conn_string:
                    QMessageBox.warning(dialog, "S57Manager", self.tr("Impossible de récupérer la connexion PostGIS"))
                    return

                # Test de la connexion
                ok, error_msg = test_postgis_connection(conn_string)
                if not ok:
                    QMessageBox.critical(dialog, "S57Manager",
                                         self.tr("Erreur connexion PostGIS:\n {}").format(error_msg))
                    return

                # Connexion OK, on sauvegarde et crée les schémas
                self.settings.set_postgis_conn(conn_string)
                try:
                    self.db_manager.ensure_postgis_schemas()
                except Exception as e:
                    QMessageBox.critical(dialog, "S57Manager",
                                         self.tr("Erreur lors de la création des schémas :\n{}").format(str(e)))
                    return

                # Activer le bouton Installer la symbologie après connexion OK
                update_install_styles_button()

            QMessageBox.information(dialog, 'S57Manager', 'Paramètres enregistrés')
        # ----------------------------------------------------------------------
        # SUITE DU CODE : update buttons, install styles, OK, Cancel…
        # (je peux t'envoyer la suite entièrement propre)
        # ----------------------------------------------------------------------

         # ----- Récupérer la vraie chaîne PostGIS depuis un nom -----
        def get_postgis_conn_string(name):
            if "=" in name:
                return name  # chaîne complète déjà saisie

            conn = {}
            prefix = f"PostgreSQL/connections/{name}/"
            for key in s.allKeys():
                if key.startswith(prefix):
                    subkey = key[len(prefix):]
                    conn[subkey] = s.value(key)

            parts = []
            if "host" in conn: parts.append(f"host={conn['host']}")
            if "database" in conn: parts.append(f"dbname={conn['database']}")
            if "username" in conn: parts.append(f"user={conn['username']}")
            if "password" in conn: parts.append(f"password={conn['password']}")
            if "port" in conn: parts.append(f"port={conn['port']}")
            return " ".join(parts)

        # ----- Test de connexion PostGIS -----
        def test_postgis_connection(conn_string):
            db = QSqlDatabase.addDatabase("QPSQL", "S57ManagerTest")
            for item in conn_string.split():
                if "=" not in item:
                    continue
                k, v = item.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "host":
                    db.setHostName(v)
                elif k == "dbname":
                    db.setDatabaseName(v)
                elif k == "user":
                    db.setUserName(v)
                elif k == "password":
                    db.setPassword(v)
                elif k == "port":
                    db.setPort(int(v))
            ok = db.open()
            error_msg = None if ok else db.lastError().text()
            db.close()
            return ok, error_msg



        def ensure_gpkg_exists(path):
            """Crée un GeoPackage valide si nécessaire."""
            driver = ogr.GetDriverByName("GPKG")

            if os.path.exists(path):
                # Vérifie que le fichier est réellement un GPKG
                try:
                    ds = driver.Open(path, 1)
                    if ds is None:
                        raise Exception(self.tr("Fichier existant mais invalide"))
                    ds = None
                    return True
                except:
                    raise Exception(f"{path} existe mais n'est pas un GeoPackage valide.")

            # Création d’un vrai GeoPackage
            ds = driver.CreateDataSource(path)
            if ds is None:
                raise Exception(self.tr("Impossible de créer un GeoPackage valide : {}").format(path))
            ds = None
            return True
        # ----- Fonction pour activer/désactiver le bouton Installer la symbologie -----
        def update_install_styles_button():
            # Mode PostGIS
            if dialog.radioPostgis.isChecked():
                conn_name = dialog.comboPgConn.currentText()
                conn_string = get_postgis_conn_string(conn_name)
                dialog.btnInstallStyles.setEnabled(bool(conn_string))
                return

            # Mode GPKG
            if dialog.radioGpkg.isChecked():
                path = dialog.lineGpkgPath.text().strip()
                enc_path = os.path.join(path, "ENC.gpkg")
                dialog.btnInstallStyles.setEnabled(os.path.exists(enc_path))
                return

            # Sécurité : désactiver par défaut
            dialog.btnInstallStyles.setEnabled(False)

        def on_install_styles():
            if dialog.radioGpkg.isChecked():
                on_install_styles_gpkg()
            else:
                on_install_styles_pg()

        # ----- Action du bouton Installer la symbologie -----
        def on_install_styles_pg():
            conn_name = dialog.comboPgConn.currentText()
            conn_string = get_postgis_conn_string(conn_name)
            if not conn_string:
                QMessageBox.warning(dialog, "S57Manager", self.tr("Aucune connexion PostGIS valide"))
                return

            plugin_dir = os.path.dirname(__file__)
            dump_file = os.path.join(plugin_dir, "dumplayersV2.sql")

            if not os.path.exists(dump_file):
                QMessageBox.critical(dialog, "Erreur", self.tr("Fichier SQL introuvable : {}").format(dump_file))
                return

            try:
                self.load_layerstyles(dump_file, conn_string)
                QMessageBox.information(dialog, "Succès", self.tr("La symbologie par défaut a été installée"))
            except Exception as e:
                QMessageBox.critical(dialog, "Erreur",self.tr("Impossible d'installer les styles :\n{}").format(str(e)))
        def on_install_styles_gpkg():
            directory = dialog.lineGpkgPath.text().strip()
            if not directory or not os.path.isdir(directory):
                QMessageBox.warning(dialog, "S57Manager",self.tr( "Veuillez sélectionner un répertoire GPKG valide."))
                return

            enc_path = os.path.join(directory, "ENC.gpkg")
            if not os.path.exists(enc_path):
                QMessageBox.critical(dialog, "Erreur", self.tr("Le fichier ENC.gpkg est introuvable dans :\n {}").format(directory))
                return

            # Fichier source contenant layer_styles + natsurf
            plugin_dir = os.path.dirname(__file__)
            source = os.path.join(plugin_dir, "resources", "layer_styles.gpkg")
            enc_path = os.path.join(directory, "ENC.gpkg")

            tables_to_copy = ["layer_styles", "natsurf"]

            for table in tables_to_copy:
                copy_table_gpkg(source, enc_path, table)
            # --- Mise à jour des chemins SVG dans layer_styles ---
            svg_path = get_svg_path()  

            if svg_path:
                cleaned_path = svg_path.replace("\\", "/")

                gpkg = ogr.Open(enc_path, 1)
                if gpkg:
                    sql = f"""
                    UPDATE layer_styles
                    SET styleqml = replace(styleqml,
                                           'svg:S57Manager',
                                           '{cleaned_path}')
                    WHERE styleqml LIKE '%svg:S57Manager%';
                    """
                    gpkg.ExecuteSQL(sql)
                    gpkg = None

            QMessageBox.information(dialog, "Succès",
                self.tr("Tables layer_styles et natsurf copiées dans ENC.gpkg."))

        
        dialog.btnInstallStyles.clicked.connect(on_install_styles)

        # PostGIS
        dialog.comboPgConn.currentIndexChanged.connect(update_install_styles_button)
        dialog.comboPgConn.editTextChanged.connect(update_install_styles_button)

        # GPKG
        dialog.lineGpkgPath.textChanged.connect(update_install_styles_button)

        # Changement de mode
        dialog.radioGpkg.toggled.connect(update_install_styles_button)
        

        def copy_table_gpkg(source_gpkg, dest_gpkg, table_name):
            """
            Copie une table depuis un GeoPackage source vers un autre GeoPackage destination,
            en écrasant la table cible si elle existe.
            """

            # Supprimer la table dans le GPKG destination si elle existe
            dest_ds = gdal.OpenEx(dest_gpkg, gdal.OF_UPDATE)
            if not dest_ds:
                raise Exception(self.tr("Impossible d’ouvrir le GeoPackage destination : {}").format(dest_gpkg))

            lyr = dest_ds.GetLayerByName(table_name)
            if lyr:
                dest_ds.DeleteLayer(table_name)
            dest_ds = None  # important : fermer avant VectorTranslate

            # Définir les options GDAL modernes
            options = gdal.VectorTranslateOptions(
                format="GPKG",
                accessMode="update",
                layers=[table_name],     # on copie uniquement cette table
                layerName=table_name     # nom de la table dans le fichier destination
            )

            # Lancement de la copie
            result = gdal.VectorTranslate(
                destNameOrDestDS=dest_gpkg,    # destination
                srcDS=source_gpkg,             # source
                options=options                # options définies
            )

            if result is None:
                raise Exception(self.tr("Échec lors de la copie de la table {}").format(table_name))


        

        def ensure_gpkg(path):
            """Crée un GeoPackage vide s'il n'existe pas."""
            if not os.path.exists(path):
                driver = ogr.GetDriverByName("GPKG")
                driver.CreateDataSource(path)

        def process_gpkg_directory(directory):
            """
            Vérifie et crée :
            - ENC.gpkg
            - pointsENC.gpkg
            - linesENC.gpkg
            - polysENC.gpkg
            """

            enc = os.path.join(directory, "ENC.gpkg")
            pts = os.path.join(directory, "pointsENC.gpkg")
            li  = os.path.join(directory, "linesENC.gpkg")
            pl  = os.path.join(directory, "polysENC.gpkg")

            ensure_gpkg(enc)
            ensure_gpkg(pts)
            ensure_gpkg(li)
            ensure_gpkg(pl)

            return enc, pts, li, pl

        def get_svg_path():
            """Retourne le chemin complet du dossier SVG/S57Manager tel que QGIS l'utilise."""
            # Chercher le répertoire SVG de QGIS
            svg_paths = QgsApplication.svgPaths()
            user_svg_path = None

            for p in svg_paths:
                # ex: C:/Users/.../AppData/Roaming/QGIS/QGIS3/profiles/default/svg
                if "profiles" in p and p.replace("\\", "/").endswith("/svg"):
                    user_svg_path = p
                    break

            if user_svg_path is None:
                # Fallback (rare)
                user_profile = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
                user_svg_path = os.path.join(user_profile, "svg")

            # chemin final
            final_svg = os.path.join(user_svg_path, "S57Manager")

            return final_svg.replace("\\", "/")

        dialog.buttonBox.accepted.connect(on_ok)
        dialog.buttonBox.rejected.connect(dialog.reject)

        # ----- Affichage du dialogue -----
        dialog.exec_()
    def open_import(self):
        ui_path = os.path.join(os.path.dirname(__file__), 'gui', 'import_dialog.ui')
        from qgis.PyQt import uic
        dialog = uic.loadUi(ui_path)

        def on_browse():
            from qgis.PyQt.QtWidgets import QFileDialog
            d = QFileDialog.getExistingDirectory(dialog, self.tr('Choisir un répertoire contenant des fichiers S57'))
            if d:
                dialog.lineDirectory.setText(d)
        dialog.btnBrowse.clicked.connect(on_browse)

        

        def on_start():
            directory = dialog.lineDirectory.text().strip()
            if not directory:
                QMessageBox.warning(dialog, "S57Manager", self.tr("Choisir un répertoire"))
                return

            dialog.btnStart.setEnabled(False)

            # ➜ Création & affichage de la fenêtre de progression
            progress = ProgressDialog(self.iface.mainWindow())
            progress.setWindowTitle("Import S-57")

            progress.show()
            QApplication.processEvents()   # <--- IMPORTANT !
            progress.append_log(self.tr("Démarrage de l'import…"))

            try:
                self.importer.import_directory(
                    directory,
                    parent=dialog,
                    progress=progress
                )
            except Exception as e:
                progress.append_log(f"❌ Erreur : {str(e)}")
                dialog.btnStart.setEnabled(True)
                return

            if not progress.cancelled:
                progress.append_log("✔ Import terminé.")
                progress.set_progress(100)
                QApplication.processEvents()  # <--- pour rafraîchir l'affichage final

            dialog.btnStart.setEnabled(True)
            QMessageBox.information(dialog, "S57Manager", self.tr("Import terminé."))



        dialog.btnStart.clicked.connect(on_start)
        dialog.exec_()




    def open_display(self):
        def on_item_changed(item, column):
            # Empêcher les boucles de signaux
            tree.blockSignals(True)

            state = item.checkState(0)

            # Si c'est un parent → synchroniser les enfants
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    child = item.child(i)
                    child.setCheckState(0, state)

            else:
                # Si c'est un enfant → mettre à jour le parent
                parent = item.parent()
                if parent is not None:
                    checked = 0
                    unchecked = 0
                    for i in range(parent.childCount()):
                        cs = parent.child(i).checkState(0)
                        if cs == Qt.Checked:
                            checked += 1
                        elif cs == Qt.Unchecked:
                            unchecked += 1

                    if checked == parent.childCount():
                        parent.setCheckState(0, Qt.Checked)
                    elif unchecked == parent.childCount():
                        parent.setCheckState(0, Qt.Unchecked)
                    else:
                        parent.setCheckState(0, Qt.PartiallyChecked)

            # Réactiver les signaux
            tree.blockSignals(False)
        # --- Charge UI minimale ou construit dynamiquement ---
        dialog = QDialog()
        dialog.setWindowTitle(self.tr("Afficher couches S-57"))

        layout = QVBoxLayout(dialog)

        # --- Barre de recherche ---
        lbl = QLabel(self.tr("Rechercher une couche :"))
        edit_search = QLineEdit()
        edit_search.setPlaceholderText(self.tr("Tapez pour filtrer..."))

        layout.addWidget(lbl)
        layout.addWidget(edit_search)

        # --- Arbre des couches ---
        tree = QTreeWidget()
        tree.setHeaderLabel(self.tr("Couches S-57"))
        layout.addWidget(tree)

        # --- Boutons sélecteur global ---
        btn_select_all = QPushButton(self.tr("Tout sélectionner"))
        btn_unselect_all = QPushButton(self.tr("Tout désélectionner"))
        layout.addWidget(btn_select_all)
        layout.addWidget(btn_unselect_all)

        # --- Bouton pour charger ---
        btn_load = QPushButton(self.tr("Charger les couches sélectionnées"))
        layout.addWidget(btn_load)

        # -------------------------------------------------------------------------------------
        # 📌 Données 
        # -------------------------------------------------------------------------------------
        # dictionnaire couche → groupe
        layer_to_group = {
            # Profondeurs / bathymétrie
            'pl_depare':self.tr('Profondeurs'),
            'pl_unsare':self.tr('Profondeurs'),
            'pl_tidewy':self.tr('Profondeurs'),
            'li_depare':self.tr('Profondeurs'),
            'li_depcnt':self.tr('Profondeurs'),

            # Obstacles / épaves
            'pl_damcon':self.tr('Obstacles / constructions'),
            'pl_causwy':self.tr('Obstacles / constructions'),
            'pl_hulkes':self.tr('Obstacles / épaves'),
            'pl_lokbsn':self.tr('Obstacles / constructions'),
            'pl_obstrn':self.tr('Obstacles / épaves'),
            'pl_ponton':self.tr('Obstacles / constructions'),
            'pl_pylons':self.tr('Obstacles / constructions'),
            'pl_sbdare':self.tr('Obstacles / aides à la navigation'),
            'pl_drgare':self.tr('Obstacles / aides à la navigation'),
            'pl_tsezne':self.tr('Obstacles / aides à la navigation'),
            'pl_wrecks':self.tr('Obstacles / épaves'),
            'pl_flodoc':self.tr('Obstacles / aides à la navigation'),

            # Terrains / zones terrestres
            'pl_lndare':self.tr('Terrains / terres'),
            'pl_canals':self.tr('Terrains / canaux'),
            'pl_lakare':self.tr('Terrains / lacs'),
            'pl_rivers':self.tr('Terrains / rivières'),
            'pl_buaare':self.tr('Terrains / zones bâties'),
            'pl_buislg':self.tr('Terrains / zones bâties'),
            'pl_chkpnt':self.tr('Terrains / points de contrôle'),
            'pl_convyr':self.tr('Terrains / infrastructures'),
            'pl_docare':self.tr('Terrains / infrastructures'),
            'pl_roadwy':self.tr('Terrains / routes'),
            'pl_runway':self.tr('Terrains / infrastructures'),
            'pl_drydoc':self.tr('Terrains / infrastructures'),
            'pl_dykcon':self.tr('Terrains / infrastructures'),
            'pl_forstc':self.tr('Terrains / nature'),
            'pl_gatcon':self.tr('Terrains / infrastructures'),
            'pl_lndmrk':self.tr('Terrains / landmarks'),
            'pl_slcons':self.tr('Terrains / infrastructures'),
            'pl_bridge':self.tr('Terrains / infrastructures'),
            'pl_wedklp':self.tr('Terrains / infrastructures'),
            'pl_wattur':self.tr('Énergies / turbines'),
            'pl_vegatn':self.tr('Végétation'),
            'pl_twrtpt':self.tr('Terrains / infrastructures'),
            'pl_tunnel':self.tr('Terrains / infrastructures'),
            'pl_tsslpt':self.tr('Terrains / infrastructures'),
            'pl_tesare':self.tr('Terrains / infrastructures'),
            'pl_swpare':self.tr('Terrains / zones d’eau'),
            'pl_splare':self.tr('Terrains / zones d’eau'),
            'pl_sndwav':self.tr('Terrains / zones d’eau'),
            'pl_smcfac':self.tr('Installations maritimes'),
            'pl_slogrd':self.tr('Installations maritimes'),
            'pl_siltnk':self.tr('Installations maritimes'),
            'pl_seaare':self.tr('Terrains / zones d’eau'),
            'pl_resare':self.tr('Terrains / zones d’eau'),
            'pl_rctlpt':self.tr('Terrains / infrastructures'),
            'pl_prdare':self.tr('Terrains / zones protégées'),
            'pl_prcare':self.tr('Terrains / zones protégées'),
            'pl_pipare':self.tr('Terrains / infrastructures'),
            'pl_pilbop':self.tr('Terrains / infrastructures'),
            'pl_ospare':self.tr('Terrains / infrastructures'),
            'pl_ofsplf':self.tr('Installations maritimes'),
            'pl_morfac':self.tr('Installations maritimes'),
            'pl_mipare':self.tr('Terrains / infrastructures'),
            'pl_marcul':self.tr('Installations maritimes'),
            'pl_logpon':self.tr('Installations maritimes'),
            'pl_lndrgn':self.tr('Terrains / zones dangereuses'),
            'pl_istzne':self.tr('Terrains / zones protégées'),
            'pl_iceare':self.tr('Terrains / zones glaciales'),
            'pl_hrbfac':self.tr('Installations maritimes'),
            'pl_hrbare':self.tr('Installations maritimes'),
            'pl_gridrn':self.tr('Terrains / infrastructure'),
            'pl_fshzne':self.tr('Zones de pêche'),
            'pl_fshgrd':self.tr('Zones de pêche'),
            'pl_fshfac':self.tr('Zones de pêche'),
            'pl_frpare':self.tr('Zones de pêche'),
            'pl_feryrt':self.tr('Zones de ferry'),
            'pl_fairwy':self.tr('Voies navigables'),
            'pl_exezne':self.tr('Zones d’exercice'),
            'pl_dwrtpt':self.tr('Installations maritimes'),
            'pl_dmpgrd':self.tr('Installations maritimes'),
            'pl_ctsare':self.tr('Installations maritimes'),
            'pl_ctnare':self.tr('Installations maritimes'),
            'pl_cblare':self.tr('Installations maritimes'),
            'pl_berths':self.tr('Installations maritimes'),
            'pl_airare':self.tr('Installations aériennes'),
            'pl_admare':self.tr('Installations maritimes'),
            'pl_achbrt':self.tr('Installations maritimes'),
            'pl_achare':self.tr('Installations maritimes'),
            
            # Lignes
            'li_rapids':self.tr('Lignes / rapides'),
            'li_marcul':self.tr('Lignes / installations'),
            'li_flodoc':self.tr('Lignes / hydrographie'),
            'li_lndmrk':self.tr('Lignes / points remarquables'),
            'li_feryrt':self.tr('Lignes / ferry'),
            'li_cblsub':self.tr('Lignes / câbles'),
            'li_coalne':self.tr('Lignes / canaux'),
            'li_depare':self.tr('Lignes / profondeurs'),
            'li_depcnt':self.tr('Lignes / profondeurs'),
            'li_lndare':self.tr('Lignes / terres'),
            'li_rivers':self.tr('Lignes / rivières'),
            'li_slcons':self.tr('Lignes / infrastructures'),
            'li_pipohd':self.tr('Lignes / pipelines'),
            'li_magvar':self.tr('Lignes / navigation'),
            'li_rectrc':self.tr('Lignes / routes'),
            'li_pipsol':self.tr('Lignes / pipelines'),
            'li_bridge':self.tr('Lignes / ponts'),
            'li_convyr':self.tr('Lignes / infrastructures'),
            'li_lndelv':self.tr('Lignes / relief'),
            'li_slotop':self.tr('Lignes / infrastructures'),
            'li_damcon':self.tr('Lignes / constructions'),
            'li_obstrn':self.tr('Lignes / obstacles'),
            'li_radlne':self.tr('Lignes / radiales'),
            'li_railwy':self.tr('Lignes / voies ferrées'),
            'li_roadwy':self.tr('Lignes / routes'),
            'li_causwy':self.tr('Lignes / constructions'),
            'li_watfal':self.tr('Lignes / cascades'),
            'li_cblohd':self.tr('Lignes / câbles'),
            'li_tssbnd':self.tr('Lignes / balises'),
            'li_wattur':self.tr('Lignes / turbines'),
            'li_morfac':self.tr('Lignes / infrastructures'),
            'li_gatcon':self.tr('Lignes / infrastructures'),
            'li_tselne':self.tr('Lignes / lignes de sel'),
            'li_dykcon':self.tr('Lignes / digues'),
            'li_vegatn':self.tr('Lignes / végétation'),
            'li_runway':self.tr('Lignes / pistes'),
            'li_fnclne':self.tr('Lignes / frontières'),
            'li_rdocal':self.tr('Lignes / routes locales'),
            'li_stslne':self.tr('Lignes / routes'),
            'li_navlne':self.tr('Lignes / navigation'),
            'li_oilbar':self.tr('Lignes / pipelines'),
            'li_canals':self.tr('Lignes / canaux'),
            'li_forstc':self.tr('Lignes / forêts'),
            'li_dwrtcl':self.tr('Lignes / infrastructures'),
            'li_tidewy':self.tr('Lignes / hydrographie'),
            'li_tunnel':self.tr('Lignes / tunnels'),
            'li_berths':self.tr('Lignes / installations maritimes'),
            'li_rcrtcl':self.tr('Lignes / infrastructures'),
            'li_fshfac':self.tr('Lignes / zones de pêche'),

            # Points
            'pt_roadwy':self.tr('Points / routes'),
            'pt_buaare':self.tr('Points / zones bâties'),
            'pt_dmpgrd':self.tr('Points / installations maritimes'),
            'pt_boycar':self.tr('Points / aides à la navigation'),
            'pt_boysaw':self.tr('Points / aides à la navigation'),
            'pt_achare':self.tr('Points / constructions'),
            'pt_boyinb':self.tr('Points / aides à la navigation'),
            'pt_pilbop':self.tr('Points / infrastructures'),
            'pt_ofsplf':self.tr('Points / installations maritimes'),
            'pt_boyspp':self.tr('Points / aides à la navigation'),
            'pt_fogsig':self.tr('Points / signaux'),
            'pt_lndare':self.tr('Points / terrains'),
            'pt_lndelv':self.tr('Points / terrains'),
            'pt_splare':self.tr('Points / zones d’eau'),
            'pt_lndrgn':self.tr('Points / terrains dangereux'),
            'pt_lights':self.tr('Points / aides à la navigation'),
            'pt_siltnk':self.tr('Points / installations maritimes'),
            'pt_wattur':self.tr('Points / turbines'),
            'pt_icnare':self.tr('Points / zones glaciales'),
            'pt_mipare':self.tr('Points / infrastructures'),
            'pt_ts_tis':self.tr('Points / signaux'),
            'pt_obstrn':self.tr('Points / obstacles'),
            'pt_pilpnt':self.tr('Points / points de pilotage'),
            'pt_rtpbcn':self.tr('Points / balises'),
            'pt_sbdare':self.tr('Points / aides à la navigation'),
            'pt_retrfl':self.tr('Points / réflecteurs'),
            'pt_soundg':self.tr('Points / signalisation sonore'),
            'pt_topmar':self.tr('Points / topographie maritime'),
            'pt_hulkes':self.tr('Points / épaves'),
            'pt_logpon':self.tr('Points / installations maritimes'),
            'pt_wedklp':self.tr('Points / infrastructures'),
            'pt_wrecks':self.tr('Points / épaves'),
            'pt_newobj':self.tr('Points / autres'),
            'pt_uwtroc':self.tr('Points / autres'),
            'pt_airare':self.tr('Points / installations aériennes'),
            'pt_curent':self.tr('Points / courants'),
            'pt_lndmrk':self.tr('Points / landmarks'),
            'pt_locmag':self.tr('Points / magnétiques'),
            'pt_seaare':self.tr('Points / zones d’eau'),
            'pt_litflt':self.tr('Points / feux'),
            'pt_boyisd':self.tr('Points / aides à la navigation'),
            'pt_ctnare':self.tr('Points / zones d’eau'),
            'pt_fshfac':self.tr('Points / pêche'),
            'pt_hrbfac':self.tr('Points / installations maritimes'),
            'pt_morfac':self.tr('Points / installations maritimes'),
            'pt_vegatn':self.tr('Points / végétation'),
            'pt_pipsol':self.tr('Points / pipelines'),
            'pt_gatcon':self.tr('Points / infrastructures'),
            'pt_smcfac':self.tr('Points / installations maritimes'),
            'pt_buisgl':self.tr('Points / zones bâties'),
            'pt_bcnlat':self.tr('Points / balises'),
            'pt_bcnspp':self.tr('Points / balises'),
            'pt_ctrpnt':self.tr('Points / centre'),
            'pt_forstc':self.tr('Points / forêts'),
            'pt_rdosta':self.tr('Points / routes'),
            'pt_damcon':self.tr('Points / constructions'),
            'pt_litves':self.tr('Points / feux'),
            'pt_bcncar':self.tr('Points / balises'),
            'pt_runway':self.tr('Points / pistes'),
            'pt_pylons':self.tr('Points / pylônes'),
            'pt_cgusta':self.tr('Points / infrastructures'),
            'pt_rctlpt':self.tr('Points / infrastructures'),
            'pt_ts_feb':self.tr('Points / signaux'),
            'pt_bridge':self.tr('Points / ponts'),
            'pt_spring':self.tr('Points / sources'),
            'pt_achbrt':self.tr('Points / constructions'),
            'pt_rdocal':self.tr('Points / routes locales'),
            'pt_boylat':self.tr('Points / aides à la navigation'),
            'pt_ts_pad':self.tr('Points / signaux'),
            'pt_ts_prh':self.tr('Points / signaux'),
            'pt_dismar':self.tr('Points / installations maritimes'),
            'pt_slogrd':self.tr('Points / installations maritimes'),
            'pt_sndwav':self.tr('Points / zones d’eau'),
            'pt_prdare':self.tr('Points / zones protégées'),
            'pt_sistaw':self.tr('Points / signaux'),
            'pt_radsta':self.tr('Points / radars'),
            'pt_cranes':self.tr('Points / grues'),
            'pt_marcul':self.tr('Points / infrastructures'),
            'pt_berths':self.tr('Points / installations maritimes'),
            'pt_rscsta':self.tr('Points / radars'),
            'pt_bcnsaw':self.tr('Points / balises'),
            'pt_sistat':self.tr('Points / signaux'),
            'pt_slcons':self.tr('Points / infrastructures'),
            'pt_bcnisd':self.tr('Points / balises'),
            'pt_daymar':self.tr('Points / balises'),
            'pt_watfal':self.tr('Points / cascades'),
        }


        if not hasattr(self.display, 'couches_a_charger'):
            QMessageBox.critical(None, "S57Manager", self.tr("display.py n'a pas couches_a_charger"))
            return

        couches = self.display.couches_a_charger   # (nom_table, echelle)

        # -------------------------------------------------------------------------------------
        # 🌳 Construction de l'arbre
        # -------------------------------------------------------------------------------------
        groups = {}

        for layer_name, echelle in couches:
            group_name = layer_to_group.get(layer_name, self.tr("Autres"))

            # Créer groupe si pas encore créé
            if group_name not in groups:
                parent = QTreeWidgetItem([group_name])
                parent.setCheckState(0, Qt.Checked)
                tree.addTopLevelItem(parent)
                groups[group_name] = parent
            else:
                parent = groups[group_name]

            # Créer couche
            child = QTreeWidgetItem([layer_name])
            child.setCheckState(0, Qt.Checked)
            parent.addChild(child)

        # -------------------------------------------------------------------------------------
        # 🔄 Gestion des cases parent/enfant
        # -------------------------------------------------------------------------------------
        def update_checks(item, col):
            if item.parent() is None:
                # parent modifié → appliquer aux enfants
                state = item.checkState(0)
                for i in range(item.childCount()):
                    child = item.child(i)
                    child.setCheckState(0, state)
            else:
                # enfant modifié → mettre le parent en checked / unchecked / partiel
                parent = item.parent()
                checked = sum(child.checkState(0) == Qt.Checked for child in [parent.child(i) for i in range(parent.childCount())])
                if checked == parent.childCount():
                    parent.setCheckState(0, Qt.Checked)
                elif checked == 0:
                    parent.setCheckState(0, Qt.Unchecked)
                else:
                    parent.setCheckState(0, Qt.PartiallyChecked)

        tree.itemChanged.connect(on_item_changed)

        # -------------------------------------------------------------------------------------
        # 🔍 Recherche / filtrage
        # -------------------------------------------------------------------------------------
        def apply_filter(text):
            text = text.lower().strip()

            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                parent_visible = False

                for j in range(parent.childCount()):
                    child = parent.child(j)
                    visible = text in child.text(0).lower()
                    child.setHidden(not visible)
                    if visible:
                        parent_visible = True

                parent.setHidden(not parent_visible)

        edit_search.textChanged.connect(apply_filter)

        # -------------------------------------------------------------------------------------
        # ⬆️ Tout sélectionner / ⬇️ Tout désélectionner
        # -------------------------------------------------------------------------------------
        def select_all():
            tree.blockSignals(True)
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                parent.setCheckState(0, Qt.Checked)
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    child.setCheckState(0, Qt.Checked)
            tree.blockSignals(False)

        def unselect_all():
            tree.blockSignals(True)
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                parent.setCheckState(0, Qt.Unchecked)
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    child.setCheckState(0, Qt.Unchecked)
            tree.blockSignals(False)


        btn_select_all.clicked.connect(select_all)
        btn_unselect_all.clicked.connect(unselect_all)

        # -------------------------------------------------------------------------------------
        # 🚀 Charger les couches cochées
        # -------------------------------------------------------------------------------------
        def load_selected():
            selected = []

            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    if child.checkState(0) == Qt.Checked:
                        selected.append(child.text(0))

            if not selected:
                QMessageBox.warning(None, "S57Manager", self.tr("Aucune couche sélectionnée"))
                return

            self.display.load_layers(selected)
            QMessageBox.information(None, "S57Manager", self.tr(" {} couches chargées").format(len(selected)))

        btn_load.clicked.connect(load_selected)

        # -------------------------------------------------------------------------------------
        dialog.exec_()



    from qgis.PyQt.QtCore import QSettings

    def get_postgis_connections(self):
        s = QSettings()
        keys = s.allKeys()
        connections = []
        for k in keys:
            if k.startswith("PostgreSQL/connections/") and k.endswith("/host"):
                # Extraire le nom de la connexion
                name = k.split("/")[2]
                connections.append(name)
        return connections
    def install_svg_library_action(self, parent_dialog=None):
        # 1. Dossier source dans le plugin
        plugin_dir = os.path.dirname(__file__)
        source_dir = os.path.join(plugin_dir, "svg_library")

        if not os.path.exists(source_dir):
            QMessageBox.critical(parent_dialog, "Erreur", self.str("Le dossier svg_library est introuvable dans le plugin."))
            return None

        # 2. Dossier utilisateur officiel QGIS
        user_profile = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        svg_user_dir = os.path.join(user_profile, "svg")
        os.makedirs(svg_user_dir, exist_ok=True)

        # 3. Trouver le bon répertoire svg du profil utilisateur
        svg_paths = QgsApplication.svgPaths()
        user_svg_path = None

        for p in svg_paths:
            if "AppData" in p and "profiles" in p:
                user_svg_path = p
                break

        if user_svg_path:
            target_dir = os.path.join(user_svg_path, "S57Manager")
        else:
            target_dir = os.path.join(svg_user_dir, "S57Manager")

        os.makedirs(target_dir, exist_ok=True)

        # 4. Copier les fichiers
        copied = 0
        skipped = 0
        for root, dirs, files in os.walk(source_dir):
            rel = os.path.relpath(root, source_dir)
            dest_path = os.path.join(target_dir, rel)
            os.makedirs(dest_path, exist_ok=True)

            for f in files:
                src_file = os.path.join(root, f)
                dest_file = os.path.join(dest_path, f)
                if not os.path.exists(dest_file):
                    shutil.copy2(src_file, dest_file)
                    copied += 1
                else:
                    skipped += 1

        # 5. Ajouter le dossier à QGIS si nécessaire
        if target_dir not in QgsApplication.svgPaths():
            QgsApplication.setSvgPaths(QgsApplication.svgPaths() + [target_dir])

        QMessageBox.information(
            parent_dialog,
            "Installation terminée",
            f"Bibliothèque SVG installée.\n"
            f"Copiés : {copied}\n"
            f"Ignorés : {skipped}\n"
            f"Dossier : {target_dir}"
        )

        return target_dir   # <<--- **AJOUT IMPORTANT**

    def load_layerstyles(self, dump_file, conn_str):
   
        """
        Charge le dump SQL des layer styles dans la base PostGIS.
        Gère les instructions SQL classiques et les blocs COPY ... FROM stdin.
        """
        # SQL de création (si nécessaire) de public.layer_styles
        create_layer_styles_sql = """
        CREATE TABLE IF NOT EXISTS public.layer_styles
        (
            id integer,
            f_table_catalog character varying,
            f_table_schema character varying,
            f_table_name character varying,
            f_geometry_column character varying,
            stylename text,
            styleqml xml,
            stylesld xml,
            useasdefault boolean,
            description text,
            owner character varying(63),
            ui xml,
            update_time timestamp without time zone,
            type character varying
        );
        ALTER TABLE IF EXISTS public.layer_styles OWNER TO postgres;
        """

        # Lire le fichier
        with open(dump_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Connexion
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()

        try:
            # 1) S'assurer que la table layer_styles existe
            cur.execute(create_layer_styles_sql)
            conn.commit()

            # 2) Parser le fichier pour gérer les blocs COPY séparément
            # On va parcourir le fichier : exécuter les SQL "normaux" (hors COPY)
            # et pour chaque COPY ... FROM stdin; ... \. -> utiliser copy_expert
            pos = 0
            length = len(content)
            import re
            copy_re = re.compile(r"^(COPY\s+[\w\.\"']+\s*\([^\)]*\)\s+FROM\s+stdin;)", re.IGNORECASE | re.MULTILINE)

            while pos < length:
                m = copy_re.search(content, pos)
                if not m:
                    # pas de COPY restant : exécuter le reste en tant que SQL normal
                    tail_sql = content[pos:].strip()
                    if tail_sql:
                        cur.execute(tail_sql)
                        conn.commit()
                    break

                # exécuter le SQL avant le COPY (si présent)
                start_copy = m.start()
                pre_sql = content[pos:start_copy].strip()
                if pre_sql:
                    cur.execute(pre_sql)
                    conn.commit()

                # récupérer l'en-tête COPY
                copy_header = m.group(1)  # ex: COPY public.layer_styles (...) FROM stdin;
                # trouver le début des données juste après l'en-tête
                data_start = m.end()

                # trouver la position de la ligne contenant seul "\." qui termine le COPY
                end_marker = content.find("\n\\.\n", data_start)
                if end_marker == -1:
                    # essayer alternative (fin de fichier ou windows line endings)
                    end_marker = content.find("\r\n\\.\r\n", data_start)
                if end_marker == -1:
                    raise RuntimeError("Dump SQL malformé : bloc COPY sans terminaison '\\.'")

                data_block = content[data_start:end_marker]

                # La commande copy_expert attend la commande COPY ... FROM STDIN avec le même header
                # on la passe telle quelle (en ascii/utf-8) et la data via StringIO
                # Normaliser copy header (retirer éventuels caractères de fin)
                copy_sql = copy_header.strip()

                # psycopg2 copy_expert nécessite une lecture binaire-compatible ; on utilise StringIO
                sio = io.StringIO(data_block)

                # exécuter la copy
                cur.copy_expert(copy_sql, sio)
                conn.commit()

                # avancer la position après la séquence "\.\n"
                pos = end_marker + len("\n\\.\n")

            # fini
        except Exception:
            conn.rollback()
            raise
        finally:
            # Ne pas fermer ici — on ferme plus bas après l'UPDATE
            pass

        # Maintenant que les données sont chargées, on fait la substitution SVG
        svg_path = self.install_svg_library_action()

        if svg_path:
            # Normalisation des antislashs Windows
            cleaned_path = svg_path.replace("\\", "/")

            sql = f"""
            UPDATE public.layer_styles
            SET styleqml = xmlparse(content replace(styleqml::text,
                                            'svg:S57Manager',
                                            '{cleaned_path}'
                                       ))
                    WHERE styleqml::text LIKE '%svg:S57Manager%';
            """

            try:
                cur.execute(sql)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()
                conn.close()
        else:
            # Si pas de chemin, on ferme quand même
            cur.close()
            conn.close()
    def import_mode(self):
        return self.value("import_mode", "files")
    def open_outils_dialog(self):
        dlg = OutilsDialog()

        # Filtrer par purpose
        dlg.btnFilterPurpose.clicked.connect(lambda: self.filter_by_purpose(dlg))

        # Retirer tous les filtres
        dlg.btnClearFilters.clicked.connect(self.clear_all_filters)

        # Appliquer échelles min/max
        dlg.btnApplyScale.clicked.connect(lambda: self.apply_scale_to_selected(dlg))

        dlg.exec()

    def clear_all_filters(self):
        from qgis.core import QgsProject, QgsMapLayerType

        project = QgsProject.instance()
        layers = project.mapLayers().values()

        count = 0
        for layer in layers:
            if layer.type() == QgsMapLayerType.VectorLayer:
                if layer.name().startswith(("pt_", "li_", "pl_")):
                    if layer.subsetString():
                        layer.setSubsetString("")  # enlever le filtre
                        count += 1

        QgsMessageLog.logMessage(
            f"✔ Filtres supprimés sur {count} couches",
            "S57Manager"
        )

        # rafraîchissement
        self.iface.mapCanvas().refresh()

    def filter_by_purpose(self, dlg):
        # Récupération de la valeur sélectionnée
        purpose_value = dlg.comboPurpose.currentIndex() + 1

        projet = QgsProject.instance()

        for couche in projet.mapLayers().values():
            if couche.type() != QgsMapLayerType.VectorLayer:
                continue

            if not couche.name().startswith(("pt_", "li_", "pl_")):
                continue

            if couche.fields().indexFromName("purpose") == -1:
                continue

            filtre = f'"purpose" = {purpose_value}'
            couche.setSubsetString(filtre)

        QgsMessageLog.logMessage(
            self.tr("Filtrage effectué : purpose = {}").format(purpose_value), "S57Manager"
        )
    def apply_scale_to_selected(self, dlg):
        try:
            min_scale = int(dlg.editScale.text()) if dlg.editScale.text().strip() else None
        except ValueError:
            QgsMessageLog.logMessage(self.str("❌ Échelle minimale invalide"), "S57Manager")
            return

        try:
            max_scale = int(dlg.editMaxScale.text()) if dlg.editMaxScale.text().strip() else None
        except ValueError:
            QgsMessageLog.logMessage(self.tr("❌ Échelle maximale invalide"), "S57Manager")
            return

        selected_layers = self.iface.layerTreeView().selectedLayers()

        if not selected_layers:
            QgsMessageLog.logMessage(self.tr("Aucune couche sélectionnée"), "S57Manager")
            return

        # Appliquer min/max scale
        for layer in selected_layers:
            layer.setScaleBasedVisibility(True)
            if min_scale is not None:
                layer.setMinimumScale(min_scale)
            if max_scale is not None:
                layer.setMaximumScale(max_scale)

        QgsMessageLog.logMessage(
            f"✔ Échelles appliquées : min={min_scale} max={max_scale} sur {len(selected_layers)} couches",
            "S57Manager"
        )

        # 🔄 Rafraîchissement du canvas pour voir les modifications
        self.iface.mapCanvas().refresh()


