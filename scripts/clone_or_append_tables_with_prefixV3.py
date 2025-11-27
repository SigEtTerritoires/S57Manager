from osgeo import ogr
from osgeo import osr

def clone_or_append_tables_with_prefix():
    input_geopackages = ["c:/testgpkgV3/pointsENC.gpkg", "c:/testgpkgV3/linesENC.gpkg", "c:/testgpkgV3/polysENC.gpkg"]
    prefixes = ["pt_", "li_", "pl_"]
    
    for i in range(len(input_geopackages)):
        input_gpkg = ogr.Open(input_geopackages[i], 0)

        if input_gpkg is not None:
            output_gpkg = ogr.Open("c:/testgpkgV3/ENC.gpkg", 1)
            prefix = prefixes[i]

            if output_gpkg is not None:
                num_tables = input_gpkg.GetLayerCount()

                for j in range(num_tables):
                    input_table = input_gpkg.GetLayerByIndex(j)
                    output_table_name = f"{prefix}{input_table.GetName()}"
                    input_table_name = input_table.GetName()

                    output_table = output_gpkg.GetLayerByName(output_table_name)
                    if output_table is None:
                        # Créer une nouvelle couche de destination si elle n'existe pas
                        output_srs = osr.SpatialReference()
                        output_srs.ImportFromEPSG(4326)  # Définir EPSG 4326
                        output_table = output_gpkg.CreateLayer(output_table_name, geom_type=input_table.GetGeomType(), options=["OVERWRITE=YES"], srs=output_srs)

                        # Copier les définitions des champs de la table source
                        input_layer = input_gpkg.GetLayerByName(input_table_name)
                        input_layer_defn = input_layer.GetLayerDefn()
                        for k in range(input_layer_defn.GetFieldCount()):
                            field_defn = input_layer_defn.GetFieldDefn(k)
                            output_table.CreateField(field_defn)

                    # Copier les entités de la table source vers la table de destination
                    for feature in input_table:
                        output_feature = ogr.Feature(output_table.GetLayerDefn())
                        output_feature.SetGeometry(feature.GetGeometryRef())

                        # Copier les valeurs des champs
                        for field_index in range(feature.GetFieldCount()):
                            output_feature.SetField(field_index, feature.GetField(field_index))

                        output_table.CreateFeature(output_feature)
                        output_feature = None  # Libérer la mémoire

                    # Créer l'index spatial
                    output_gpkg.ExecuteSQL(f"CREATE SPATIAL INDEX ON '{output_table_name}'")                     
                    # Définir le SRC 4326
                    output_gpkg.ExecuteSQL(f"UPDATE gpkg_geometry_columns SET srs_id = (SELECT srs_id FROM gpkg_spatial_ref_sys WHERE srs_id = 4326) WHERE table_name = '{output_table_name}'")

                    print(f"Contenu ajouté de {input_geopackages[i]}.{input_table.GetName()} vers ENC.gpkg.{output_table_name}")

                input_gpkg = None
                output_gpkg = None
            else:
                print(f"Impossible d'ouvrir le GeoPackage {output_geopackage} en mode écriture.")
        else:
            print(f"Impossible d'ouvrir le GeoPackage {input_geopackages[i]} en mode lecture.")

clone_or_append_tables_with_prefix()
