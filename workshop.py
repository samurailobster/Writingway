import json
import os
import re
import glob
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QMessageBox, QInputDialog, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QApplication, QSplitter, QWidget, QScrollArea, QLabel
)
from PyQt5.QtCore import Qt
from prompts import load_project_options, get_workshop_prompts
from llm_integration import send_prompt_to_llm
from conversation_history_manager import estimate_conversation_tokens, summarize_conversation, prune_conversation_history

TOKEN_LIMIT = 2000

def parse_compendium_references(message):
    filename = "compendium.json"
    refs = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                compendium = json.load(f)
            if isinstance(compendium, dict):
                names = list(compendium.keys())
            elif isinstance(compendium, list):
                names = [entry.get("name", "") for entry in compendium]
            else:
                names = []
            for name in names:
                if name and re.search(r'\b' + re.escape(name) + r'\b', message, re.IGNORECASE):
                    refs.append(name)
        except Exception as e:
            print("Error parsing compendium references:", e)
    return refs

def get_compendium_data():
    filename = "compendium.json"
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading compendium data:", e)
    return {"categories": {}}

def get_compendium_text(category, entry):
    data = get_compendium_data()
    categories = data.get("categories", {})
    return categories.get(category, {}).get(entry, f"[No content for {entry} in category {category}]")

class ExtendedContextDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Context")
        self.resize(500, 400)
        self.selected_contexts = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderHidden(True)
        self.build_project_tree()
        self.project_tree.itemChanged.connect(self.handle_item_changed)
        self.tabs.addTab(self.project_tree, "Project Structure")
        
        self.compendium_tree = QTreeWidget()
        self.compendium_tree.setHeaderHidden(True)
        self.build_compendium_tree()
        self.compendium_tree.itemChanged.connect(self.handle_item_changed)
        self.tabs.addTab(self.compendium_tree, "Compendium")
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.on_ok)
        layout.addWidget(ok_button)
    
    def build_project_tree(self):
        self.project_tree.clear()
        structure = None
        if self.parent() is not None and hasattr(self.parent(), "structure"):
            structure = self.parent().structure
        if structure is None:
            structure = {"acts": []}
        for act in structure.get("acts", []):
            act_item = QTreeWidgetItem(self.project_tree, [act.get("name", "Unnamed Act")])
            act_item.setFlags(act_item.flags() & ~Qt.ItemIsUserCheckable)
            for chapter in act.get("chapters", []):
                chap_item = QTreeWidgetItem(act_item, [chapter.get("name", "Unnamed Chapter")])
                chap_item.setFlags(chap_item.flags() | Qt.ItemIsUserCheckable)
                chap_item.setCheckState(0, Qt.Unchecked)
                for scene in chapter.get("scenes", []):
                    scene_item = QTreeWidgetItem(chap_item, [scene.get("name", "Unnamed Scene")])
                    scene_item.setFlags(scene_item.flags() | Qt.ItemIsUserCheckable)
                    scene_item.setCheckState(0, Qt.Unchecked)
        self.project_tree.expandAll()
    
    def build_compendium_tree(self):
        self.compendium_tree.clear()
        data = get_compendium_data()
        categories = data.get("categories", {})
        for cat, entries in categories.items():
            cat_item = QTreeWidgetItem(self.compendium_tree, [cat])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsUserCheckable)
            for entry in sorted(entries.keys()):
                entry_item = QTreeWidgetItem(cat_item, [entry])
                entry_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                entry_item.setCheckState(0, Qt.Unchecked)
        self.compendium_tree.expandAll()
    
    def handle_item_changed(self, item, column):
        if item.flags() & Qt.ItemIsUserCheckable:
            state = item.checkState(column)
            for i in range(item.childCount()):
                child = item.child(i)
                if child.flags() & Qt.ItemIsUserCheckable:
                    child.setCheckState(0, state)
            self.update_parent(item)
    
    def update_parent(self, item):
        parent = item.parent()
        if not parent or not (parent.flags() & Qt.ItemIsUserCheckable):
            return
        checked = 0
        partial = False
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.checkState(0) == Qt.Checked:
                checked += 1
            elif child.checkState(0) == Qt.PartiallyChecked:
                partial = True
        if checked == parent.childCount():
            parent.setCheckState(0, Qt.Checked)
        elif checked > 0 or partial:
            parent.setCheckState(0, Qt.PartiallyChecked)
        else:
            parent.setCheckState(0, Qt.Unchecked)
        self.update_parent(parent)
    
    def get_selected_contexts(self):
        selections = []
        def traverse(item):
            if item.childCount() == 0 and item.checkState(0) == Qt.Checked:
                selections.append(item.text(0))
            else:
                for i in range(item.childCount()):
                    traverse(item.child(i))
        root = self.project_tree.invisibleRootItem()
        for i in range(root.childCount()):
            traverse(root.child(i))
        for i in range(self.compendium_tree.topLevelItemCount()):
            cat_item = self.compendium_tree.topLevelItem(i)
            category = cat_item.text(0)
            for j in range(cat_item.childCount()):
                entry_item = cat_item.child(j)
                if entry_item.checkState(0) == Qt.Checked:
                    selections.append(f"{category}: {entry_item.text(0)}")
        return selections
    
    def on_ok(self):
        self.selected_contexts = self.get_selected_contexts()
        if not self.selected_contexts:
            QMessageBox.warning(self, "No Selection", "Please select at least one scene or compendium entry.")
            return
        self.accept()

class WorkshopWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workshop")
        self.resize(800, 600)
        if self.parent() is not None and hasattr(self.parent(), "project_name"):
            self.project_name = self.parent().project_name
        else:
            self.project_name = "DefaultProject"
        if self.parent() is not None and hasattr(self.parent(), "structure"):
            self.structure = self.parent().structure
        else:
            self.structure = {"acts": []}
        self.workshop_prompt_config = None
        self.conversation_history = []
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        main_layout.addWidget(self.chat_log)
        
        splitter = QSplitter(Qt.Horizontal)
        
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Type your message here...")
        left_layout.addWidget(self.chat_input)
        
        buttons_layout = QHBoxLayout()
        self.prompt_button = QPushButton("Prompt")
        self.prompt_button.clicked.connect(self.select_workshop_prompt)
        buttons_layout.addWidget(self.prompt_button)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        buttons_layout.addWidget(self.send_button)
        
        self.context_button = QPushButton("Context")
        self.context_button.setCheckable(True)
        self.context_button.clicked.connect(self.toggle_context_panel)
        buttons_layout.addWidget(self.context_button)
        
        self.model_label = QLabel("Model: [None]")
        buttons_layout.addWidget(self.model_label)
        
        buttons_layout.addStretch()
        left_layout.addLayout(buttons_layout)
        
        splitter.addWidget(left_container)
        
        self.context_panel = QWidget()
        context_layout = QVBoxLayout(self.context_panel)
        self.context_tabs = QTabWidget()
        self.extended_context_dialog = ExtendedContextDialog(self)
        
        scroll1 = QScrollArea()
        scroll1.setWidget(self.extended_context_dialog.project_tree)
        scroll1.setWidgetResizable(True)
        self.context_tabs.addTab(scroll1, "Project Structure")
        
        scroll2 = QScrollArea()
        scroll2.setWidget(self.extended_context_dialog.compendium_tree)
        scroll2.setWidgetResizable(True)
        self.context_tabs.addTab(scroll2, "Compendium")
        
        context_layout.addWidget(self.context_tabs)
        self.context_panel.setVisible(False)
        splitter.addWidget(self.context_panel)
        
        splitter.setSizes([500, 300])
        main_layout.addWidget(splitter)
    
    def toggle_context_panel(self):
        if self.context_panel.isVisible():
            self.context_panel.setVisible(False)
            self.context_button.setText("Context")
        else:
            self.context_panel.setVisible(True)
            self.context_button.setText("Hide")
    
    def select_workshop_prompt(self):
        prompts = get_workshop_prompts(self.project_name)
        if not prompts:
            QMessageBox.information(self, "Workshop Prompt", "No workshop prompts found.")
            return
        prompt_names = [p.get("name", "Unnamed") for p in prompts]
        item, ok = QInputDialog.getItem(self, "Select Workshop Prompt", "Choose a prompt:", prompt_names, 0, False)
        if ok and item:
            for p in prompts:
                if p.get("name", "") == item:
                    self.workshop_prompt_config = p
                    provider = p.get("provider", "Local")
                    model = p.get("model", "Local Model")
                    self.model_label.setText(f"Model: {provider}/{model}")
                    break
    
    def send_message(self):
        user_message = self.chat_input.toPlainText().strip()
        if not user_message:
            return
        
        augmented_message = user_message
        if self.context_panel.isVisible():
            contexts = self.extended_context_dialog.get_selected_contexts()
            if contexts:
                augmented_message += "\nContext:\n" + "\n".join(contexts)
        refs = parse_compendium_references(augmented_message)
        if refs:
            augmented_message += "\n[Compendium references: " + ", ".join(refs) + "]"
        
        self.chat_log.append("You: " + user_message)
        self.chat_input.clear()
        self.chat_log.append("LLM: Generating response...")
        QApplication.processEvents()
        
        conversation_payload = list(self.conversation_history)
        
        if not conversation_payload and self.workshop_prompt_config:
            conversation_payload.append({
                "role": "system",
                "content": self.workshop_prompt_config.get("text", "")
            })
        
        conversation_payload.append({"role": "user", "content": augmented_message})
        
        overrides = {}
        if self.workshop_prompt_config:
            overrides = {
                "provider": self.workshop_prompt_config.get("provider", "Local"),
                "model": self.workshop_prompt_config.get("model", "Local Model"),
                "max_tokens": self.workshop_prompt_config.get("max_tokens", 2000),
                "temperature": self.workshop_prompt_config.get("temperature", 1.0)
            }
        
        if estimate_conversation_tokens(conversation_payload) > TOKEN_LIMIT:
            summary = summarize_conversation(conversation_payload)
            conversation_payload = [conversation_payload[0], {"role": "system", "content": summary}]
            self.chat_log.append("LLM: [Conversation summarized to reduce token count.]")
        
        response = send_prompt_to_llm("", overrides=overrides, conversation_history=conversation_payload)
        
        self.chat_log.append("LLM: " + response)
        QApplication.processEvents()
        
        self.conversation_history = conversation_payload
        self.conversation_history.append({"role": "assistant", "content": response})
