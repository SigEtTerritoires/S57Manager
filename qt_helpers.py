# qt_helpers.py#

from qgis.PyQt import QtWidgets, QtCore, QtGui
__all__ = [
    "frame_shape",
    "frame_shadow",
    "size_policy",
    "dialog_button",
    "alignment",
    "font_weight",
]

# ---------

# QFrame

# ---------

def frame_shape(shape_name: str):

    """

    Retourne la valeur correcte d'une constante QFrame (Shape).

    Exemple : frame_shape("HLine"), frame_shape("VLine")

    """

    if hasattr(QtWidgets.QFrame, "Shape"):  # Qt6

        return getattr(QtWidgets.QFrame.Shape, shape_name)

    else:  # Qt5

        return getattr(QtWidgets.QFrame, shape_name)

def frame_shadow(shadow_name: str):

    """

    Retourne la valeur correcte d'une constante QFrame (Shadow).

    Exemple : frame_shadow("Sunken"), frame_shadow("Raised")

    """

    if hasattr(QtWidgets.QFrame, "Shadow"):  # Qt6

        return getattr(QtWidgets.QFrame.Shadow, shadow_name)

    else:

        return getattr(QtWidgets.QFrame, shadow_name)

# ---------

# QSizePolicy

# ---------

def size_policy(policy_name: str):

    """

    Retourne la valeur correcte d'une constante QSizePolicy.

    Exemple : size_policy("Expanding"), size_policy("Fixed")

    """

    if hasattr(QtWidgets.QSizePolicy, "Policy"):  # Qt6

        return getattr(QtWidgets.QSizePolicy.Policy, policy_name)

    else:

        return getattr(QtWidgets.QSizePolicy, policy_name)

# ---------

# QDialogButtonBox

# ---------

def dialog_button(button_name: str):

    """

    Retourne la valeur correcte pour un bouton standard de QDialogButtonBox.

    Exemple : dialog_button("Ok"), dialog_button("Cancel"), dialog_button("Apply")

    """

    if hasattr(QtWidgets.QDialogButtonBox, "StandardButton"):  # Qt6

        return getattr(QtWidgets.QDialogButtonBox.StandardButton, button_name)

    else:

        return getattr(QtWidgets.QDialogButtonBox, button_name)

# ---------

# Qt Alignment

# ---------

def alignment(align_name: str):

    """

    Retourne la valeur correcte pour les alignements Qt.

    Exemple : alignment("AlignLeft"), alignment("AlignCenter"), alignment("AlignRight")

    """

    if hasattr(QtCore, "AlignmentFlag"):  # Qt6

        return getattr(QtCore.AlignmentFlag, align_name)

    else:

        return getattr(QtCore, align_name)

# ---------

# QFont

# ---------

def font_weight(weight_name: str):

    """

    Retourne la valeur correcte d'un poids de police.

    Exemple : font_weight("Bold"), font_weight("Normal")

    """

    if hasattr(QtGui.QFont, "Weight"):  # Qt6

        return getattr(QtGui.QFont.Weight, weight_name)

    else:

        return getattr(QtGui.QFont, weight_name)
def dialog_button(button_name: str):
    try:
        if hasattr(QtWidgets.QDialogButtonBox, "StandardButton"):
            return getattr(QtWidgets.QDialogButtonBox.StandardButton, button_name)
        else:
            return getattr(QtWidgets.QDialogButtonBox, button_name)
    except AttributeError:
        raise ValueError(f"Unknown QDialogButtonBox button: {button_name}")
