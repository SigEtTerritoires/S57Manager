from pathlib import Path
import tempfile

from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import QThread, QCoreApplication,Qt

from ..logic.noaa.catalog import NoaaEncCatalog, NoaaEncCell
from ..logic.noaa.noaa_worker import NoaaWorker
from ..logic.noaa.updater import NoaaUpdater
from ..logic.display import S57Display
from qgis.core import QgsMessageLog
from qgis.PyQt.QtWidgets import (
        QVBoxLayout, QHBoxLayout, QGridLayout,
        QGroupBox, QCheckBox, QLabel, QPushButton,
        QSpinBox, QTableWidget, QTableWidgetItem,
        QTextEdit, QHeaderView,  QAbstractItemView
    )
from qgis.utils import iface

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle
)

class NoaaDialog(QtWidgets.QDialog):

    def __init__(
        self,
        parent=None,
        settings=None,
        db_manager=None,
    ):
        super().__init__(parent)
        self.iface = iface
        self.settings = settings
        self.db_manager = db_manager
        self.catalog = NoaaEncCatalog()
        self.updater = NoaaUpdater(log_callback=self.log_message)
        self.temp_dir = tempfile.mkdtemp(prefix="noaa_enc_")
        self.catalog_loaded = False
        # Layout principal
        main_layout = QVBoxLayout(self)

        # =================================================
        # 🔹 GROUPE : Filtres
        # =================================================
        filters_group = QGroupBox(self.tr("Filtres NOAA ENC"))
        filters_layout = QGridLayout()

        # --- Emprise & échelle canvas
        self.chk_extent = QCheckBox(self.tr("Limiter à l’emprise de la carte"))
        self.chk_canvas_scale = QCheckBox(self.tr("Adapter à l’échelle courante"))

        filters_layout.addWidget(self.chk_extent, 0, 0, 1, 2)
        filters_layout.addWidget(self.chk_canvas_scale, 1, 0, 1, 2)

        # --- Échelle ENC
        filters_layout.addWidget(QLabel(self.tr("Échelle ENC")), 2, 0)

        self.spin_scale_min = QSpinBox()
        self.spin_scale_min.setRange(1_000, 50_000_000)
        self.spin_scale_min.setValue(1_000)
        self.spin_scale_min.setPrefix("1:")

        self.spin_scale_max = QSpinBox()
        self.spin_scale_max.setRange(1_000, 50_000_000)
        self.spin_scale_max.setValue(10_000_000)
        self.spin_scale_max.setPrefix("1:")

        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Min"))
        scale_layout.addWidget(self.spin_scale_min)
        scale_layout.addWidget(QLabel("Max"))
        scale_layout.addWidget(self.spin_scale_max)

        filters_layout.addLayout(scale_layout, 2, 1)

        # --- Purpose
        filters_layout.addWidget(QLabel("Purpose"), 3, 0)

        purpose_layout = QGridLayout()

        self.chk_purpose = {}
        purposes = [
            (1,self.tr( "Overview")),
            (2,self.tr( "General")),
            (3, self.tr("Coastal")),
            (4,self.tr( "Approach")),
            (5,self.tr( "Harbour")),
            (6,self.tr( "Berthing")),
        ]

        for i, (pid, label) in enumerate(purposes):
            chk = QCheckBox(label)
            chk.setChecked(True)
            self.chk_purpose[pid] = chk
            purpose_layout.addWidget(chk, i // 3, i % 3)

        filters_layout.addLayout(purpose_layout, 3, 1)

        filters_group.setLayout(filters_layout)
        main_layout.addWidget(filters_group)

        # =================================================
        # 🔹 TABLE : Cellules NOAA
        # =================================================
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Cell ID", self.tr("Nom"), self.tr("Purpose"), self.tr("Échelle")])
        try:
            resize_mode = QHeaderView.ResizeMode.Stretch  # Qt6
        except AttributeError:
            resize_mode = QHeaderView.Stretch              # Qt5
        self.table.horizontalHeader().setSectionResizeMode(resize_mode)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        main_layout.addWidget(self.table)

        # =================================================
        # 🔹 LOG / PROGRESSION
        # =================================================
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(80)

        main_layout.addWidget(self.log_box)

        # =================================================
        # 🔹 BOUTONS
        # =================================================
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.btn_import = QPushButton(self.tr("Importer la cellule sélectionnée"))
        self.btn_close = QPushButton(self.tr("Fermer"))
        self.load_catalog_btn = QPushButton(self.tr("Télécharger le catalogue NOAA"))
        self.btn_close.clicked.connect(self.close)
        self.load_catalog_btn.clicked.connect(self.load_catalog)
        buttons_layout.addWidget(self.load_catalog_btn)
        buttons_layout.addWidget(self.btn_import)
        buttons_layout.addWidget(self.btn_close)
        self.chk_add_to_map = QCheckBox(
            self.tr("Charger la carte ENC après l’import")
        )
        self.chk_add_to_map.setChecked(True)
        main_layout.addWidget(self.chk_add_to_map)

        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)
        self.setWindowTitle(self.tr("NOAA ENC – Catalogue"))
        self.resize(900, 650)

        
        
        self.spin_scale_min.valueChanged.connect(self.refresh_cells)
        self.spin_scale_max.valueChanged.connect(self.refresh_cells)
        self.chk_extent.toggled.connect(self.refresh_cells)
        self.chk_canvas_scale.toggled.connect(self.refresh_cells)

        
        
        for chk in self.chk_purpose.values():
            chk.toggled.connect(self.refresh_cells)


        selected_purposes = [
            pid for pid, chk in self.chk_purpose.items() if chk.isChecked()
        ]

        scale_min = self.spin_scale_min.value()
        scale_max = self.spin_scale_max.value()

        use_extent = self.chk_extent.isChecked()
        use_canvas_scale = self.chk_canvas_scale.isChecked()
        self._connect_signals()

    def tr(self, message):
        return QCoreApplication.translate("S57Settings", message)
    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------



    def _connect_signals(self):
        self.btn_close.clicked.connect(self.close)
        self.btn_import.clicked.connect(self.import_selected_cell)

        self.chk_extent.stateChanged.connect(self.refresh_cells)
        self.chk_canvas_scale.stateChanged.connect(self.refresh_cells)
        self.spin_scale_min.valueChanged.connect(self.refresh_cells)
        self.spin_scale_max.valueChanged.connect(self.refresh_cells)

        for chk in self.chk_purpose.values():
            chk.stateChanged.connect(self.refresh_cells)


    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def load_catalog(self):
        self.log_message(self.tr("Chargement du catalogue NOAA…"))
        self.load_catalog_btn.setEnabled(False)

        try:
            self.catalog.load()
        except Exception as e:
            self.log_message(self.tr("❌ Erreur catalogue : {}").format(str(e)))
            self.load_catalog_btn.setEnabled(True)
            return

        self.catalog_loaded = True
        self.log_message(self.tr("✔ {} cellules chargées").format(len(self.catalog.cells())))

        # Premier affichage selon filtres par défaut
        self.refresh_cells()

        self.load_catalog_btn.setEnabled(True)


    def _on_selection_changed(self):
        self.btn_import.setEnabled(self.cell_list.currentItem() is not None)

    def import_selected_cell(self):

        # -----------------------------------
        # 1️⃣ Récupération de la ligne sélectionnée
        # -----------------------------------
        row = self.table.currentRow()
        if row < 0:
            self.log_message(self.tr("⚠ Aucune cellule sélectionnée"))
            return

        # -----------------------------------
        # 2️⃣ Récupération de l’objet NoaaEncCell
        # -----------------------------------
        cell = self.table.item(row, 0).data(QtCore.Qt.UserRole)

        if cell is None:
            self.log_message(self.tr("❌ Erreur interne : cellule invalide"))
            return

        # -----------------------------------
        # 3️⃣ Log DEBUG (optionnel mais utile)
        # -----------------------------------
        self.log_message(self.tr("Démarrage du traitement de la cellule {}").format(cell.id))
        self.log_message(f"DEBUG id = {cell.id}")
        self.log_message(f"DEBUG name = {cell.name}")
        self.log_message(f"DEBUG url = {cell.zip_url}")
        self.log_message(f"DEBUG scale = {cell.scale}")

        # -----------------------------------
        # 4️⃣ Désactivation bouton
        # -----------------------------------
        self.btn_import.setEnabled(False)

        # -----------------------------------
        # 5️⃣ Thread + Worker (inchangé)
        # -----------------------------------
        self.thread = QThread(self)
        self.worker = NoaaWorker(
            cell=cell,
            target_dir=self.temp_dir,
            settings=self.settings,
            db_manager=self.db_manager,
            target=self.settings.storage_mode(),
            overwrite=False,
        )

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.log_message)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    # ------------------------------------------------------------------
    # Callbacks worker
    # ------------------------------------------------------------------

    def _on_worker_finished(self, success: bool, message: str, cell_id: str):
        if success:
            self.log_message(self.tr("✔ {}").format(message))

            if self.chk_add_to_map.isChecked() and cell_id:
                self.log_message(self.tr("⏳ Patientez, chargement des couches dans le projet.."))
                self._load_enc_cell(cell_id)
                self.log_message(self.tr("✔ Traitement terminé"))

        else:
            self.log_message(self.tr("❌ {}").format(message))

        self.btn_import.setEnabled(True)


    # ------------------------------------------------------------------
    # Log helper
    # ------------------------------------------------------------------

    def log_message(self, message: str):
        self.log_box.append(message)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )



    def refresh_cells(self):

        if not self.catalog_loaded:
            return

        canvas = self.iface.mapCanvas()
        canvas_crs = canvas.mapSettings().destinationCrs()



        # ----------------------------
        # Récupération des filtres
        # ----------------------------
        use_extent = self.chk_extent.isChecked()
        use_canvas_scale = self.chk_canvas_scale.isChecked()

        scale_min = self.spin_scale_min.value()
        scale_max = self.spin_scale_max.value()

        if use_canvas_scale:
            canvas_scale = self.iface.mapCanvas().scale()
            scale_min = int(canvas_scale * 0.5)
            scale_max = int(canvas_scale * 2)
        crs_wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

        transform = None
        if use_extent and canvas_crs != crs_wgs84:
            transform = QgsCoordinateTransform(
                crs_wgs84,
                canvas_crs,
                QgsProject.instance()
            )
        canvas_rect = None
        if use_extent:
            canvas_rect = self.iface.mapCanvas().extent()

        selected_purposes = {
            pid for pid, chk in self.chk_purpose.items() if chk.isChecked()
        }

        # ----------------------------
        # Nettoyage table
        # ----------------------------
        self.table.clearContents()
        while (self.table.rowCount() > 0):
            {
                self.table.removeRow(0)
            }
        self.table.setRowCount(0)

        count = 0

        # ----------------------------
        # Boucle sur les cellules
        # ----------------------------
        for cell in self.catalog.cells():

            # filtres
            if cell.purpose not in selected_purposes:
                continue

            if not (scale_min <= cell.scale <= scale_max):
                continue

            if use_extent:
                if not cell.bbox:
                    continue
                
                bbox = cell.bbox

                # reprojection NOAA (EPSG:4326) → CRS du canvas
                if transform:
                    try:
                        bbox = transform.transformBoundingBox(bbox)
                    except Exception:
                        continue  # bbox invalide → on ignore la cellule

                
                if not canvas_rect.intersects(bbox):
                    continue            
                

            # ----------------------------
            # Ajout à la table
            # ----------------------------
            row = self.table.rowCount()
            self.table.insertRow(row)

            item_id = QTableWidgetItem(cell.id)
            item_id.setData(Qt.ItemDataRole.UserRole, cell)

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, QTableWidgetItem(cell.name))
            self.table.setItem(row, 2, QTableWidgetItem(str(cell.purpose)))
            self.table.setItem(row, 3, QTableWidgetItem(f"1:{cell.scale:,}"))

            count += 1

        self.log_message(self.tr("🔎 {} cellules affichées après filtrage").format(count))



    def _cell_extent(self, cell):
        minx, miny, maxx, maxy = cell.bbox
        return QgsRectangle(minx, miny, maxx, maxy)
    def _load_enc_cell(self, cell_id: str):
        display = S57Display(
            settings=self.settings,
            db_manager=self.db_manager,
            iface=self.iface,
        )
        display.load_enc_cell(cell_id)
