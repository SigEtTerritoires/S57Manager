import time
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar,
    QTextEdit, QPushButton, QHBoxLayout, QFileDialog
)
from PyQt5.QtWidgets import QApplication


class WorkerSignals:
    """Structure simple pour gérer les signaux du thread."""
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    step = pyqtSignal(str)
    finished = pyqtSignal()
    cancelled = pyqtSignal()


class ProgressDialog(QDialog):
    """Fenêtre de suivi pour import S57."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Import S57 – en cours…"))
        self.setMinimumWidth(520)
        self.cancelled = False
        self.start_time = time.time()

        layout = QVBoxLayout(self)

        # Étape en cours
        self.step_label = QLabel(self.tr("Préparation…"))
        self.step_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        layout.addWidget(self.step_label)

        # Barre de progression
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # Temps estimé
        self.eta_label = QLabel(self.tr("Temps estimé : --"))
        eta_font = self.eta_label.font()
        eta_font.setItalic(True)
        self.eta_label.setFont(eta_font)
        layout.addWidget(self.eta_label)

        # Journal texte
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        # Boutons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton(self.tr("Annuler"))
        self.btn_save = QPushButton(self.tr("Exporter le journal"))
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        # Connexions
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_save.clicked.connect(self._save_log)

    # --- Signaux utilisés par le thread ---

    def append_log(self, text):
        self.log.append(text)
        self.log.ensureCursorVisible()

    def set_step(self, text):
        self.step_label.setText(text)

    def set_progress(self, value):
        self.progress.setValue(value)
        self._update_eta(value)

    # --- Fonctions internes ---

    def _on_cancel(self):
        self.cancelled = True
        self.append_log(self.tr("⛔ Annulation demandée…"))

    def _save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Exporter le journal"), "", "*.txt")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log.toPlainText())

    def _update_eta(self, progress):
        if progress <= 1:
            return
        elapsed = time.time() - self.start_time
        remaining = elapsed * (100 - progress) / progress
        self.eta_label.setText(self.tr("Temps estimé restant : {} sec").format(int(remaining)))
