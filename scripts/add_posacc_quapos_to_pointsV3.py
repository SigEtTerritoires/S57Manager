import sys
from osgeo import ogr

def add_posacc_quapos_to_pointsV3 (geopackage_path):
    # Chemin vers le GeoPackage

    # Liste des tables à exclure
    tables_exclues = ["IsolatedNode", "ConnectedNode","DSID","C_AGGR","C_ASSO","layer_styles"]  

    # Ouvrir le GeoPackage
    driver = ogr.GetDriverByName("GPKG")
    geopackage = driver.Open(geopackage_path, 1)

    # Récupérer la table IsolatedNode
    isolated_node_table = geopackage.GetLayerByName("IsolatedNode")

    # Parcourir toutes les tables du GeoPackage
    for i in range(geopackage.GetLayerCount()):
        table = geopackage.GetLayerByIndex(i)
        table_name = table.GetName()
        
        # Vérifier si la table n'est pas dans la liste des tables exclues et si elle n'est pas IsolatedNode
        if table_name not in tables_exclues and table_name != "IsolatedNode" :
            print(f"Traitement table {table_name}")
            # Récupérer les noms des champs des tables
            table_defn = table.GetLayerDefn()
            field_names = [table_defn.GetFieldDefn(j).GetName() for j in range(table_defn.GetFieldCount())]
            
            # Index des champs rcid et enc_chart dans la table IsolatedNode
            isolated_node_defn = isolated_node_table.GetLayerDefn()
            rcid_index_isolated_node = isolated_node_defn.GetFieldIndex("RCID")
            enc_chart_index_isolated_node = isolated_node_defn.GetFieldIndex("enc_chart")
            
            # Parcourir les enregistrements de la table
            table.ResetReading()
            for feature in table:
                rcid_full = feature.GetField("NAME_RCID")
                rcid = rcid_full.split(":")[1]
                rcid = rcid[:-1]
                enc_chart = feature.GetField("enc_chart")
                
                # Rechercher le rcid et enc_chart dans la table IsolatedNode
                isolated_node_table.SetAttributeFilter("RCID = '{}' AND enc_chart = '{}'".format(rcid, enc_chart))
                isolated_node_feature = isolated_node_table.GetNextFeature()
                
                if isolated_node_feature:
                    # Mettre à jour les attributs POSACC et QUAPOS de la table en cours avec ceux d'IsolatedNode
                    posacc_index = table_defn.GetFieldIndex("POSACC")
                    quapos_index = table_defn.GetFieldIndex("QUAPOS")
                    if posacc_index >= 0:
                        posacc = isolated_node_feature.GetField("POSACC")
                        feature.SetField(posacc_index, posacc)
                    if quapos_index >= 0:
                        quapos = isolated_node_feature.GetField("QUAPOS")
                        feature.SetField(quapos_index, quapos)
                        
                    
                    # Sauvegarder les modifications
                    table.SetFeature(feature)

    # Fermer le GeoPackage
    geopackage = None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py geopackage_path ")
        sys.exit(1)
    
    geopackage_path = sys.argv[1]
    

    add_posacc_quapos_to_pointsV3 (geopackage_path)
