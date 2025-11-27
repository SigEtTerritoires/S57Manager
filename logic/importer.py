import os
from urllib.parse import quote
from qgis.core import QgsMessageLog
import subprocess
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QApplication
from osgeo import ogr, osr
from qgis.core import (
    QgsProject, QgsField, QgsFeatureRequest, QgsVectorLayer, QgsWkbTypes,
    QgsFields
)
from PyQt5.QtCore import QVariant
import re
from qgis.PyQt.QtSql import QSqlDatabase, QSqlQuery
class S57Importer:
    def __init__(self, settings, db_manager):
        self.db_manager = db_manager
        self.settings = settings
    # ------------------------------------------------------------------
    # IMPORT D’UN RÉPERTOIRE
    # ------------------------------------------------------------------


    def import_directory(self, directory, parent=None, progress=None):
        """
        Importe tous les fichiers S57 depuis le répertoire donné, soit vers PostGIS
        (code existant), soit vers un GeoPackage (nouveau code).
        """
        mode = self.settings.storage_mode()
        if mode == "postgis":
            # --- Import vers PostGIS (code existant) ---
            files = []
            
            for root, dirs, filenames in os.walk(directory):
                for f in filenames:
                    if f.lower().endswith('.000'):
                        files.append(os.path.join(root, f))

            if not files:
                QgsMessageLog.logMessage(self.tr('Aucun fichier .000 trouvé'), 'S57Manager')
                return
            total = len(files)
            for idx, f in enumerate(files, start=1):
                if progress:
                    if progress.cancelled:
                        return

                    progress.append_log(self.tr("📄 Fichier {} / {}  : {} ").format(idx,total,os.path.basename(f)))
                    progress.set_progress(int(idx * 100 / total))
                    QApplication.processEvents()

                self.import_s57_file(f, parent=parent, progress=progress)


            # --- 🔥 Post-traitement : mise à jour du schéma enc 🔥 ---
            try:
                conninfo = self.db_manager.settings.postgis_conn()
                db_params = {}
                for part in conninfo.split():
                    if "=" in part:
                        k, v = part.split("=", 1)
                        db_params[k.strip()] = v.strip()

                host = db_params.get("host", "localhost")
                port = db_params.get("port", "5432")
                dbname = db_params.get("dbname", "")
                user = db_params.get("user", "")
                pwd = db_params.get("password", "")
                # Connexion PostgreSQL via QtSql
                
                db.setHostName(host)
                db.setPort(int(port))
                db.setDatabaseName(dbname)
                db.setUserName(user)
                db.setPassword(pwd)
                
                if not db.open():
                    raise Exception(self.tr("Impossible de se connecter à la base PostgreSQL"))
                if progress:
                    progress.append_log(self.tr("  - Post-traitement des imports..."))
                    QApplication.processEvents()
                query = QSqlQuery(db)
                if not query.exec("SELECT public.clone_tables_with_prefix();"):
                    raise Exception(f"Erreur SQL : {query.lastError().text()}")

                db.commit()
                db.close()
                

                if progress:
                    progress.append_log(self.tr("✔ Mise à jour du schéma enc terminée."))
                    QApplication.processEvents()

            except Exception as e:
                if progress:
                    progress.append_log(self.tr("❌ Erreur clone_tables_with_prefix :\n{}").format(str(e)))
                    QApplication.processEvents()
                QgsMessageLog.logMessage(str(e), 'S57Manager')


        elif mode == "gpkg":
            # --- Import vers GeoPackage ---
            gpkg_path = self.settings.gpkg_path()

            if not gpkg_path:
                QgsMessageLog.logMessage(self.tr("Chemin GPKG non configuré dans les options."), "S57Manager")
                QMessageBox.warning(None, "S57Manager", self.tr("Veuillez configurer le chemin du GeoPackage dans les options."))
                return

            self.import_s57_files_gpkg(directory, gpkg_path, parent=parent,progress=progress)  # fonction que tu as déjà écrite
        else:
            QMessageBox.warning(None, "S57Manager",
                f"Mode de stockage inconnu : {mode}")

    def import_s57_file(self, s57_path,parent=None,progress=None):
        # --- Vérifie la connexion PostGIS ---
        try:
            db = self.db_manager.get_connection()
            db.close()  # on n'utilise la connexion que pour tester
        except Exception as e:
            QgsMessageLog.logMessage(self.tr("IImpossible de récupérer la connexion PostGIS:\n{}").format(str(e)), "S57Manager")
            return

        # --- Récupère les paramètres pour PG ---
        conninfo = self.db_manager.settings.postgis_conn()
        db_params = {}
        for part in conninfo.split():
            if "=" in part:
                k, v = part.split("=", 1)
                db_params[k.strip()] = v.strip()

        host = db_params.get("host", "localhost")
        port = db_params.get("port", "5432")
        dbname = db_params.get("dbname", "")
        user = db_params.get("user", "")
        pwd = db_params.get("password", "")
        if progress:
            progress.append_log(self.tr("📄 Fichier  {}").format(s57_path))
            QApplication.processEvents()
        # --- Schémas actifs comme dans le .bat ---
        schemas = {
            "pointsenc": ("MULTIPOINT", "OGR_GEOMETRY='POINT' or OGR_GEOMETRY='MULTIPOINT'", "pointsDSID"),
            "linesenc": ("MULTILINESTRING", "OGR_GEOMETRY='LINESTRING' or OGR_GEOMETRY='MULTILINESTRING'", "linesDSID"),
            "polysenc": ("MULTIPOLYGON", "OGR_GEOMETRY='POLYGON' or OGR_GEOMETRY='MULTIPOLYGON'", "polysDSID")
        }

        for schema, (nlt, where_clause, dsid_name) in schemas.items():
            # import principal
            if progress:
                progress.append_log(f"  - Import {schema}...")
                QApplication.processEvents()
            pg_conn = f'PG:host={host} port={port} dbname={dbname} user={user} password={pwd} active_schema={schema}'
            cmd_main = [
                "ogr2ogr",
                "-f", "PostgreSQL",
                pg_conn,
                s57_path,
                "-nlt", nlt,
                "-where", where_clause,
                "-skipfailures",
                "-append",
                "-update",
                "-s_srs", "EPSG:4326",
                "-t_srs", "EPSG:4326",
                "-oo", "RETURN_PRIMITIVES=ON",
                "-oo", "SPLIT_MULTIPOINT=ON",
                "-oo", "RETURN_LINKAGES=ON",
                "-oo", "LNAM_REFS=ON",
                "-oo", "ADD_SOUNDG_DEPTH=ON"
            ]
 
            # import DSID
            cmd_dsid = [
                "ogr2ogr",
                "-f", "PostgreSQL",
                pg_conn,
                s57_path,
                "DSID",
                "-nln", dsid_name,
                "-append",
                "-update"
            ]

            # --- Exécution ---
            for cmd in [cmd_main, cmd_dsid]:
                QgsMessageLog.logMessage(f"ogr2ogr: {' '.join(cmd)}", "S57Manager")
                try:
                    subprocess.check_call(cmd)
                except subprocess.CalledProcessError as e:
                    QgsMessageLog.logMessage(f"Erreur ogr2ogr: {e}", "S57Manager")
                except Exception as e:
                    QgsMessageLog.logMessage(f"Erreur import: {e}", "S57Manager")

        QgsMessageLog.logMessage(self.tr("Import terminé"), "S57Manager")
        




    # --- Fonctions de post-traitement intégrées ---
    def get_default_scale(self,geopackage_path, default_enc):
        geopackage = ogr.Open(geopackage_path, 0)
        default_scale = '0'
        default_enc = default_enc + '.000'
        if geopackage:
            dsid_layer = geopackage.GetLayerByName('DSID')
            if dsid_layer:
                dsid_layer.SetAttributeFilter(f"DSID_DSNM = '{default_enc}'")
                feature = dsid_layer.GetNextFeature()
                if feature:
                    default_scale = feature.GetField('DSPM_CSCL')
        return default_scale

    def get_default_purpose(self,geopackage_path, default_enc):
        geopackage = ogr.Open(geopackage_path, 0)
        default_purpose = '0'
        default_enc = default_enc + '.000'
        if geopackage:
            dsid_layer = geopackage.GetLayerByName('DSID')
            if dsid_layer:
                dsid_layer.SetAttributeFilter(f"DSID_DSNM = '{default_enc}'")
                feature = dsid_layer.GetNextFeature()
                if feature:
                    default_purpose = feature.GetField('DSID_INTU')
        return default_purpose

    def update_geopackage_dsid(self,gpkg_path, enc_file_name, scale=None, purpose=None):
        """
        Met à jour toutes les tables d'un GeoPackage S57 en ajoutant les champs enc_chart, scale et purpose.
        Supprime les tables vides.
        
        :param gpkg_path: chemin vers le GeoPackage
        :param enc_file_name: nom du fichier S57 traité
        :param scale: échelle de la carte (optionnel)
        :param purpose: finalité de la carte (optionnel)
        """
        gpkg = ogr.Open(gpkg_path, 1)  # mode écriture
        if gpkg is None:
            raise Exception(self.tr("Impossible d'ouvrir le GeoPackage : {}").format(gpkg_path))

        # Récupérer toutes les couches
        gpkg_layers = [gpkg.GetLayerByIndex(i).GetName() for i in range(gpkg.GetLayerCount())]

        for table_name in gpkg_layers:
            layer = gpkg.GetLayerByName(table_name)
            if layer is None:
                print(f"[WARN] La table '{table_name}' n'existe pas dans {gpkg_path}")
                continue

            # Supprimer les tables vides
            if layer.GetFeatureCount() == 0:
                gpkg.ExecuteSQL(f"DROP TABLE '{table_name}'")
                print(f"[INFO] Table '{table_name}' supprimée (vide)")
                continue

            # Ajouter les champs s'ils n'existent pas déjà
            field_names = [layer.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(layer.GetLayerDefn().GetFieldCount())]
            if "enc_chart" not in field_names:
                fld = ogr.FieldDefn("enc_chart", ogr.OFTString)
                fld.SetWidth(50)
                layer.CreateField(fld)

            if "scale" not in field_names and scale is not None:
                fld = ogr.FieldDefn("scale", ogr.OFTInteger)
                layer.CreateField(fld)

            if "purpose" not in field_names and purpose is not None:
                fld = ogr.FieldDefn("purpose", ogr.OFTString)
                fld.SetWidth(50)
                layer.CreateField(fld)

            # Remplir les valeurs des champs pour toutes les entités
            layer.StartTransaction()
            for feature in layer:
                feature.SetField("enc_chart", enc_file_name)
                if scale is not None:
                    feature.SetField("scale", scale)
                if purpose is not None:
                    feature.SetField("purpose", purpose)
                layer.SetFeature(feature)
            layer.CommitTransaction()

            print(f"[INFO] Table '{table_name}' mise à jour avec enc_chart, scale et purpose")

        gpkg = None


    def add_posacc_quapos(self, geopackage_path, progress=None):
        log = lambda m: (progress.append_log(m) if progress else QgsMessageLog.logMessage(m, "S57Manager"))


        tables_exclues = ["IsolatedNode", "ConnectedNode", "DSID", "C_AGGR", "C_ASSO", "layer_styles"]

        driver = ogr.GetDriverByName("GPKG")
        geopackage = driver.Open(geopackage_path, 1)

        if geopackage is None:
            log(self.tr("❌ Impossible d'ouvrir le GeoPackage."))
            return

        # -------- Vérifier existence d’IsolatedNode --------
        isolated_node_table = geopackage.GetLayerByName("IsolatedNode")
        if isolated_node_table is None:
            log(f"❌ Table IsolatedNode introuvable dans GPKG : {geopackage_path}")
            geopackage = None
            return
        

        isolated_defn = isolated_node_table.GetLayerDefn()

        # -------- Parcours des tables --------
        for i in range(geopackage.GetLayerCount()):
            table = geopackage.GetLayerByIndex(i)
            table_name = table.GetName()

            if table_name in tables_exclues:
                log(f"⏭ Table ignorée : {table_name}")
                continue



            table_defn = table.GetLayerDefn()

            # Vérifier présence des champs
            posacc_idx = table_defn.GetFieldIndex("POSACC")
            quapos_idx = table_defn.GetFieldIndex("QUAPOS")

            if posacc_idx == -1 or quapos_idx == -1:
 

                # Ajout des champs manquants
                if posacc_idx == -1:
                    table.CreateField(ogr.FieldDefn("POSACC", ogr.OFTString))
                if quapos_idx == -1:
                    table.CreateField(ogr.FieldDefn("QUAPOS", ogr.OFTString))

                # Recharger le defn
                table_defn = table.GetLayerDefn()
                posacc_idx = table_defn.GetFieldIndex("POSACC")
                quapos_idx = table_defn.GetFieldIndex("QUAPOS")



            table.ResetReading()

            # -------- Traitement des features --------
            for feature in table:
                rcid_full = feature.GetField("NAME_RCID")

                if not rcid_full:
                    log(f"   ⚠ NAME_RCID vide dans {table_name}, feature SKIPPED")
                    continue

                # Exemple format : "RCID:1043,"
                try:
                    rcid = rcid_full.split(":")[1].replace(",", "").strip()
                    rcid = rcid.replace(",", "").replace(")", "").strip()
                except Exception as e:
                    log(f"   ❌ Erreur parsing NAME_RCID='{rcid_full}' : {e}")
                    continue

                enc_chart = feature.GetField("enc_chart")



                isolated_node_table.SetAttributeFilter(f"RCID = '{rcid}' AND enc_chart = '{enc_chart}'")
                isolated_feature = isolated_node_table.GetNextFeature()

                if isolated_feature is None:
                    log(f"   ⚠ Aucun isolatednode correspondant (rcid={rcid})")
                    isolated_node_table.SetAttributeFilter(None)
                    continue

                # Récupération des valeurs
                posacc_value = isolated_feature.GetField("POSACC")
                quapos_value = isolated_feature.GetField("QUAPOS")



                # Mise à jour du feature
                feature.SetField(posacc_idx, posacc_value)
                feature.SetField(quapos_idx, quapos_value)
                table.SetFeature(feature)

                isolated_node_table.SetAttributeFilter(None)



        geopackage = None
        log("🎉 add_posacc_quapos terminé.")


    def add_posacc_quapos_lines(self,geopackage_path):
        """
        Met à jour les champs POSACC et QUAPOS des tables du GeoPackage
        à partir de la table Edge (objets linéaires).
        
        :param geopackage_path: Chemin du GeoPackage GPKG.
        :param progress: Objet optionnel de suivi, doit avoir méthode log(str).
        """
        tables_exclues = ["Edge", "IsolatedNode", "ConnectedNode", "DSID", "C_AGGR", "C_ASSO"]
        
        driver = ogr.GetDriverByName("GPKG")
        gpkg = driver.Open(geopackage_path, 1)
        if gpkg is None:
            raise Exception(f"Impossible d'ouvrir le GeoPackage : {geopackage_path}")

        # Table Edge
        edge_table = gpkg.GetLayerByName("Edge")
        if edge_table is None:
            raise Exception("Table 'Edge' introuvable dans le GeoPackage")

        total_tables = gpkg.GetLayerCount()
        for idx in range(total_tables):
            table = gpkg.GetLayerByIndex(idx)
            table_name = table.GetName()
            
            if table_name in tables_exclues or table_name == "Edge":
                continue

 
            table_defn = table.GetLayerDefn()
            edge_defn = edge_table.GetLayerDefn()
            rcid_idx_edge = edge_defn.GetFieldIndex("RCID")
            enc_chart_idx_edge = edge_defn.GetFieldIndex("enc_chart")

            posacc_idx = table_defn.GetFieldIndex("POSACC")
            quapos_idx = table_defn.GetFieldIndex("QUAPOS")

            table.ResetReading()
            for feature in table:
                rcid_full = feature.GetField("NAME_RCID")
                if not rcid_full or ":" not in rcid_full:
                    continue
                rcid = rcid_full.split(":")[1][:-1]
                rcid = rcid.replace(",", "").replace(")", "").strip()
                enc_chart = feature.GetField("enc_chart")

                # Filtrer Edge
                edge_table.SetAttributeFilter(f"RCID = '{rcid}' AND enc_chart = '{enc_chart}'")
                edge_feature = edge_table.GetNextFeature()
                if edge_feature:
                    if posacc_idx >= 0:
                        feature.SetField(posacc_idx, edge_feature.GetField("POSACC"))
                    if quapos_idx >= 0:
                        feature.SetField(quapos_idx, edge_feature.GetField("QUAPOS"))
                    table.SetFeature(feature)

        gpkg = None


    # --- Fonction principale d'import ---
    def import_s57_files_gpkg(self,directory, gpkg_path, parent=None,progress=None):
        """
        Importe tous les fichiers .000 depuis un répertoire vers un GeoPackage.
        """
        if not os.path.isdir(directory):
            QMessageBox.warning(parent, "Import S57", self.tr("Répertoire invalide."))
            return False

        if not os.path.exists(gpkg_path):
            QMessageBox.warning(parent, "Import S57", self.tr("GeoPackage introuvable : {}").format(gpkg_path))
            return False

        files = [os.path.join(dp, f) for dp, dn, fn in os.walk(directory) for f in fn if f.lower().endswith('.000')]
        
        if not files:
            QMessageBox.warning(parent, "Import S57", self.tr("Aucun fichier .000 trouvé."))
            return False
        # Au lieu de recevoir gpkg_path en argument, on le construit depuis les settings
        gpkg_dir = self.settings.gpkg_path()  # ex: C:/S57/geopak
        if not gpkg_dir or not os.path.isdir(gpkg_dir):
            QMessageBox.warning(parent, "Import S57", self.tr("Répertoire GeoPackage invalide ou non défini."))
            return False

        # Nom fixe du GeoPackage cible
        gpkg_path = os.path.join(gpkg_dir, "pointsENC.gpkg")
        total = len(files)
        for idx, file in enumerate(files, 1):
            if progress:
                if progress.cancelled:
                    return
                progress.append_log(self.tr("📄 Fichier {} / {} : {}").format(idx,total,os.path.basename(file)))
                progress.set_progress(int(idx * 100 / total))
                QApplication.processEvents()

            base_name = os.path.splitext(os.path.basename(file))[0]
            print(self.tr("[{} / {} ] Traitement de {}").format(idx,total,base_name))
            if progress:
                progress.append_log(self.tr("  • Extraction des points…"))
                QApplication.processEvents()

            # Commande ogr2ogr équivalente au .bat
            cmd = [
                "ogr2ogr",
                "-f", "GPKG",
                "-skipfailures",
                "-append",
                "-update",
                "-where", "OGR_GEOMETRY='POINT' OR OGR_GEOMETRY='MULTIPOINT'",
                "-oo", "SPLIT_MULTIPOINT=ON",
                "-oo", "RETURN_LINKAGES=ON",
                "-oo", "LNAM_REFS=ON",
                "-oo", "ADD_SOUNDG_DEPTH=ON",
                "-oo", "RETURN_PRIMITIVES=ON",
                "-nlt", "MULTIPOINT",
                "-mapFieldType", "StringList=String,IntegerList=String",
                gpkg_path,
                file
            ]

            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(parent, "Erreur import", f"Erreur sur {base_name} : {e}")
                return False
            if progress:
                progress.append_log(self.tr("  • Création des tables DSID et C_AGGR…"))
                QApplication.processEvents()

            # Import des tables DSID et C_AGGR
            for layer in ["DSID", "C_AGGR"]:
                cmd_layer = ["ogr2ogr", "-f", "GPKG", "-skipfailures", "-append", "-update", gpkg_path, file, layer]
                try:
                    subprocess.check_call(cmd_layer)
                except subprocess.CalledProcessError as e:
                    QMessageBox.critical(parent, "Erreur import", f"Erreur sur {base_name}, couche {layer} : {e}")
                    return False
            scale=self.get_default_scale(gpkg_path, base_name)
            purpose=self.get_default_purpose(gpkg_path, base_name)
            # --- Post-traitement Python intégré ---
            if progress:
                progress.append_log("  • Remplissage des tables avec DSID et C_AGGR…")
                QApplication.processEvents()
            self.update_geopackage_dsid(gpkg_path, base_name,scale,purpose)
            if progress:
                progress.append_log(self.tr("  • Mise à jour de POSACC et QUAPOS des tables…"))
                QApplication.processEvents()
            self.add_posacc_quapos(gpkg_path,progress=progress)


       
        # Nom fixe du GeoPackage cible
        gpkg_path = os.path.join(gpkg_dir, "linesENC.gpkg")
        total = len(files)
        for idx, file in enumerate(files, 1):
            base_name = os.path.splitext(os.path.basename(file))[0]
            print(f"[{idx}/{total}] Traitement de {base_name}")
            if progress:
                progress.append_log(self.tr("  • Extraction des lignes…"))
                QApplication.processEvents()

            # Commande ogr2ogr équivalente au .bat
            cmd = [
                "ogr2ogr",
                "-f", "GPKG",
                "-skipfailures",
                "-append",
                "-update",
                "-where", "OGR_GEOMETRY='LINESTRING' or OGR_GEOMETRY='MULTILINESTRING'",
                "-oo", "RETURN_LINKAGES=ON",
                "-oo", "LNAM_REFS=ON",
                "-oo", "RETURN_PRIMITIVES=ON",
                "-mapFieldType", "StringList=String,IntegerList=String",
                gpkg_path,
                file
            ]

            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(parent, "Erreur import", f"Erreur sur {base_name} : {e}")
                return False
            if progress:
                progress.append_log(self.tr("  • Création des tables DSID et C_AGGR…"))
                QApplication.processEvents()

            # Import des tables DSID et C_AGGR
            for layer in ["DSID", "C_AGGR"]:
                cmd_layer = ["ogr2ogr", "-f", "GPKG", "-skipfailures", "-append", "-update", gpkg_path, file, layer]
                try:
                    subprocess.check_call(cmd_layer)
                except subprocess.CalledProcessError as e:
                    QMessageBox.critical(parent, "Erreur import", f"Erreur sur {base_name}, couche {layer} : {e}")
                    return False
            scale=self.get_default_scale(gpkg_path, base_name)
            purpose=self.get_default_purpose(gpkg_path, base_name)
            # --- Post-traitement Python intégré ---
            if progress:
                progress.append_log(self.tr("  • Remplissage des tables avec DSID et C_AGGR…"))
                QApplication.processEvents()
            self.update_geopackage_dsid(gpkg_path, base_name,scale,purpose)
            if progress:
                progress.append_log(self.tr("  • Mise à jour de POSACC et QUAPOS des tables…"))
                QApplication.processEvents()
            self.add_posacc_quapos_lines(gpkg_path)
                
        # Nom fixe du GeoPackage cible pour les polygones
               
        gpkg_path = os.path.join(gpkg_dir, "polysENC.gpkg")
        
        # Créer le GeoPackage s'il n'existe pas encore
        if not os.path.exists(gpkg_path):
            from osgeo import ogr
            driver = ogr.GetDriverByName("GPKG")
            gpkg = driver.CreateDataSource(gpkg_path)
            if gpkg is None:
                QMessageBox.critical(parent, "Erreur", self.tr("Impossible de créer {}").format(gpkg_path))
                return False
            gpkg = None
            if progress:
                progress.append_log(self.tr("✅ Création du GeoPackage vide : {}").format(gpkg_path))
                QApplication.processEvents()

        total = len(files)
        for idx, file in enumerate(files, 1):
            base_name = os.path.splitext(os.path.basename(file))[0]
            if progress:
                progress.append_log(self.tr("[{}/{}] Traitement {} (polygones)…").format(idx,total,base_name))
                QApplication.processEvents()

            # Extraction des polygones avec ogr2ogr
            cmd = [
                "ogr2ogr",
                "-f", "GPKG",
                "-skipfailures",
                "-append",
                "-update",
                "-where", "OGR_GEOMETRY='POLYGON' OR OGR_GEOMETRY='MULTIPOLYGON'",
                "-oo", "RETURN_LINKAGES=ON",
                "-oo", "LNAM_REFS=ON",
                "-oo", "RETURN_PRIMITIVES=ON",
                "-mapFieldType", "StringList=String,IntegerList=String",
                gpkg_path,
                file
            ]
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(parent, "Erreur import",
                                     self.tr("Erreur sur {} :").format(str(e)))
                return False
            if progress:
                progress.append_log(self.tr("  • Création des tables DSID et C_AGGR…"))
                QApplication.processEvents()

            # Import des tables DSID et C_AGGR
            for layer in ["DSID", "C_AGGR"]:
                cmd_layer = ["ogr2ogr", "-f", "GPKG", "-skipfailures", "-append", "-update", gpkg_path, file, layer]
                try:
                    subprocess.check_call(cmd_layer)
                except subprocess.CalledProcessError as e:
                    QMessageBox.critical(parent, "Erreur import",
                                         self.tr("Erreur sur {}, couche {} : {}").format(base_name,layer,e))
                    return False

            # Calcul scale et purpose
            scale = self.get_default_scale(gpkg_path, base_name)
            purpose = self.get_default_purpose(gpkg_path, base_name)

            # Post-traitement Python
            if progress:
                progress.append_log(self.tr("  • Remplissage des tables avec DSID et C_AGGR…"))
                QApplication.processEvents()
            self.update_geopackage_dsid(gpkg_path, base_name, scale, purpose)


            # Mise à jour de la barre de progression globale
            if progress:
                progress.set_progress(int(idx * 100 / total))
                QApplication.processEvents()

        input_gpkg_paths = [
            os.path.join(gpkg_dir, "pointsENC.gpkg"),
            os.path.join(gpkg_dir, "linesENC.gpkg"),
            os.path.join(gpkg_dir, "polysENC.gpkg")
        ]
        output_gpkg_path = os.path.join(gpkg_dir, "ENC.gpkg")

        self.update_enc_gpkg(input_gpkg_paths, output_gpkg_path, progress=progress)

        return True
    def clear_gpkg_tables(self,gpkg_path, progress=None):
        gpkg = ogr.Open(gpkg_path, update=1)
        if gpkg is None:
            if progress:
                progress.append_log(self.tr("⚠ Impossible d’ouvrir {} pour nettoyage.").format(gpkg_path))
            return

        layer_count = gpkg.GetLayerCount()
        layers_to_delete = [gpkg.GetLayerByIndex(i).GetName() for i in range(layer_count)]

        for layer_name in layers_to_delete:
            sql = f"DROP TABLE IF EXISTS \"{layer_name}\""
            try:
                gpkg.ExecuteSQL(sql)
                if progress:
                    progress.append_log(self.tr("🗑 Suppression de la table {}").format(layer_name))
            except Exception as e:
                if progress:
                    progress.append_log(self.tr("⚠ Impossible de supprimer {} : {}").format(layer_name,e))

        gpkg = None

        if progress:
            progress.append_log(self.tr("✔ Tous les contenus de {} ont été supprimés.").format(os.path.basename(gpkg_path)))


    def update_enc_gpkg(self,input_geopackages, enc_gpkg_path, prefixes=None, progress=None):
        """
        Met à jour le GeoPackage ENC.gpkg à partir des GeoPackages points/lines/polys.
        
        :param input_geopackages: liste de chemins vers pointsENC.gpkg, linesENC.gpkg, polysENC.gpkg
        :param enc_gpkg_path: chemin vers ENC.gpkg de destination
        :param prefixes: liste de préfixes à ajouter aux noms de table ['pt_', 'li_', 'pl_']
        :param progress: objet optionnel avec méthode append_log(str)
        """
        if prefixes is None:
            prefixes = ["pt_", "li_", "pl_"]

        # Créer ENC.gpkg s’il n’existe pas
        if not os.path.exists(enc_gpkg_path):
            driver = ogr.GetDriverByName("GPKG")
            enc_gpkg = driver.CreateDataSource(enc_gpkg_path)
            if progress:
                progress.append_log(self.tr("✔ Création du GeoPackage {}").format(enc_gpkg_path))
            enc_gpkg = None

        driver = ogr.GetDriverByName("GPKG")

        for i, input_path in enumerate(input_geopackages):
            prefix = prefixes[i] if i < len(prefixes) else ""
            if progress:
                progress.append_log(self.tr("🔄 Ouverture du GeoPackage source : {}").format(input_path))

            input_gpkg = driver.Open(input_path, 0)
            if input_gpkg is None:
                if progress:
                    progress.append_log(self.tr("❌ Impossible d'ouvrir le GeoPackage {}").format(input_path))
                continue

            output_gpkg = driver.Open(enc_gpkg_path, 1)
            if output_gpkg is None:
                if progress:
                    progress.append_log(self.tr("❌ Impossible d'ouvrir le GeoPackage de destination {}").format(enc_gpkg_path))
                continue
            if progress:
                progress.append_log(self.tr("🔄 Ouverture du GeoPackage destination : {}").format(enc_gpkg_path))
            non_geom_tables = {"DSID", "C_AGGR", "C_ASSO", "IsolatedNode", "ConnectedNode"}

            for j in range(input_gpkg.GetLayerCount()):
                input_layer = input_gpkg.GetLayerByIndex(j)
                table_name = input_layer.GetName()
                # Ignorer les tables non géométriques dans lines/polys
                if table_name in non_geom_tables and prefix != "pt_":
                    if progress:
                        progress.append_log(self.tr(" Table non géométrique {} ignorée pour {}").format(table_name,prefix))
                    continue                
                output_table_name = f"{prefix}{table_name}"

                if progress:
                    progress.append_log(self.tr("📄 Traitement de la table {} → {}").format(table_name,output_table_name))
                # --- ⛔ Ignorer les tables vides ---
                feature_count = input_layer.GetFeatureCount()
                if feature_count == 0:
                    if progress:
                        progress.append_log(self.tr("⚠ Table {} ignorée (aucune entité)").format(table_name))
                    continue
                # Vérifier si la couche existe dans ENC.gpkg
                output_layer = output_gpkg.GetLayerByName(output_table_name)
                if output_layer is None:
                    # Créer la nouvelle couche
                    srs = osr.SpatialReference()
                    srs.ImportFromEPSG(4326)
                    output_layer = output_gpkg.CreateLayer(
                        output_table_name,
                        geom_type=input_layer.GetGeomType(),
                        srs=srs,
                        options=["OVERWRITE=YES"]
                    )
                    # Copier les champs
                    layer_defn = input_layer.GetLayerDefn()
                    for k in range(layer_defn.GetFieldCount()):
                        field_defn = layer_defn.GetFieldDefn(k)
                        output_layer.CreateField(field_defn)
                    if progress:
                        progress.append_log(self.tr("  • Création de la couche {}").format(output_table_name))

                # Copier les entités
                input_layer.ResetReading()
                for feature in input_layer:
                    out_feat = ogr.Feature(output_layer.GetLayerDefn())
                    geom = feature.GetGeometryRef()
                    if geom:
                        out_feat.SetGeometry(geom.Clone())
                    for idx in range(feature.GetFieldCount()):
                        out_feat.SetField(idx, feature.GetField(idx))
                    output_layer.CreateFeature(out_feat)
                    out_feat = None
                # Créer l'index spatial
                geom_field = output_layer.GetLayerDefn().GetGeomFieldDefn(0).GetName()                    
                if progress:
                    progress.append_log(self.tr("  • Copie des {} entités de {}").format(input_layer.GetFeatureCount(),table_name))
                try:
                    output_gpkg.ExecuteSQL("SELECT CreateSpatialIndex('{output_table_name}', '{geom_field}')")
                except:
                    if progress:
                        progress.append_log(self.tr("⚠ Index spatial déjà existant pour {}").format(output_table_name))
                if progress:
                    progress.append_log(self.tr("  • Index spatial créé pour {}").format(output_table_name))
            self.clear_gpkg_tables(input_path, progress)
            input_gpkg = None
            output_gpkg = None
            if progress:
                progress.append_log(self.tr("✔ Contenu de {} ajouté dans ENC.gpkg").format(input_path))
            layer = QgsVectorLayer(f"{enc_gpkg_path}|layername=pt_sbdare", "pt_sbdare", "ogr")

            provider = layer.dataProvider()
            fields = provider.fields()

            if not fields.indexOf("Label") != -1:
                provider.addAttributes([QgsField("Label", QVariant.String)])
                layer.updateFields()

            # -------------------------------------------------------
            #  1) Charger la couche natsurf et la convertir en dictionnaire
            # -------------------------------------------------------
            natsurf_layer = QgsVectorLayer(f"{enc_gpkg_path}|layername=natsurf", "natsurf", "ogr")
            if not natsurf_layer.isValid():
                QgsMessageLog.logMessage(self.tr("❌ Couche natsurf introuvable dans ENC.gpkg"), "S57Manager")
                return

            # Indexation rapide : dict[(NATSURT, NATQUAT)] = ETIQ
            dict_natsurf = {}

            for f in natsurf_layer.getFeatures():
                key = (str(f["NATSURT"]), str(f["NATQUAT"]) if f["NATQUAT"] not in [None, ""] else "NULL")
                dict_natsurf[key] = f["ETIQ"]


            # -------------------------------------------------------
            #  2) Fonction utilitaire identique à ton code
            # -------------------------------------------------------
            def extraire_parts_NATSURT(NATSUR):
                parts = NATSUR[3:-1].split(",")
                premier, deux, trois, quatre = None, None, None, None
                S1, S2, S3 = ".", ".", "."
                next_val = None
                ii = 0

                for i, part in enumerate(parts):
                    slash = part.find('/')
                    ff = 0
                    if slash != -1:
                        part, next_val = part.split('/')
                        ff = 1

                    if ff == 0:
                        if i == 0:
                            premier = part
                        if i == 1 and ii == 0:
                            deux = part
                        elif i == 1 and ii == 1:
                            trois = part
                        if i == 2 and ii <= 1:
                            trois = part
                        elif i == 2 and ii == 2:
                            quatre = part
                        if i == 3 and ii <= 2:
                            quatre = part

                    if ff == 1:
                        if i == 0:
                            premier = part
                            S1 = '/'
                            deux = next_val
                            ii = 1
                        if i == 1:
                            deux = part
                            S2 = '/'
                            trois = next_val
                            ii = 2
                        if i == 3:
                            trois = part
                            S3 = '/'
                            quatre = next_val
                            ii = 3
                            break

                return premier, deux, trois, quatre, S1, S2, S3


            # -------------------------------------------------------
            #  3) Calcul final du champ Label pour pt_sbdare
            # -------------------------------------------------------
            layer.startEditing()

            idx_Label = layer.fields().indexOf("Label")

            for f in layer.getFeatures():

                NATSUR = str(f["NATSUR"])
                NATQUA = str(f["NATQUA"])
                QUAPOS = f["QUAPOS"]

                p1, p2, p3, p4, S1, S2, S3 = extraire_parts_NATSURT(NATSUR)
                label = ""

                # -----------------------------------------------------------------
                # EXACTEMENT ta logique d'origine (mais optimisée)
                # -----------------------------------------------------------------

                def get_etiq(natsurt, natquat):
                    natquat = natquat if natquat not in [None, "", "NULL"] else "NULL"
                    return dict_natsurf.get((str(natsurt), str(natquat)), "")

                # === (1:...) =====================================================
                if NATSUR.startswith("(1:"):
                    if not NATQUA.startswith("(1:"):
                        # NATQUA simple → un NATSURT obligatoire + 2e optionnel
                        e1 = get_etiq(p1, "NULL")
                        if p2:
                            e2 = get_etiq(p2, "NULL")
                            label = f"{e1}/{e2}"
                        else:
                            label = e1
                    else:
                        # NATQUA multiple
                        NATQUAT1 = NATQUA.split(",")[0][3:-1]
                        e1 = get_etiq(p1, NATQUAT1)
                        if p2:
                            e2 = get_etiq(p2, "NULL")
                            label = f"{e1}/{e2}"
                        else:
                            label = e1

                # === (2:...) =====================================================
                elif NATSUR.startswith("(2:"):
                    # Même logique que ton script, mais accélérée
                    partsNQ = NATQUA[3:-1].split(",") if NATQUA.startswith("(") else []
                    NATQ1 = partsNQ[0] if len(partsNQ) > 0 else "NULL"
                    NATQ2 = partsNQ[1] if len(partsNQ) > 1 else "NULL"

                    e1 = get_etiq(p1, NATQ1)
                    e2 = get_etiq(p2, NATQ2)
                    label = f"{e1}{S1}{e2}"

                # === (3:...) =====================================================
                elif NATSUR.startswith("(3:"):
                    partsNQ = NATQUA[3:-1].split(",") if NATQUA.startswith("(") else []
                    NATQ1 = partsNQ[0] if len(partsNQ) > 0 else "NULL"
                    NATQ2 = partsNQ[1] if len(partsNQ) > 1 else "NULL"
                    NATQ3 = partsNQ[2] if len(partsNQ) > 2 else "NULL"

                    e1 = get_etiq(p1, NATQ1)
                    e2 = get_etiq(p2, NATQ2)
                    e3 = get_etiq(p3, NATQ3)
                    label = f"{e1}{S1}{e2}{S2}{e3}"

                # === (4:...) ou (5:...) ==========================================
                elif NATSUR.startswith("(4:") or NATSUR.startswith("(5:"):
                    partsNQ = NATQUA[3:-1].split(",") if NATQUA.startswith("(") else []
                    NATQ1 = partsNQ[0] if len(partsNQ) > 0 else "NULL"
                    NATQ2 = partsNQ[1] if len(partsNQ) > 1 else "NULL"
                    NATQ3 = partsNQ[2] if len(partsNQ) > 2 else "NULL"
                    NATQ4 = partsNQ[3] if len(partsNQ) > 3 else "NULL"

                    e1 = get_etiq(p1, NATQ1)
                    e2 = get_etiq(p2, NATQ2)
                    e3 = get_etiq(p3, NATQ3)
                    e4 = get_etiq(p4, NATQ4)
                    label = f"{e1}{S1}{e2}{S2}{e3}{S3}{e4}"

                # QUAPOS → préfixe PA/PD
                if QUAPOS == 4:
                    label = "PA" + label
                elif QUAPOS == 5:
                    label = "PD" + label

                f[idx_Label] = label
                layer.updateFeature(f)

            layer.commitChanges()

            if progress:
                progress.append_log(self.tr("✔ Calcul des étiquettes Label terminé."))



        if progress:
            progress.append_log(self.tr("✅ Mise à jour ENC.gpkg terminée."))



