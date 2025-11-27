from qgis.core import QgsProject, QgsVectorLayer, QgsDataSourceUri, QgsMapLayerStyle
from qgis.core import QgsMessageLog

class S57Display:
    def __init__(self, settings,db_manager, iface):
        self.db_manager = db_manager
        self.iface = iface
        self.settings = settings
        # Liste des couches à charger (nom_table, echelle_min)
        self.couches_a_charger = [
            ('pl_depare', 100000000),
            ('pl_unsare', 100000000),
            ('pl_tidewy', 100000000),
            ('pl_damcon', 100000000),
            ('pl_causwy', 100000000),
            ('pl_hulkes', 100000000),
            ('pl_lokbsn', 100000000),
            ('pl_obstrn', 100000000),
            ('pl_ponton', 100000000),
            ('pl_pylons', 100000000),
            ('pl_sbdare', 100000000),
            ('pl_drgare', 100000000),
            ('pl_tsezne', 100000000),
            ('pl_wrecks', 100000000),
            ('pl_flodoc', 100000000),
            ('pl_lndare', 100000000),
            ('pl_canals', 100000000),
            ('pl_lakare', 100000000),
            ('pl_rivers', 100000000),
            ('pl_buaare', 100000000),
            ('pl_buislg', 100000000),
            ('pl_chkpnt', 100000000),
            ('pl_convyr', 100000000),
            ('pl_docare', 100000000),
            ('pl_roadwy', 100000000),
            ('pl_runway', 100000000),
            ('pl_drydoc', 100000000),
            ('pl_dykcon', 100000000),
            ('pl_forstc', 100000000),
            ('pl_gatcon', 100000000),
            ('pl_lndmrk', 100000000),
            ('pl_slcons', 100000000),
            ('pl_bridge', 100000000),
            ('pl_wedklp', 100000000),
            ('pl_wattur', 100000000),
            ('pl_vegatn', 100000000),
            ('pl_twrtpt', 100000000),
            ('pl_tunnel', 100000000),
            ('pl_tsslpt', 100000000),
            ('pl_tesare', 100000000),
            ('pl_swpare', 100000000),
            ('pl_splare', 100000000),
            ('pl_sndwav', 100000000),
            ('pl_smcfac', 100000000),
            ('pl_slogrd', 100000000),
            ('pl_siltnk', 100000000),
            ('pl_seaare', 100000000),
            ('pl_resare', 100000000),
            ('pl_rctlpt', 100000000),
            ('pl_prdare', 100000000),
            ('pl_prcare', 100000000),
            ('pl_pipare', 100000000),
            ('pl_pilbop', 100000000),
            ('pl_ospare', 100000000),
            ('pl_ofsplf', 100000000),
            ('pl_morfac', 100000000),
            ('pl_mipare', 100000000),
            ('pl_marcul', 100000000),
            ('pl_logpon', 100000000),
            ('pl_lndrgn', 100000000),
            ('pl_istzne', 100000000),
            ('pl_iceare', 100000000),
            ('pl_hrbfac', 100000000),
            ('pl_hrbare', 100000000),
            ('pl_gridrn', 100000000),
            ('pl_fshzne', 100000000),
            ('pl_fshgrd', 100000000),
            ('pl_fshfac', 100000000),
            ('pl_frpare', 100000000),
            ('pl_feryrt', 100000000),
            ('pl_fairwy', 100000000),
            ('pl_exezne', 0),
            ('pl_dwrtpt', 100000000),
            ('pl_dmpgrd', 100000000),
            ('pl_ctsare', 100000000),
            ('pl_ctnare', 100000000),
            ('pl_cblare', 100000000),
            ('pl_berths', 100000000),
            ('pl_airare', 100000000),
            ('pl_admare', 100000000),
            ('pl_achbrt', 100000000),
            ('pl_achare', 100000000),
            ('pl_cranes', 100000000),
            ('li_rapids', 100000000),
            ('li_marcul', 100000000),
            ('li_flodoc', 100000000),
            ('li_lndmrk', 100000000),
            ('li_feryrt', 100000000),
            ('li_cblsub', 100000000),
            ('li_coalne', 100000000),
            ('li_depare', 100000000),
            ('li_depcnt', 100000000),
            ('li_lndare', 100000000),
            ('li_rivers', 100000000),
            ('li_slcons', 100000000),
            ('li_pipohd', 100000000),
            ('li_magvar', 100000000),
            ('li_rectrc', 100000000),
            ('li_pipsol', 100000000),
            ('li_bridge', 100000000),
            ('li_convyr', 100000000),
            ('li_sbdare', 100000000),
            ('li_lndelv', 100000000),
            ('li_slotop', 100000000),
            ('li_damcon', 100000000),
            ('li_obstrn', 100000000),
            ('li_radlne', 100000000),
            ('li_railwy', 100000000),
            ('li_roadwy', 100000000),
            ('li_causwy', 100000000),
            ('li_watfal', 100000000),
            ('li_cblohd', 100000000),
            ('li_tssbnd', 100000000),
            ('li_wattur', 100000000),
            ('li_morfac', 100000000),
            ('li_gatcon', 100000000),
            ('li_tselne', 100000000),
            ('li_dykcon', 100000000),
            ('li_vegatn', 100000000),
            ('li_runway', 100000000),
            ('li_fnclne', 100000000),
            ('li_rdocal', 100000000),
            ('li_stslne', 100000000),
            ('li_navlne', 100000000),
            ('li_oilbar', 100000000),
            ('li_canals', 100000000),
            ('li_forstc', 100000000),
            ('li_dwrtcl', 100000000),
            ('li_tidewy', 100000000),
            ('li_tunnel', 100000000),
            ('li_berths', 100000000),
            ('li_rcrtcl', 100000000),
            ('li_fshfac', 100000000),
            ('li_ponton', 100000000),
            ('pt_roadwy', 100000000),
            ('pt_buaare', 100000000),
            ('pt_dmpgrd', 100000000),
            ('pt_boycar', 100000000),
            ('pt_boysaw', 100000000),
            ('pt_achare', 100000000),
            ('pt_boyinb', 100000000),
            ('pt_pilbop', 100000000),
            ('pt_ofsplf', 100000000),
            ('pt_boyspp', 100000000),
            ('pt_fogsig', 100000000),
            ('pt_lndare', 100000000),
            ('pt_lndelv', 100000000),
            ('pt_splare', 100000000),
            ('pt_lndrgn', 100000000),
            ('pt_lights', 100000000),
            ('pt_siltnk', 100000000),
            ('pt_wattur', 100000000),
            ('pt_icnare', 100000000),
            ('pt_mipare', 100000000),
            ('pt_ts_tis', 100000000),
            ('pt_obstrn', 100000000),
            ('pt_pilpnt', 100000000),
            ('pt_rtpbcn', 100000000),
            ('pt_sbdare', 100000000),
            ('pt_retrfl', 100000000),
            ('pt_soundg', 100000000),
            ('pt_topmar', 100000000),
            ('pt_hulkes', 100000000),
            ('pt_logpon', 100000000),
            ('pt_wedklp', 100000000),
            ('pt_wrecks', 100000000),
            ('pt_newobj', 100000000),
            ('pt_uwtroc', 100000000),
            ('pt_airare', 100000000),
            ('pt_curent', 100000000),
            ('pt_lndmrk', 100000000),
            ('pt_locmag', 100000000),
            ('pt_seaare', 100000000),
            ('pt_litflt', 100000000),
            ('pt_boyisd', 100000000),
            ('pt_ctnare', 100000000),
            ('pt_fshfac', 100000000),
            ('pt_hrbfac', 100000000),
            ('pt_morfac', 100000000),
            ('pt_vegatn', 100000000),
            ('pt_pipsol', 100000000),
            ('pt_gatcon', 100000000),
            ('pt_smcfac', 100000000),
            ('pt_buisgl', 100000000),
            ('pt_bcnlat', 100000000),
            ('pt_bcnspp', 100000000),
            ('pt_ctrpnt', 100000000),
            ('pt_forstc', 100000000),
            ('pt_rdosta', 100000000),
            ('pt_damcon', 100000000),
            ('pt_litves', 100000000),
            ('pt_bcncar', 100000000),
            ('pt_runway', 100000000),
            ('pt_pylons', 100000000),
            ('pt_cgusta', 100000000),
            ('pt_rctlpt', 100000000),
            ('pt_ts_feb', 100000000),
            ('pt_bridge', 100000000),
            ('pt_spring', 100000000),
            ('pt_achbrt', 100000000),
            ('pt_rdocal', 100000000),
            ('pt_boylat', 100000000),
            ('pt_ts_pad', 100000000),
            ('pt_ts_prh', 100000000),
            ('pt_dismar', 100000000),
            ('pt_slogrd', 100000000),
            ('pt_sndwav', 100000000),
            ('pt_prdare', 100000000),
            ('pt_sistaw', 100000000),
            ('pt_radsta', 100000000),
            ('pt_cranes', 100000000),
            ('pt_marcul', 100000000),
            ('pt_berths', 100000000),
            ('pt_rscsta', 100000000),
            ('pt_bcnsaw', 100000000),
            ('pt_sistat', 100000000),
            ('pt_slcons', 100000000),
            ('pt_bcnisd', 100000000),
            ('pt_daymar', 100000000),
            ('pt_watfal', 100000000)
        ]

    def load_layers(self, selected_tables):
        from qgis.core import (
            QgsProject, QgsVectorLayer, QgsDataSourceUri, QgsMapLayerStyle
        )

        mode = self.settings.storage_mode()
        projet = QgsProject.instance()

        # =====================================================
        # === MODE POSTGIS ====================================
        # =====================================================
        if mode == "postgis":

            # Vérifie la connexion PostGIS
            try:
                db = self.db_manager.get_connection()
                db.close()
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Impossible de récupérer la connexion PostGIS: {e}",
                    "S57Manager"
                )
                return

            # Paramètres PG (exactement comme dans l'import)
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
            schema = "enc"

            for nom_table in selected_tables:
                uri = QgsDataSourceUri()
                uri.setConnection(host, port, dbname, user, pwd)
                uri.setDataSource(schema, nom_table, "wkb_geometry", "", "ogc_fid")

                couche = QgsVectorLayer(uri.uri(False), nom_table, "postgres")

                if not couche.isValid():
                    QgsMessageLog.logMessage(
                        f"Impossible de charger la couche : {nom_table}",
                        "S57Manager")
                    continue

                # Charger le style portant le même nom que la couche
                styles = couche.listStylesInDatabase()
                namedStylesToId = dict(zip(styles[2], styles[1]))
                style_id = namedStylesToId.get(nom_table)

                if style_id:
                    qml_content, _ = couche.getStyleFromDatabase(style_id)
                    lStyle = QgsMapLayerStyle(qml_content)
                    lStyle.writeToLayer(couche)

                projet.addMapLayer(couche)

            self.iface.mapCanvas().refreshAllLayers()
            return

        # =====================================================
        # === MODE GEOPACKAGE ==================================
        # =====================================================
        if mode == "gpkg":
            gpkg_path = self.settings.gpkg_path()+"/ENC.gpkg"

            if not gpkg_path:
                QgsMessageLog.logMessage(
                    self.tr("Aucun GeoPackage ENC.gpkg n'est défini dans les options."),
                    "S57Manager"
                )
                return
            # Liste des couches à ignorer
            ignored_layers = ["pl_exezne", "DSID", "C_AGGR", "C_ASSO"]  # à adapter selon tes besoins
            for nom_table in selected_tables:
                if nom_table in ignored_layers:
                    continue
                # Syntaxe QGIS : path|layername=xxx
                uri = f"{gpkg_path}|layername={nom_table}"

                couche = QgsVectorLayer(uri, nom_table, "ogr")

                if not couche.isValid():
                    QgsMessageLog.logMessage(
                        f"Impossible de charger la couche GPKG : {nom_table}",
                        "S57Manager"
                    )
                    continue

                # ---- Charger le style depuis layer_styles ----
                styles = couche.listStylesInDatabase()
                namedStylesToId = dict(zip(styles[2], styles[1]))

                style_id = namedStylesToId.get(nom_table)
                if style_id:
                    qml, _ = couche.getStyleFromDatabase(style_id)
                    layer_style = QgsMapLayerStyle(qml)
                    layer_style.writeToLayer(couche)

                projet.addMapLayer(couche)

            self.iface.mapCanvas().refreshAllLayers()
            return


        