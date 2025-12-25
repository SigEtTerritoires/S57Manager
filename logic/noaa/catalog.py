# logic/noaa/catalog.py

import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from qgis.utils import iface
from qgis.core import QgsRectangle
import re
CATALOG_URL = "https://charts.noaa.gov/ENCs/ENCProdCat_19115.xml"

NS = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}



# ----------------------------------------------------------------------
# Modèle cellule ENC NOAA
# ----------------------------------------------------------------------

@dataclass
class NoaaEncPanel:
    panel_id: str
    bbox: QgsRectangle


@dataclass
class NoaaEncCell:
    id: str
    name: str
    scale: int
    purpose: int
    zip_url: str
    bbox: QgsRectangle  # bbox globale (union)

# ----------------------------------------------------------------------
# Catalogue NOAA ISO 19139
# ----------------------------------------------------------------------

class NoaaEncCatalog:
    def __init__(self):
        self._cells: list[NoaaEncCell] = []
    def tr(self, message):
        return QCoreApplication.translate("S57Settings", message)
# ------------------------------------------------------------------
    def load(self):
        try:
            with urllib.request.urlopen(CATALOG_URL) as response:
                xml_data = response.read()
        except Exception as e:
            raise RuntimeError(self.tr("Impossible de charger le catalogue NOAA : {}").format(str(e)))

        root = ET.fromstring(xml_data)
        self._cells.clear()

        for md in root.findall(".//gmd:MD_Metadata", NS):


            title = md.find(".//gmd:title/gco:CharacterString", NS)
            if title is None:
                continue
            cell_id = title.text.strip()

            alt = md.find(".//gmd:alternateTitle/gco:CharacterString", NS)
            name = alt.text.strip() if alt is not None else None

            url = md.find(".//gmd:onLine//gmd:URL", NS)
            zip_url = url.text.strip() if url is not None else None

            scale_el = md.find(".//gmd:MD_RepresentativeFraction//gco:Integer", NS)
            scale = int(scale_el.text) if scale_el is not None else None

            bbox = self.extract_bbox(md)
            purpose = self.extract_purpose(cell_id)

            self._cells.append(
                NoaaEncCell(
                    id=cell_id,
                    name=name,
                    zip_url=zip_url,
                    scale=scale,
                    purpose=purpose,
                    bbox=bbox
                )
            )

        if not self._cells:
            raise RuntimeError(self.tr("Catalogue NOAA chargé mais aucune cellule détectée"))


    # ------------------------------------------------------------------
    def cells(self):
        return self._cells


    # ------------------------------------------------------------------
    def get_cell(self, cell_id: str):
        for cell in self._cells:
            if cell.id == cell_id:
                return cell
        return None
    def extract_purpose(self,cell_id: str) -> int | None:
        m = re.search(r'\D(\d)\D', cell_id)
        purpose = int(m.group(1)) if m else None
        return purpose
        


    def extract_bbox(self,md_element) -> QgsRectangle | None:
        positions = md_element.findall(".//{*}pos")
        if not positions:
            return None

        lats = []
        lons = []

        for pos in positions:
            lat, lon = map(float, pos.text.split())
            lats.append(lat)
            lons.append(lon)

        return QgsRectangle(
            min(lons),
            min(lats),
            max(lons),
            max(lats),
        )

