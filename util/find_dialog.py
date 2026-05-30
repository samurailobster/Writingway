from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QGridLayout, 
                            QLineEdit, QPushButton, QMessageBox, QApplication, 
                            QTextEdit, QCheckBox, QLabel, QGroupBox)
from PyQt5.QtGui import QTextCursor, QColor, QTextDocument, QTextFormat
from PyQt5.QtCore import Qt

class FindDialog(QDialog):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Find")
        self.setModal(False)  # The dialog is non-modal
        self.lastSearch = ""  # Remember last search
        self.setMinimumWidth(350)  # Minimum width for the dialog window
        
        # Create layouts
        self.mainLayout = QVBoxLayout()
        self.searchLayout = QGridLayout()
        self.buttonLayout = QHBoxLayout()
        
        # Search widgets
        self.searchLabel = QLabel("Find:", self)
        self.search_field = QLineEdit(self)
        self.search_field.setPlaceholderText("Enter text to search...")
        self.search_field.returnPressed.connect(self.find_next)
        self.search_field.textChanged.connect(self.reset_results)
        
        # Search options
        self.optionsGroup = QGroupBox("Search Options")
        self.optionsLayout = QVBoxLayout()
        
        self.case_sensitive = QCheckBox("Match case", self)
        self.whole_word = QCheckBox("Whole words only", self)
        self.highlight_all = QCheckBox("Highlight all occurrences", self)
        self.highlight_all.toggled.connect(self.toggle_highlight_all)
        self.wrap_search = QCheckBox("Wrap around", self)
        self.wrap_search.setChecked(True)  # Enabled by default
        
        self.optionsLayout.addWidget(self.case_sensitive)
        self.optionsLayout.addWidget(self.whole_word)
        self.optionsLayout.addWidget(self.highlight_all)
        self.optionsLayout.addWidget(self.wrap_search)
        self.optionsGroup.setLayout(self.optionsLayout)
        
        # Buttons
        self.find_next_button = QPushButton("Find Next", self)
        self.find_next_button.clicked.connect(self.find_next)
        
        self.find_prev_button = QPushButton("Find Previous", self)
        self.find_prev_button.clicked.connect(self.find_prev)
        
        self.clear_search_button = QPushButton("Clear Search", self)
        self.clear_search_button.clicked.connect(self.clear_search)
        
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.close)
        
        # Add widgets to layouts
        self.searchLayout.addWidget(self.searchLabel, 0, 0)
        self.searchLayout.addWidget(self.search_field, 0, 1)
        
        self.buttonLayout.addWidget(self.find_next_button)
        self.buttonLayout.addWidget(self.find_prev_button)
        self.buttonLayout.addWidget(self.clear_search_button)
        self.buttonLayout.addWidget(self.close_button)
        
        # Results label
        self.resultsLabel = QLabel("No search performed", self)
        
        # Set main layout
        self.mainLayout.addLayout(self.searchLayout)
        self.mainLayout.addWidget(self.optionsGroup)
        self.mainLayout.addLayout(self.buttonLayout)
        self.mainLayout.addWidget(self.resultsLabel)
        self.setLayout(self.mainLayout)
        
        # Initialize state variables
        self.all_matches = []  # List of all found matches
        self.current_match_index = -1  # Index of current match
        self.search_results_count = 0  # Count of search results
    
    def reset_results(self):
        """Reset results when search text changes"""
        self.resultsLabel.setText("No search performed")
        
    def highlight_found_text(self, cursor=None):
        """Highlight the currently found text"""
        if cursor is None:
            cursor = self.editor.textCursor()
        
        extraSelections = []
        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        # Set highlighting (yellow background, black text)
        selection.format.setBackground(Qt.GlobalColor.yellow)
        selection.format.setForeground(Qt.GlobalColor.black)
        extraSelections.append(selection)
        self.editor.setExtraSelections(extraSelections)
        
        # Force immediate update of the view
        self.editor.viewport().update()
        QApplication.processEvents()
        
        # Update result status - we've found at least one result
        self.update_results_label(1)

    def highlight_all_occurrences(self, search_text):
        """Highlight all occurrences of the search text."""
        if not search_text:
            return
        
        self.all_matches = []
        extraSelections = []
        
        # Save the current cursor position
        current_cursor = self.editor.textCursor()
        saved_position = current_cursor.position()
        
        # Move to the beginning of the document
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cursor)
        
        # Set search options
        flags = QTextDocument.FindFlags()
        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_word.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        
        # Iteratively find all occurrences
        counter = 0
        while self.editor.find(search_text, flags):
            counter += 1
            match_cursor = self.editor.textCursor()
            self.all_matches.append(match_cursor)
            
            selection = QTextEdit.ExtraSelection()
            selection.cursor = match_cursor
            
            # Different colors for different occurrences
            bg_color = QColor(255, 255, 0, 100)
            selection.format.setBackground(bg_color)
            selection.format.setForeground(Qt.GlobalColor.black)
            extraSelections.append(selection)
        
        # Restore cursor position
        cursor = self.editor.textCursor()
        cursor.setPosition(saved_position)
        self.editor.setTextCursor(cursor)
        
        # Set highlighting
        self.editor.setExtraSelections(extraSelections)
        
        # Update result status
        self.update_results_label(counter)
    
    def update_results_label(self, count):
        """Update the results count label"""
        self.search_results_count = count
        if count == 0:
            self.resultsLabel.setText("No results found")
        elif count == 1:
            self.resultsLabel.setText("1 result found")
        else:
            self.resultsLabel.setText(f"{count} results found")
    
    def toggle_highlight_all(self, checked):
        """Toggle highlighting of all occurrences."""
        search_text = self.search_field.text()
        if checked and search_text:
            self.highlight_all_occurrences(search_text)
        else:
            # Clear all highlights
            self.editor.setExtraSelections([])
    
    def count_occurrences(self, search_text):
        """Count all occurrences of the search text without changing selection"""
        if not search_text:
            return 0
            
        # Save the current cursor position and selection
        current_cursor = self.editor.textCursor()
        saved_position = current_cursor.position()
        had_selection = current_cursor.hasSelection()
        selection_start = current_cursor.selectionStart()
        selection_end = current_cursor.selectionEnd()
        
        # Move to the beginning of the document
        temp_cursor = QTextCursor(self.editor.document())
        temp_cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # Set search options
        flags = QTextDocument.FindFlags()
        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_word.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
            
        # Count occurrences
        count = 0
        while not temp_cursor.isNull() and not temp_cursor.atEnd():
            temp_cursor = self.editor.document().find(search_text, temp_cursor, flags)
            if not temp_cursor.isNull():
                count += 1
                
        # Restore original cursor position and selection
        restore_cursor = QTextCursor(self.editor.document())
        restore_cursor.setPosition(saved_position)
        if had_selection:
            restore_cursor.setPosition(selection_start)
            restore_cursor.setPosition(selection_end, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(restore_cursor)
        
        return count
    
    def find_next(self):
        """Find the next occurrence of text."""
        search_text = self.search_field.text()
        if not search_text:
            return
        
        # Remember search text
        self.lastSearch = search_text
        
        # Set search flags
        flags = QTextDocument.FindFlags()
        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_word.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        
        # First search from current position
        found = self.editor.find(search_text, flags)
        
        if found:
            # Update found text highlight and results
            self.highlight_found_text()
            # Count total occurrences without changing selection
            total_count = self.count_occurrences(search_text)
            self.update_results_label(total_count)
        else:
            # If not found from current position and wrap is enabled
            if self.wrap_search.isChecked():
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.editor.setTextCursor(cursor)
                
                if self.editor.find(search_text, flags):
                    self.highlight_found_text()
                    total_count = self.count_occurrences(search_text)
                    self.update_results_label(total_count)
                    QMessageBox.information(self, "Find", "Search wrapped to beginning of document.")
                else:
                    self.update_results_label(0)
                    QMessageBox.information(self, "Find", "No results found.")
            else:
                total_count = self.count_occurrences(search_text)
                if total_count > 0:
                    QMessageBox.information(self, "Find", "Reached the end of document.")
                else:
                    self.update_results_label(0)
                    QMessageBox.information(self, "Find", "No results found.")
    
    def find_prev(self):
        """Find the previous occurrence of text."""
        search_text = self.search_field.text()
        if not search_text:
            return
        
        # Remember search text
        self.lastSearch = search_text
        
        # Set search flags
        flags = QTextDocument.FindFlags()
        flags |= QTextDocument.FindFlag.FindBackward  # Search backward
        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_word.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        
        # First search from current position backwards
        found = self.editor.find(search_text, flags)
        
        if found:
            # Update found text highlight and results
            self.highlight_found_text()
            # Count total occurrences without changing selection
            total_count = self.count_occurrences(search_text)
            self.update_results_label(total_count)
        else:
            # If not found from current position and wrap is enabled
            if self.wrap_search.isChecked():
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.editor.setTextCursor(cursor)
                
                if self.editor.find(search_text, flags):
                    self.highlight_found_text()
                    total_count = self.count_occurrences(search_text)
                    self.update_results_label(total_count)
                    QMessageBox.information(self, "Find", "Search wrapped to end of document.")
                else:
                    self.update_results_label(0)
                    QMessageBox.information(self, "Find", "No results found.")
            else:
                total_count = self.count_occurrences(search_text)
                if total_count > 0:
                    QMessageBox.information(self, "Find", "Reached the beginning of document.")
                else:
                    self.update_results_label(0)
                    QMessageBox.information(self, "Find", "No results found.")
    
    def clear_search(self):
        """Clear search field and highlights"""
        self.search_field.clear()
        self.editor.setExtraSelections([])
        self.resultsLabel.setText("No search performed")
        self.all_matches = []
        self.current_match_index = -1
        
        # Focus the search field
        self.search_field.setFocus()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Clear highlights when dialog is closed
        self.editor.setExtraSelections([])
        event.accept()


# For testing and demonstration
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # Sample text editor
    editor = QTextEdit()
    editor.setText("This is a sample text for searching.\n"
                   "You can search for the word 'text' or 'searching'.\n"
                   "The program offers options to search forward and backward.\n"
                   "text text text - these are sample repetitions.\n"
                   "You can also search with case sensitivity.")
    
    # Create search dialog
    find_dialog = FindDialog(editor)
    
    # Show both windows
    editor.show()
    find_dialog.show()
    
    sys.exit(app.exec_())