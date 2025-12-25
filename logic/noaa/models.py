# logic/noaa/models.py
# ---------------------------------------------------------
# Modèles de données – NOAA ENC
# ---------------------------------------------------------

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class ENCDescriptor:
    """
    Décrit une cellule ENC NOAA (S-57).

    Cette classe est volontairement :
    - indépendante de QGIS
    - indépendante du stockage (ZIP, dossier, DB)
    - sérialisable (JSON, pickle, etc.)
    """

    # --- Identification ---
    cell_name: str                 # ex: US5FL15M
    title: str                     # Nom lisible

    # --- Usage / échelle ---
    purpose: int                   # 1..6 (Overview → Berthing)
    scale: int                     # échelle nominale

    # --- Versionnement ---
    edition: int                   # numéro d’édition
    update: int                    # dernier update appliqué
    status: str                    # active | deprecated | obsolete

    # --- Couverture spatiale ---
    coverage: Optional[Dict] = None  # bbox, footprint GeoJSON, etc.

    # --- Téléchargement ---
    base_url: str = ""
    update_urls: List[str] = field(default_factory=list)

    # -----------------------------------------------------
    # Méthodes utilitaires
    # -----------------------------------------------------

    def is_active(self) -> bool:
        """Retourne True si la cellule est active."""
        return self.status.lower() == "active"

    def has_updates(self) -> bool:
        """Indique si des mises à jour incrémentales existent."""
        return len(self.update_urls) > 0

    def display_name(self) -> str:
        """
        Nom lisible pour affichage UI.
        Exemple : 'US5FL15M – Approach (1:50 000)'
        """
        return f"{self.cell_name} – {self.title} (1:{self.scale:,})"

    def to_dict(self) -> dict:
        """Sérialisation simple (JSON-friendly)."""
        return {
            "cell_name": self.cell_name,
            "title": self.title,
            "purpose": self.purpose,
            "scale": self.scale,
            "edition": self.edition,
            "update": self.update,
            "status": self.status,
            "coverage": self.coverage,
            "base_url": self.base_url,
            "update_urls": self.update_urls,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ENCDescriptor":
        """Reconstruction depuis un dictionnaire."""
        return cls(
            cell_name=data["cell_name"],
            title=data.get("title", ""),
            purpose=int(data.get("purpose", 0)),
            scale=int(data.get("scale", 0)),
            edition=int(data.get("edition", 0)),
            update=int(data.get("update", 0)),
            status=data.get("status", "active"),
            coverage=data.get("coverage"),
            base_url=data.get("base_url", ""),
            update_urls=data.get("update_urls", []),
        )
