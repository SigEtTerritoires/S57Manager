from qgis.PyQt.QtCore import QSettings

class S57Settings:
    KEY_STORAGE = 's57manager/storage_mode'
    KEY_GPKG_PATH = 's57manager/gpkg_path'
    KEY_PG_CONN = 's57manager/pg_connection'

    def set_storage_mode(self, mode: str):
        QSettings().setValue(self.KEY_STORAGE, mode)

    def storage_mode(self) -> str:
        return QSettings().value(self.KEY_STORAGE, 'gpkg')

    def set_gpkg_path(self, path: str):
        QSettings().setValue(self.KEY_GPKG_PATH, path)

    def gpkg_path(self) -> str:
        return QSettings().value(self.KEY_GPKG_PATH, '')

    def set_postgis_conn(self, conn: str):
        QSettings().setValue(self.KEY_PG_CONN, conn)

    def postgis_conn(self) -> str:
        return QSettings().value(self.KEY_PG_CONN, '')
