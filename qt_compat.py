# qt_compat.py
# ---------------------------------------------------------
# Compatibilité PyQt5 ↔ PyQt6 pour QGIS
# ---------------------------------------------------------

from qgis.PyQt.QtCore import Qt, QCoreApplication

# --- Orientation ---
if hasattr(Qt, "Orientation"):  # Qt6
    Orientation = Qt.Orientation
else:  # Qt5
    class _Orientation:
        Horizontal = Qt.Horizontal
        Vertical = Qt.Vertical
    Orientation = _Orientation

# --- Alignement ---
if hasattr(Qt, "AlignmentFlag"):  # Qt6
    AlignmentFlag = Qt.AlignmentFlag
else:
    class _Alignment:
        AlignLeft = Qt.AlignLeft
        AlignRight = Qt.AlignRight
        AlignTop = Qt.AlignTop
        AlignBottom = Qt.AlignBottom
        AlignCenter = Qt.AlignCenter
        AlignHCenter = Qt.AlignHCenter
        AlignVCenter = Qt.AlignVCenter
    AlignmentFlag = _Alignment

# --- États de cases ---
if hasattr(Qt, "CheckState"):  # Qt6
    CheckState = Qt.CheckState
else:
    class _CheckState:
        Checked = Qt.Checked
        Unchecked = Qt.Unchecked
        PartiallyChecked = Qt.PartiallyChecked
    CheckState = _CheckState

# --- Formes du curseur ---
if hasattr(Qt, "CursorShape"):  # Qt6
    CursorShape = Qt.CursorShape
else:
    class _CursorShape:
        ArrowCursor = Qt.ArrowCursor
        PointingHandCursor = Qt.PointingHandCursor
        WaitCursor = Qt.WaitCursor
    CursorShape = _CursorShape

# --- Fenêtres/boîtes de dialogue ---
if hasattr(Qt, "WindowType"):
    WindowType = Qt.WindowType
else:
    class _WindowType:
        Dialog = Qt.Dialog
        Window = Qt.Window
    WindowType = _WindowType

# --- Méthode d'internationalisation ---
def tr(text):
    """Compatible PyQt5 / PyQt6 translation function."""
    return QCoreApplication.translate("S57Manager", text)
