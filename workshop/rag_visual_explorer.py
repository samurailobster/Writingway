import datetime
import io
import json
import os
import time

import fitz
from PIL import Image
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .rag_utils import LlmClient


class ProcessingThread(QThread):
    progress_updated = pyqtSignal(int, str)
    task_completed = pyqtSignal(int, str)
    all_completed = pyqtSignal()

    def __init__(self, parent, tasks):
        super().__init__(parent)
        self.parent = parent
        self.tasks = tasks

    def run(self):
        total_tasks = len(self.tasks)

        for i, task in enumerate(self.tasks):
            if self.parent.processing_cancelled:
                self.progress_updated.emit(100, "Cancelled")
                break

            progress = int((i / total_tasks) * 100)
            self.progress_updated.emit(progress, f"Processing {i+1}/{total_tasks}: {task['item']['name']}")

            try:
                idx = task['index']
                item = task['item']
                prompt = task['prompt']

                img_bytes = self.prepare_image(item)

                response, err = LlmClient.send_prompt_with_image(prompt, img_bytes)

                if err:
                    response = f"Error: {err}"

                self.task_completed.emit(idx, response)

            except Exception as e:
                self.task_completed.emit(task['index'], f"Error: {e!s}")

            time.sleep(0.1)

        if not self.parent.processing_cancelled:
            self.progress_updated.emit(100, "Completed")
        self.all_completed.emit()

    def prepare_image(self, item):
        """
        Prepare image or PDF page for sending to LLM based on selected format and settings.
        """
        max_width = self.parent.sb_max_width.value()
        max_height = self.parent.sb_max_height.value()

        pil_img = None

        if item['type'] == 'pdf_page':
            # Render PDF page at 300 DPI to a PIL Image
            page = item['doc'][item['page_num']]
            pix = page.get_pixmap(dpi=300)
            pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        elif item['type'] == 'image':
            pil_img = Image.open(item['path'])
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')

        original_width, original_height = pil_img.size
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height
        scale_ratio = min(width_ratio, height_ratio)

        if scale_ratio < 1.0:
            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)
            pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)

        buf = io.BytesIO()
        selected_format = self.parent.cb_format.currentText()
        if selected_format == "JPEG":
            quality = self.parent.sb_jpeg_quality.value()
            pil_img.save(buf, format="JPEG", quality=quality)
        else:  # PNG
            compression = self.parent.sb_png_compression.value()
            pil_img.save(buf, format="PNG", compress_level=compression)

        return buf.getvalue()

class VisualExplorerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.init_vl_tab()

    def init_vl_tab(self):
        main_layout = QHBoxLayout(self)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        file_group = QGroupBox("File Selection")
        h_file = QHBoxLayout(file_group)
        h_file.addWidget(QLabel("File:"))
        self.le_file_path = QLineEdit()
        self.le_file_path.setReadOnly(True)
        h_file.addWidget(self.le_file_path)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self.on_vl_browse)
        h_file.addWidget(btn_browse)
        left_layout.addWidget(file_group)

        settings_group = QGroupBox("Image Settings")
        settings_layout = QGridLayout(settings_group)
        settings_layout.addWidget(QLabel("Max Width (px):"), 0, 0)
        self.sb_max_width = QtWidgets.QSpinBox()
        self.sb_max_width.setRange(256, 2048)
        self.sb_max_width.setValue(768)
        self.sb_max_width.setSingleStep(64)
        settings_layout.addWidget(self.sb_max_width, 0, 1)
        settings_layout.addWidget(QLabel("Max Height (px):"), 1, 0)
        self.sb_max_height = QtWidgets.QSpinBox()
        self.sb_max_height.setRange(256, 2048)
        self.sb_max_height.setValue(1366)
        self.sb_max_height.setSingleStep(64)
        settings_layout.addWidget(self.sb_max_height, 1, 1)

        settings_layout.addWidget(QLabel("Format:"), 2, 0)
        self.cb_format = QtWidgets.QComboBox()
        self.cb_format.addItems(["JPEG", "PNG"])
        self.cb_format.currentIndexChanged.connect(self.vl_format_changed)
        settings_layout.addWidget(self.cb_format, 2, 1)

        self.lbl_jpeg_quality_label = QLabel("JPEG Quality:")
        settings_layout.addWidget(self.lbl_jpeg_quality_label, 3, 0)
        self.sb_jpeg_quality = QtWidgets.QSpinBox()
        self.sb_jpeg_quality.setRange(10, 95)
        self.sb_jpeg_quality.setValue(75)
        self.sb_jpeg_quality.setSingleStep(5)
        settings_layout.addWidget(self.sb_jpeg_quality, 3, 1)

        self.lbl_png_compression_label = QLabel("PNG Compression (0–9):")
        settings_layout.addWidget(self.lbl_png_compression_label, 4, 0)
        self.sb_png_compression = QtWidgets.QSpinBox()
        self.sb_png_compression.setRange(0, 9)
        self.sb_png_compression.setValue(6)
        self.sb_png_compression.setSingleStep(1)
        settings_layout.addWidget(self.sb_png_compression, 4, 1)

        # Initial visibility: JPEG controls shown, PNG controls hidden
        self.lbl_png_compression_label.setVisible(False)
        self.sb_png_compression.setVisible(False)

        settings_layout.addWidget(QLabel("Show Preview:"), 5, 0)
        self.cb_show_preview = QCheckBox()
        self.cb_show_preview.setChecked(True)
        self.cb_show_preview.stateChanged.connect(self.toggle_preview_panel)
        settings_layout.addWidget(self.cb_show_preview, 5, 1)
        left_layout.addWidget(settings_group)

        check_group = QGroupBox("Selection Controls")
        check_layout = QHBoxLayout(check_group)
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all_items)
        check_layout.addWidget(self.btn_select_all)
        self.btn_select_none = QPushButton("Deselect All")
        self.btn_select_none.clicked.connect(self.deselect_all_items)
        check_layout.addWidget(self.btn_select_none)
        left_layout.addWidget(check_group)

        items_group = QGroupBox("Items")
        items_layout = QVBoxLayout(items_group)
        self.list_items = QListWidget()
        self.list_items.setSelectionMode(QListWidget.SingleSelection)
        self.list_items.currentRowChanged.connect(self.on_item_selected)
        items_layout.addWidget(self.list_items)
        self.btn_save_images = QPushButton("Save Selected Images…")
        self.btn_save_images.clicked.connect(self.save_selected_images)
        items_layout.addWidget(self.btn_save_images)
        left_layout.addWidget(items_group, stretch=1)

        self.main_splitter.addWidget(left_panel)

        self.middle_panel = QWidget()
        middle_layout = QVBoxLayout(self.middle_panel)
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        preview_container = QWidget()
        preview_container_layout = QVBoxLayout(preview_container)
        self.lbl_preview = QLabel("No item selected")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_container_layout.addWidget(self.lbl_preview)
        preview_container_layout.addStretch()
        scroll_area.setWidget(preview_container)
        preview_layout.addWidget(scroll_area)
        middle_layout.addWidget(preview_group)

        self.main_splitter.addWidget(self.middle_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        prompt_group = QGroupBox("Prompt Settings")
        prompt_layout = QVBoxLayout(prompt_group)

        prompt_header = QHBoxLayout()
        prompt_header.addWidget(QLabel("Default Prompt:"))
        self.cb_individual_prompts = QCheckBox("Use Individual Prompts")
        self.cb_individual_prompts.setChecked(False)
        self.cb_individual_prompts.stateChanged.connect(self.vl_toggle_individual_prompts)
        prompt_header.addWidget(self.cb_individual_prompts)

        self.btn_copy_to_all = QPushButton("Copy to All from Page 1")
        self.btn_copy_to_all.clicked.connect(self.copy_prompt_to_all)
        self.btn_copy_to_all.setVisible(False)
        prompt_header.addWidget(self.btn_copy_to_all)

        prompt_layout.addLayout(prompt_header)

        self.prompt_stack = QStackedWidget()
        self.te_default_prompt = QPlainTextEdit()
        self.te_default_prompt.setPlaceholderText("Enter default prompt for all selected images…")
        self.prompt_stack.addWidget(self.te_default_prompt)
        self.individual_prompts_widget = QWidget()
        individual_layout = QVBoxLayout(self.individual_prompts_widget)
        self.prompt_scroll_area = QScrollArea()
        self.prompt_scroll_area.setWidgetResizable(True)
        self.prompt_scroll_area.setMinimumHeight(300)
        self.prompt_container = QWidget()
        self.prompt_container_layout = QVBoxLayout(self.prompt_container)
        self.prompt_scroll_area.setWidget(self.prompt_container)
        individual_layout.addWidget(self.prompt_scroll_area)
        self.prompt_stack.addWidget(self.individual_prompts_widget)

        prompt_layout.addWidget(self.prompt_stack)

        btn_layout = QHBoxLayout()
        self.btn_run_all = QPushButton("Process Selected")
        self.btn_run_all.clicked.connect(self.process_selected_items)
        btn_layout.addWidget(self.btn_run_all)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_processing)
        self.btn_cancel.setEnabled(False)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Results")
        self.btn_save.clicked.connect(self.save_vl_results)
        self.btn_save.setEnabled(False)
        btn_layout.addWidget(self.btn_save)

        prompt_layout.addLayout(btn_layout)
        right_layout.addWidget(prompt_group)

        progress_group = QGroupBox("Progress")
        self.progress_group = progress_group
        progress_layout = QVBoxLayout(progress_group)
        self.vl_progress_bar = QProgressBar()
        self.vl_progress_bar.setRange(0, 100)
        self.vl_progress_bar.setValue(0)
        progress_layout.addWidget(self.vl_progress_bar)
        self.lbl_progress_status = QLabel("Ready")
        progress_layout.addWidget(self.lbl_progress_status)
        right_layout.addWidget(progress_group)
        progress_group.setVisible(False)

        response_group = QGroupBox("LLM Responses")
        self.response_group = response_group
        response_layout = QVBoxLayout(response_group)
        self.te_vl_responses = QTextEdit()
        self.te_vl_responses.setReadOnly(True)
        response_layout.addWidget(self.te_vl_responses)
        right_layout.addWidget(response_group, stretch=1)
        response_group.setVisible(False)

        self.main_splitter.addWidget(right_panel)

        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setStretchFactor(2, 1)

        main_layout.addWidget(self.main_splitter)

        self.vl_items = []
        self.vl_doc = None
        self.vl_prompts = {}
        self.vl_responses = {}
        self.processing_cancelled = False
        self.processing_thread = None

    def vl_format_changed(self, index):
        """
        Toggle visibility of JPEG quality and PNG compression controls based on the selected format.
        """
        selected_format = self.cb_format.currentText()
        if selected_format == "JPEG":
            self.lbl_jpeg_quality_label.setVisible(True)
            self.sb_jpeg_quality.setVisible(True)
            self.lbl_png_compression_label.setVisible(False)
            self.sb_png_compression.setVisible(False)
        else:  # PNG selected
            self.lbl_jpeg_quality_label.setVisible(False)
            self.sb_jpeg_quality.setVisible(False)
            self.lbl_png_compression_label.setVisible(True)
            self.sb_png_compression.setVisible(True)

    def select_all_items(self):
        for i in range(self.list_items.count()):
            item = self.list_items.item(i)
            item.setCheckState(Qt.CheckState.Checked)
        if self.cb_individual_prompts.isChecked():
            self.update_individual_prompts()

    def deselect_all_items(self):
        for i in range(self.list_items.count()):
            item = self.list_items.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        if self.cb_individual_prompts.isChecked():
            self.update_individual_prompts()

    def vl_toggle_individual_prompts(self, state):
        if state == Qt.CheckState.Checked:
            self.prompt_stack.setCurrentIndex(1)
            self.btn_copy_to_all.setVisible(True)
            default_txt = self.te_default_prompt.toPlainText().strip()
            if default_txt:
                for idx in range(len(self.vl_items)):
                    self.vl_prompts.setdefault(idx, default_txt)
            self.update_individual_prompts()
        else:
            self.prompt_stack.setCurrentIndex(0)
            self.btn_copy_to_all.setVisible(False)
            for prompt in self.vl_prompts.values():
                if prompt.strip():
                    self.te_default_prompt.setPlainText(prompt)
                    break

    def update_individual_prompts(self):
        self.clear_individual_prompts()
        selected_indices = self.get_selected_indices()

        if not selected_indices:
            label = QLabel("No items selected. Select items from the list.")
            self.prompt_container_layout.addWidget(label)
            return

        for idx in selected_indices:
            item = self.vl_items[idx]
            name = item['name']

            group = QGroupBox(name)
            group_layout = QVBoxLayout(group)

            prompt_edit = QPlainTextEdit()
            prompt_edit.setPlaceholderText(f"Enter prompt for {name}...")
            if idx in self.vl_prompts:
                prompt_edit.setPlainText(self.vl_prompts[idx])
            else:
                prompt_edit.setPlainText(self.te_default_prompt.toPlainText())

            prompt_edit.setObjectName(f"prompt_{idx}")
            prompt_edit.textChanged.connect(lambda idx=idx, edit=prompt_edit: self.save_individual_prompt(idx, edit))
            group_layout.addWidget(prompt_edit)

            if self.vl_responses.get(idx):
                response_label = QLabel("Response:")
                group_layout.addWidget(response_label)
                response_text = QTextEdit()
                response_text.setReadOnly(True)
                response_text.setPlainText(self.vl_responses[idx])
                response_text.setMaximumHeight(150)
                group_layout.addWidget(response_text)

            self.prompt_container_layout.addWidget(group)

        self.prompt_container_layout.addStretch()

    def update_progress(self, value, status):
        self.vl_progress_bar.setValue(value)
        self.lbl_progress_status.setText(status)

    def on_task_completed(self, index, response):
        self.vl_responses[index] = response
        if not self.response_group.isVisible():
            self.response_group.setVisible(True)

        current_text = self.te_vl_responses.toPlainText()
        item_name = self.vl_items[index]['name']

        if current_text:
            current_text += "\n\n"

        self.te_vl_responses.setPlainText(
            current_text +
            f"--- {item_name} ---\n" +
            response
        )

        self.te_vl_responses.verticalScrollBar().setValue(
            self.te_vl_responses.verticalScrollBar().maximum()
        )

    def on_all_tasks_completed(self):
        self.progress_group.setVisible(False)
        QtWidgets.QApplication.restoreOverrideCursor()
        self.btn_run_all.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_save.setEnabled(len(self.vl_responses) > 0)
        total_processed = len(self.vl_responses)
        self.lbl_progress_status.setText(f"Completed {total_processed} items")

    def cancel_processing(self):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_cancelled = True
            self.lbl_progress_status.setText("Cancelling...")
            self.btn_cancel.setEnabled(False)
            QtWidgets.QApplication.restoreOverrideCursor()

    def clear_individual_prompts(self):
        while self.prompt_container_layout.count():
            item = self.prompt_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def save_individual_prompt(self, index, edit):
        self.vl_prompts[index] = edit.toPlainText()

    def copy_prompt_to_all(self):
        selected_indices = self.get_selected_indices()
        if not selected_indices:
            return

        first_prompt = None
        for idx in selected_indices:
            prompt_edit = self.prompt_container.findChild(QPlainTextEdit, f"prompt_{idx}")
            if prompt_edit:
                first_prompt = prompt_edit.toPlainText()
                break

        if not first_prompt:
            return

        for idx in selected_indices:
            prompt_edit = self.prompt_container.findChild(QPlainTextEdit, f"prompt_{idx}")
            if prompt_edit:
                prompt_edit.setPlainText(first_prompt)
                self.vl_prompts[idx] = first_prompt

    def get_selected_indices(self):
        selected = []
        for i in range(self.list_items.count()):
            if self.list_items.item(i).checkState() == Qt.CheckState.Checked:
                selected.append(i)
        return selected

    def process_selected_items(self):
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtGui.QPixmap("assets/icons/clock.svg")))

        selected_indices = self.get_selected_indices()
        if not selected_indices:
            QtWidgets.QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "No Selection", "Please select at least one item first.")
            return

        default_prompt = self.te_default_prompt.toPlainText().strip()
        if not self.cb_individual_prompts.isChecked() and not default_prompt:
            QtWidgets.QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "No Prompt", "Enter a prompt for the selected items.")
            return

        if self.cb_individual_prompts.isChecked():
            missing_prompts = []
            for idx in selected_indices:
                if idx not in self.vl_prompts or not self.vl_prompts[idx].strip():
                    missing_prompts.append(self.vl_items[idx]['name'])
            if missing_prompts:
                QtWidgets.QApplication.restoreOverrideCursor()
                QMessageBox.warning(
                    self,
                    "Missing Prompts",
                    "Please enter prompts for all selected items:\n- " + "\n- ".join(missing_prompts)
                )
                return

        self.progress_group.setVisible(True)

        tasks = []
        for idx in selected_indices:
            item = self.vl_items[idx]
            prompt = (self.vl_prompts.get(idx, default_prompt)
                      if self.cb_individual_prompts.isChecked()
                      else default_prompt)
            tasks.append({'index': idx, 'item': item, 'prompt': prompt})

        for idx in selected_indices:
            self.vl_responses.pop(idx, None)
        self.te_vl_responses.clear()
        self.vl_progress_bar.setValue(0)
        self.lbl_progress_status.setText("Starting...")

        self.btn_run_all.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.processing_cancelled = False

        self.processing_thread = ProcessingThread(self, tasks)
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.task_completed.connect(self.on_task_completed)
        self.processing_thread.all_completed.connect(self.on_all_tasks_completed)
        self.processing_thread.start()

    def toggle_preview_panel(self, state):
        if state == Qt.CheckState.Checked:
            self.middle_panel.show()
        else:
            self.middle_panel.hide()

    def on_vl_browse(self):
        image_formats = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)"
        pdf_format = "PDF Files (*.pdf)"
        all_formats = f"{pdf_format};;{image_formats};;All Files (*.*)"

        paths, selected_filter = QFileDialog.getOpenFileNames(
            self, "Open Files", "", all_formats
        )

        if not paths:
            return

        self.list_items.clear()
        self.vl_items = []
        self.vl_prompts = {}
        self.vl_responses = {}

        if hasattr(self, 'vl_doc') and self.vl_doc is not None:
            self.vl_doc.close()
            self.vl_doc = None

        for path in paths:
            file_ext = os.path.splitext(path)[1].lower()

            if file_ext == '.pdf':
                pdf_doc = fitz.open(path)
                self.vl_doc = pdf_doc

                for i in range(pdf_doc.page_count):
                    item_name = f"{os.path.basename(path)} - Page {i+1}"
                    item = QListWidgetItem(item_name)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    self.list_items.addItem(item)
                    self.vl_items.append({
                        'type': 'pdf_page',
                        'pdf_path': path,
                        'page_num': i,
                        'doc': pdf_doc,
                        'name': item_name
                    })

            elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff']:
                item_name = os.path.basename(path)
                item = QListWidgetItem(item_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.list_items.addItem(item)
                self.vl_items.append({
                    'type': 'image',
                    'path': path,
                    'name': item_name
                })

        if self.list_items.count() > 0:
            self.list_items.setCurrentRow(0)

        if len(paths) == 1:
            self.le_file_path.setText(paths[0])
        else:
            self.le_file_path.setText(f"{len(paths)} files selected")

        self.clear_individual_prompts()
        self.btn_save.setEnabled(False)

    def on_item_selected(self, row: int):
        if row < 0 or row >= len(self.vl_items):
            return

        item = self.vl_items[row]

        if item['type'] == 'pdf_page':
            page = item['doc'][item['page_num']]
            pix = page.get_pixmap(dpi=75)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)

            width_pt = page.rect.width
            height_pt = page.rect.height
            width_px = int(width_pt)
            height_px = int(height_pt)

            self.sb_max_width.setValue(
                max(min(width_px, self.sb_max_width.maximum()), self.sb_max_width.minimum())
            )
            self.sb_max_height.setValue(
                max(min(height_px, self.sb_max_height.maximum()), self.sb_max_height.minimum())
            )

        elif item['type'] == 'image':
            pixmap = QPixmap(item['path'])
            self.sb_max_width.setValue(
                max(min(pixmap.width(), self.sb_max_width.maximum()), self.sb_max_width.minimum())
            )
            self.sb_max_height.setValue(
                max(min(pixmap.height(), self.sb_max_height.maximum()), self.sb_max_height.minimum())
            )

        self.lbl_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_preview.setScaledContents(False)
        self.lbl_preview.setPixmap(pixmap)
        self.lbl_preview.adjustSize()

    def save_vl_results(self):
        if not self.vl_responses:
            QMessageBox.warning(self, "Error", "No responses to save.")
            return

        data = {
            "source_files": [],
            "date_processed": datetime.datetime.now().isoformat(),
            "items": []
        }

        source_files = set()

        for idx, response in self.vl_responses.items():
            item = self.vl_items[idx]

            if item['type'] == 'pdf_page':
                source_files.add(item['pdf_path'])
            else:
                source_files.add(item['path'])

            prompt = self.vl_prompts.get(idx, self.te_default_prompt.toPlainText()) \
                if self.cb_individual_prompts.isChecked() else self.te_default_prompt.toPlainText()

            data["items"].append({
                "name": item['name'],
                "type": item['type'],
                "source": item['pdf_path'] if item['type'] == 'pdf_page' else item['path'],
                "page_number": item['page_num'] if item['type'] == 'pdf_page' else None,
                "prompt": prompt,
                "response": response
            })

        data["source_files"] = list(source_files)

        if len(source_files) == 1:
            suggested_name = os.path.splitext(os.path.basename(list(source_files)[0]))[0] + "_vl_results"
        else:
            suggested_name = "multiple_files_vl_results"

        filename, ok = QtWidgets.QInputDialog.getText(
            self,
            "Save Results",
            "Enter filename (no extension):",
            text=suggested_name
        )

        if not ok or not filename.strip():
            return

        filename = filename.strip() + ".json"
        save_path = os.path.join(self.parent_app.history_dir, filename)

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.parent_app.status_bar.showMessage(f"Saved JSON to {save_path}", 5000)

        combined = "\n\n".join([
            f"--- {item['name']} ---\n{item['response']}"
            for item in data["items"]
        ])

        self.parent_app.search_history.append((filename, combined))
        self.parent_app.save_history()
        self.parent_app.status_bar.showMessage(f"History updated with {filename}", 5000)

    def save_selected_images(self):
        """
        Save all checked items as PNG files to a user-selected directory.
        """
        # Gather indices of checked items
        checked_indices = []
        for i in range(self.list_items.count()):
            if self.list_items.item(i).checkState() == Qt.CheckState.Checked:
                checked_indices.append(i)

        if not checked_indices:
            QMessageBox.warning(self, "No Selection", "Please select at least one item to save.")
            return

        # Ask user for a target folder
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if not folder:
            return

        saved_count = 0
        for idx in checked_indices:
            item = self.vl_items[idx]
            # Create a PIL Image from the item (PDF page or image file)
            if item['type'] == 'pdf_page':
                page = item['doc'][item['page_num']]
                pix = page.get_pixmap(dpi=100)
                pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            else:
                pil_img = Image.open(item['path'])
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')

            # Derive filename from the stored 'name' field, ensuring uniqueness
            base_name = item['name'].replace(" ", "_").replace("/", "_")
            save_path = os.path.join(folder, f"{base_name}.png")

            pil_img.save(save_path, format="PNG")
            saved_count += 1

        QMessageBox.information(
            self,
            "Save Complete",
            f"Saved {saved_count} image(s) to:\n{folder}"
        )
