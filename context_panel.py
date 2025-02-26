import os
import json
import re
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt

# Assume get_compendium_text is imported from a shared module or defined elsewhere.
from workshop import get_compendium_text  # Use the function from workshop.py

class ContextPanel(QWidget):
    """
    A panel that lets the user choose extra context for the prose prompt.
    It contains a QTabWidget with two tabs:
      - Project: shows chapters and scenes from the project (only these levels are checkable).
      - Compendium: shows compendium entries organized by category.
    Selections persist until manually changed.
    """
    def __init__(self, project_structure, project_name, parent=None):
        super().__init__(parent)
        self.project_structure = project_structure  # reference to the project structure
        self.project_name = project_name
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: Project Structure
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderHidden(True)
        self.build_project_tree()
        self.project_tree.itemChanged.connect(self.propagate_check_state)
        self.tabs.addTab(self.project_tree, "Project")
        
        # Tab 2: Compendium
        self.compendium_tree = QTreeWidget()
        self.compendium_tree.setHeaderHidden(True)
        self.build_compendium_tree()
        self.compendium_tree.itemChanged.connect(self.propagate_check_state)
        self.tabs.addTab(self.compendium_tree, "Compendium")
    
    def build_project_tree(self):
        """Build a tree from the project structure showing only chapters and scenes."""
        self.project_tree.clear()
        for act in self.project_structure.get("acts", []):
            act_item = QTreeWidgetItem(self.project_tree, [act.get("name", "Unnamed Act")])
            act_item.setFlags(act_item.flags() & ~Qt.ItemIsUserCheckable)
            for chapter in act.get("chapters", []):
                chapter_item = QTreeWidgetItem(act_item, [chapter.get("name", "Unnamed Chapter")])
                chapter_item.setFlags(chapter_item.flags() | Qt.ItemIsUserCheckable)
                chapter_item.setCheckState(0, Qt.Unchecked)
                chapter_item.setData(0, Qt.UserRole, {"type": "chapter", "data": chapter})
                for scene in chapter.get("scenes", []):
                    scene_item = QTreeWidgetItem(chapter_item, [scene.get("name", "Unnamed Scene")])
                    scene_item.setFlags(scene_item.flags() | Qt.ItemIsUserCheckable)
                    scene_item.setCheckState(0, Qt.Unchecked)
                    scene_item.setData(0, Qt.UserRole, {"type": "scene", "data": scene})
        self.project_tree.expandAll()
    
    def build_compendium_tree(self):
        """Build a tree from the compendium data."""
        self.compendium_tree.clear()
        filename = "compendium.json"
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        categories = data.get("categories", {})
        for cat, entries in categories.items():
            cat_item = QTreeWidgetItem(self.compendium_tree, [cat])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsUserCheckable)
            for entry in sorted(entries.keys()):
                entry_item = QTreeWidgetItem(cat_item, [entry])
                entry_item.setFlags(entry_item.flags() | Qt.ItemIsUserCheckable)
                entry_item.setCheckState(0, Qt.Unchecked)
                entry_item.setData(0, Qt.UserRole, {"type": "compendium", "category": cat, "label": entry})
        self.compendium_tree.expandAll()
    
    def propagate_check_state(self, item, column):
        """Propagate check state changes to children and update parent items."""
        if item.childCount() > 0:
            state = item.checkState(column)
            for i in range(item.childCount()):
                child = item.child(i)
                if child.flags() & Qt.ItemIsUserCheckable:
                    child.setCheckState(0, state)
        self.update_parent_check_state(item)
    
    def update_parent_check_state(self, item):
        parent = item.parent()
        if not parent or not (parent.flags() & Qt.ItemIsUserCheckable):
            return
        checked = sum(1 for i in range(parent.childCount())
                      if parent.child(i).checkState(0) == Qt.Checked)
        if checked == parent.childCount():
            parent.setCheckState(0, Qt.Checked)
        elif checked > 0:
            parent.setCheckState(0, Qt.PartiallyChecked)
        else:
            parent.setCheckState(0, Qt.Unchecked)
        self.update_parent_check_state(parent)
    
    def get_selected_context_text(self):
        """Collect selected text from both tabs, formatted with headers."""
        texts = []
        root = self.project_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._traverse_project_item(root.child(i), texts)
        for i in range(self.compendium_tree.topLevelItemCount()):
            cat_item = self.compendium_tree.topLevelItem(i)
            category = cat_item.text(0)
            for j in range(cat_item.childCount()):
                entry_item = cat_item.child(j)
                if entry_item.checkState(0) == Qt.Checked:
                    text = get_compendium_text(category, entry_item.text(0))
                    texts.append(text)
        if texts:
            return "Additional Context:\n" + "\n\n".join(texts)
        return ""
    
    def _traverse_project_item(self, item, texts):
        data = item.data(0, Qt.UserRole)
        if item.childCount() == 0 and item.checkState(0) == Qt.Checked:
            if data:
                if data.get("type") == "chapter":
                    summary = data.get("data", {}).get("summary", "")
                    if summary:
                        texts.append(f"[Chapter Summary - {item.text(0)}]:\n{summary}")
                elif data.get("type") == "scene":
                    content = data.get("data", {}).get("content", "")
                    if content:
                        texts.append(f"[Scene Content - {item.text(0)}]:\n{content}")
        else:
            for i in range(item.childCount()):
                self._traverse_project_item(item.child(i), texts)
