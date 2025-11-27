from qgis.PyQt.QtWidgets import QDialog 
from .ui_outils_dialog import Ui_Ui_OutilsDialog as Ui_OutilsDialog

class OutilsDialog(QDialog, Ui_OutilsDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.buttonBox.rejected.connect(self.reject)
