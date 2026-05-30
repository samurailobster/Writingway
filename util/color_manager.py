import os
import json
from PyQt5.QtWidgets import QColorDialog, QMessageBox
from PyQt5.QtGui import QColor, QTextCharFormat
from PyQt5.QtCore import Qt

class ColorManager:
    """
    Manages text color and background selection, application, and persistence.
    """
    def __init__(self, settings_path):
        self.settings_file = settings_path
        self.default_fg = QColor(Qt.GlobalColor.black)
        self.default_bg = QColor(Qt.GlobalColor.transparent)
        self.load_colors()

    def load_colors(self):
        """
        Load saved colors from JSON settings file.
        """
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    fg = data.get('last_fg')
                    bg = data.get('last_bg')
                    if fg:
                        self.default_fg = QColor(*fg)
                    if bg:
                        self.default_bg = QColor(*bg)
            except Exception as e:
                print(f"Error loading colors: {e}")

    def save_colors(self, fg: QColor, bg: QColor):
        """
        Save selected colors to JSON settings file.
        """
        data = {
            'last_fg': (fg.red(), fg.green(), fg.blue(), fg.alpha()),
            'last_bg': (bg.red(), bg.green(), bg.blue(), bg.alpha())
        }
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving colors: {e}")

    def choose_color(self, parent=None):
        """
        Open a color dialog initialized with last used colors.
        Returns tuple (fg, bg) QColor or None if canceled.
        """
        dialog = QColorDialog(parent)
        dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        dialog.setCurrentColor(self.default_fg)
        if dialog.exec_() != QColorDialog.Accepted:
            return None
        fg = dialog.selectedColor()

        bg = QColorDialog.getColor(self.default_bg, parent, "Background Color", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if not bg.isValid():
            return None

        self.save_colors(fg, bg)
        return fg, bg

    def apply_color_to_selection(self, editor, fg: QColor, bg: QColor):
        """
        Apply given foreground and background colors to current text selection.
        """
        cur = editor.textCursor()
        if not cur.hasSelection():
            QMessageBox.information(editor, "Color", "Please select some text first.")
            return
        fmt = QTextCharFormat()
        fmt.setForeground(fg)
        fmt.setBackground(bg)
        cur.beginEditBlock()
        cur.mergeCharFormat(fmt)
        cur.endEditBlock()

    def apply_fg_to_selection(self, editor, fg: QColor):
        cur = editor.textCursor()
        if not cur.hasSelection():
            QMessageBox.information(editor, "Text Color", "Please select some text first.")
            return
        fmt = QTextCharFormat()
        fmt.setForeground(fg)
        cur.beginEditBlock()
        cur.mergeCharFormat(fmt)
        cur.endEditBlock()