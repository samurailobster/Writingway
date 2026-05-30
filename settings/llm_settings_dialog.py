from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QPushButton, QGroupBox
from settings.llm_api_aggregator import WWApiAggregator

class LLMSettingsDialog(QDialog):
    """A reusable modal dialog for selecting LLM provider overrides."""
    
    def __init__(self, parent=None, default_provider=None, default_model=None, default_timeout=30, default_max_tokens=1024):
        super().__init__(parent)
        self.setWindowTitle("LLM Settings")
        self.setModal(True)
        self.selected_settings = {}
        self.init_ui(default_provider, default_model, default_timeout, default_max_tokens)

    def init_ui(self, default_provider, default_model, default_timeout, default_max_tokens):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Provider selection
        self.provider_combo = QComboBox()
        providers = WWApiAggregator.get_llm_providers()
        self.provider_combo.addItems(providers)
        if default_provider and default_provider in providers:
            self.provider_combo.setCurrentText(default_provider)
        self.provider_combo.currentTextChanged.connect(self.update_model_combo)
        form_layout.addRow("Provider:", self.provider_combo)

        # Model selection
        self.model_combo = QComboBox()
        self.update_model_combo(self.provider_combo.currentText())
        if default_model:
            self.model_combo.setCurrentText(default_model)
        form_layout.addRow("Model:", self.model_combo)

        # Tokens and Timeout row
        tokens_timeout_layout = QVBoxLayout()
        
        # Max Tokens selection
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 16384)  # Reasonable range for most LLMs
        self.max_tokens_spin.setValue(default_max_tokens)
        self.max_tokens_spin.setSingleStep(100)  # Step by 100 tokens
        form_layout.addRow("Max Tokens:", self.max_tokens_spin)

        # Timeout selection
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)  # 5 seconds to 5 minutes
        self.timeout_spin.setValue(default_timeout)
        self.timeout_spin.setSuffix(" seconds")
        form_layout.addRow("Timeout:", self.timeout_spin)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QVBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.resize(300, 200)

    def update_model_combo(self, provider_name):
        """Update the model dropdown based on the selected provider."""
        self.model_combo.clear()
        provider = WWApiAggregator.aggregator.get_provider(provider_name)
        if provider:
            try:
                models = provider.get_available_models()
                self.model_combo.addItems(models)
            except Exception as e:
                self.model_combo.addItem("Default Model")
                print(f"Error fetching models for {provider_name}: {e}")
        else:
            self.model_combo.addItem("Default Model")

    def get_settings(self):
        """Return the selected settings as a dictionary."""
        return {
            "provider": self.provider_combo.currentText(),
            "model": self.model_combo.currentText(),
            "timeout": self.timeout_spin.value(),
            "max_tokens": self.max_tokens_spin.value()
        }

    @staticmethod
    def show_dialog(parent=None, default_provider=None, default_model=None, default_timeout=60, default_max_tokens=3000):
        """Static method to show the dialog and return settings if accepted."""
        dialog = LLMSettingsDialog(parent, default_provider, default_model, default_timeout, default_max_tokens)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            return dialog.get_settings()
        return None
