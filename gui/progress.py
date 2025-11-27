from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QPlainTextEdit, QProgressBar, QPushButton, QHBoxLayout
)
from qgis.PyQt.QtCore import Qt

class ProgressWindow(QDialog):
    def __init__(self, parent=None, title="Importation ENC"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 400)
        self.cancelled = False

        layout = QVBoxLayout(self)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Annuler")
        self.btn_cancel.clicked.connect(self.on_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def log(self, msg):
        self.text.appendPlainText(msg)
        self.text.ensureCursorVisible()
        QApplication.processEvents()  # permet au dialogue de rester fluide

    def set_progress(self, value):
        self.progress.setValue(value)
        QApplication.processEvents()

    def on_cancel(self):
        self.cancelled = True
        self.log("⚠️ Import annulé par l'utilisateur.")
