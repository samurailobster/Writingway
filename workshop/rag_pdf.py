import sys
import os
import io
import logging
import json
import re
import math
import base64
import time
import datetime
from pathlib import Path
from typing import Any, List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from difflib import SequenceMatcher
from PIL import Image
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.messages.base import BaseMessage

import fitz
import pymupdf4llm
import tiktoken
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QTextOption, QKeySequence, QPixmap, QCursor, QTextDocument, QTextCursor, QImage
from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, 
                            QLineEdit, QPushButton, QTextEdit, QSpinBox, QPlainTextEdit, 
                            QLabel, QProgressBar, QScrollArea, QFileDialog, QMessageBox, 
                            QGridLayout, QSplitter, QComboBox, QDoubleSpinBox, QDialog,
                            QListWidgetItem, QMenuBar, QAction, QListWidget, QStatusBar,
                            QMenu, QInputDialog, QShortcut, QApplication, QCheckBox,
                            QSizePolicy, QStackedWidget)
from settings.llm_api_aggregator import WWApiAggregator
from util.find_dialog import FindDialog

from .rag_utils import SettingsManager, HistoryDialog, AppSettings
from .rag_smart_qa import SmartQAWidget
from .rag_manual_processing import ManualProcessingWidget
from .rag_visual_explorer import VisualExplorerWidget

logging.basicConfig(
    filename='pdf_rag_app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PdfRagApp')

class PdfRagApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF RAG Processor")
        self.resize(1000, 800)
        
        self.shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_find.activated.connect(self.open_find_dialog)
        self.find_dialog = None

        self.settings = SettingsManager.load_settings()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.history_dir = os.path.join(self.base_dir, "rag_history")
        os.makedirs(self.history_dir, exist_ok=True)
        self.history_file = os.path.join(self.history_dir, "rag_search_history.json")

        self.load_history()

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.qa_tab = SmartQAWidget(self)
        self.manual_tab = ManualProcessingWidget(self)
        self.vl_tab = VisualExplorerWidget(self)
        self.tabs.addTab(self.qa_tab, "Smart QA")
        self.tabs.addTab(self.manual_tab, "Manual Processing")
        self.tabs.addTab(self.vl_tab, "Visual Explorer")
        self.main_layout.addWidget(self.tabs)

        self.status_bar = QtWidgets.QStatusBar()
        self.main_layout.addWidget(self.status_bar)
        self.create_menu_bar()

        self.apply_loaded_settings()
        
        self.active_workers = 0
        self.busy_cursor = self.load_custom_cursor("assets/icons/clock.svg")
        
    def load_custom_cursor(self, path):
        pixmap = QPixmap(path)
        return QCursor(pixmap) if not pixmap.isNull() else QCursor(Qt.CursorShape.WaitCursor)

    def set_busy_cursor(self):
        self.active_workers += 1
        if self.active_workers == 1:
            QApplication.setOverrideCursor(self.busy_cursor)

    def restore_cursor(self):
        self.active_workers -= 1
        if self.active_workers <= 0:
            QApplication.restoreOverrideCursor()
            self.active_workers = 0

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.search_history = json.load(f)
            else:
                self.search_history = []
        except Exception as e:
            print("Error loading history:", e)
            self.search_history = []
            
    def update_history_entry(self, title: str, new_text: str):
        for i, (t, txt) in enumerate(self.search_history):
            if t == title:
                self.search_history[i] = (t, new_text)
                break
        self.save_history()

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.search_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error saving history:", e)

    def create_menu_bar(self):
        mb = QMenuBar(self)
        
        hm = mb.addMenu("History")
        show = QAction("Show History", self)
        show.triggered.connect(self.show_history)
        hm.addAction(show)
        clear = QAction("Clear History", self)
        clear.triggered.connect(self.clear_history)
        hm.addAction(clear)
        
        help_menu = mb.addMenu("Help")
        about_action = QAction("About PDF RAG Processor", self)
        about_action.triggered.connect(self.show_app_info)
        help_menu.addAction(about_action)

        self.layout().setMenuBar(mb)

    def show_app_info(self):
        html = """
        <html>
        <head>
            <style>
            </style>
        </head>
        <body>
            <h1>PDF RAG Processor</h1>
            <p>
                A desktop application for fast ingestion, indexing,
                and intelligent querying of PDF documents using
                Retrieval-Augmented Generation (RAG).
            </p>

            <h2>Key Features</h2>
            <ul>
                <li><span class="feature">Smart Q&A</span>: Ask natural-language questions and get context-aware answers.</li>
                <li><span class="feature">Manual Processing</span>: Preview, annotate, and correct text before indexing.</li>
                <li><span class="feature">Visual Analysis</span>: Process PDF pages and images with vision-enabled LLMs.</li>
                <li><span class="feature">Bulk PDF Ingestion</span>: Import PDFs and auto-extract text.</li>
                <li><span class="feature">History & Privacy</span>: Review or clear past queries anytime.</li>
                <li><span class="feature">Document Search</span>: Find text in documents with <span class="shortcut">Ctrl+F</span> shortcut.</li>
            </ul>

            <h2>Core Work Modes</h2>
            <ul>
                <li><span class="feature">Smart QA Mode</span>
                    <ul>
                        <li><b>Hybrid semantic + keyword search</b>: This mode combines the power of semantic similarity (understanding the *meaning* of your question) with traditional keyword matching.  The application first finds paragraphs that are semantically similar to your query, and then boosts the score of those paragraphs that also contain your keywords. This provides a balance between finding relevant information even if you don't use the exact wording from the document, and ensuring that important terms are considered.</li>
                        <li><b>Semantic Search Only</b>:  This mode relies solely on semantic similarity to find relevant paragraphs. It uses advanced language models to understand the meaning of your question and identify paragraphs with similar meanings, regardless of the specific keywords used. This is useful when you want to explore broader concepts or paraphrase your query.</li>
                        <li><b>Exact Keyword Matching</b>: This mode performs a simple search for exact keyword matches within the document text. It's fast and precise but may miss relevant information if your question uses different wording than what's in the document.  It is case-insensitive.</li>
                        <li>Adjustable similarity threshold: Control how closely the meaning of the query must match the document content to be considered a hit. Higher thresholds mean stricter matching, lower thresholds are more inclusive.</li>
                        <li>Dynamic context window: The amount of text surrounding each relevant paragraph that's sent to the LLM for generating an answer can be adjusted (Snippet, Full Paragraph, or with surrounding paragraphs).</li>
                    </ul>
                </li>
                <li><span class="feature">Manual Processing Mode</span>
                    <ul>
                        <li>Custom chunk sizes & page ranges:  Break down your PDF into smaller chunks of text to optimize processing and LLM performance. You can also specify which pages to include in the indexing process.</li>
                        <li>Individual prompt tuning: Customize the prompts sent to the LLM for each chunk of text, allowing you to tailor the responses based on the specific content of that chunk.  This is useful when different sections of your document require different instructions.</li>
                        <li>Batch LLM processing with progress bar: Process multiple chunks of text in a batch using an LLM, with a visual progress bar to track the status of each chunk.</li>
                    </ul>
                </li>
                <li><span class="feature">Visual Explorer Mode</span>
                    <ul>
                        <li>Multi-panel layout for visual document analysis: Analyze PDF pages and images side-by-side, allowing you to quickly identify key information.</li>
                        <li>Batch processing of PDF pages and images: Process multiple pages or images simultaneously using vision-enabled LLMs.</li>
                        <li>Adjustable resolution and JPEG quality settings: Optimize image processing costs by adjusting the resolution and compression level of the images.</li>
                        <li>Individual or shared prompts per item: Customize the prompts sent to the LLM for each page or image, allowing you to tailor the responses based on the specific content of that item.</li>
                        <li>Response history tracking and JSON exports: Keep track of your previous responses and export them in a structured JSON format for further analysis.</li>
                    </ul>
                </li>
            </ul>

            <h2>Usage Tips</h2>
            <ol>
                <li>Go to the <span class="feature">Smart QA</span> tab for fast queries.</li>
                <li>Use <span class="feature">Manual Processing</span> to refine extracted text.</li>
                <li>Clear your history under the <span class="feature">History</span> menu regularly.</li>
                <li>In <span class="feature">Visual Explorer</span>, use "Select All/Deselect All" for batch operations.</li>
                <li>Adjust image dimensions in Visual Explorer to optimize processing costs.</li>
                <li>Use individual prompts for different pages/images when needed.</li>
            </ol>

        </body>
        </html>
        """

        dialog = QDialog(self)
        dialog.setWindowTitle("About PDF RAG Processor")
        dialog.resize(600, 550)

        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)

        content = QLabel()
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setText(html)
        content.setWordWrap(True)
        content.setOpenExternalLinks(True)
        scroll.setWidget(content)

        layout = QVBoxLayout(dialog)
        layout.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("close-btn")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec_()

    def show_history(self):
        self.load_history()
        dlg = HistoryDialog(self, self.search_history)
        dlg.exec_()

    def clear_history(self):
        r = QMessageBox.question(self, "Clear History",
                                 "Clear all history?", 
                                 QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            for title, _ in self.search_history:
                file_path = os.path.join(self.history_dir, title)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        QMessageBox.warning(
                            self, 
                            "Error", 
                            f"Failed to delete file {title}: {str(e)}"
                        )
            
            self.search_history = []
            self.save_history()
            QMessageBox.information(self, "History Cleared", "All history files removed from disk.")

    def apply_loaded_settings(self):
        pass

    def open_find_dialog(self):
        if self.find_dialog is None:
            self.find_dialog = FindDialog(self.manual_tab.manual_markdown_editor, self)
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.search_field.setFocus()

    def closeEvent(self, event):
        self.settings.last_pdf_path_manual = self.manual_tab.manual_pdf_path_edit.text()
        self.settings.last_pdf_path_qa = self.qa_tab.qa_pdf_path_edit.text()
        self.settings.last_chunk_size = self.manual_tab.manual_chunk_spin.value()
        self.settings.default_prompt = self.manual_tab.manual_default_prompt_edit.toPlainText()
        SettingsManager.save_settings(self.settings)
        event.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    window = PdfRagApp()
    window.show()
    sys.exit(app.exec_())