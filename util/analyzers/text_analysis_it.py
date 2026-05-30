#!/usr/bin/env python
"""
text_analysis_it.py

Italian-specific text analysis module inheriting from BaseTextAnalysis.
Located in the 'analyzers' folder.
"""

import spacy
import spacy.cli
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis
import re

# Tooltip translations in Italian for Italian text analysis.
TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Frasi Complesse</b><br>
        Evidenzia le frasi molto lunghe o con una struttura complessa, che possono risultare difficili da comprendere.<br>
        Considera di suddividerle in frasi più brevi e accessibili.
    """,
    "weak": """
        <b>Formulazioni Deboli/Voce Passiva</b><br>
        Indica frammenti di testo con un linguaggio impreciso o poco deciso.<br>
        Include:<br>
        - Formulazioni deboli (espressioni poco chiare o indecise)<br>
        - Voce passiva (frasi in cui il soggetto non esegue l'azione)<br>
        Esempio: 'La palla è stata lanciata' vs 'Marco ha lanciato la palla'<br>
        Entrambe possono rendere il testo meno diretto.
    """,
    "nonstandard": """
        <b>Verbi di Parlato Non Standard</b><br>
        Indica l'uso di verbi atipici per descrivere il parlato<br>
        (invece di quelli comuni come 'ha detto').<br>
        Verbi troppo creativi possono confondere il lettore.
    """,
    "filter": """
        <b>Parole Filtranti</b><br>
        Indica parole che indeboliscono il messaggio<br>
        (come 'appena', 'davvero', 'letteralmente').<br>
        La loro rimozione può rafforzare la chiarezza del testo.
    """,
    "telling": """
        <b>Raccontare invece di Mostrare</b><br>
        Evidenzia le sezioni in cui le emozioni o le azioni vengono enunciate direttamente<br>
        invece di essere mostrate tramite descrizioni o azioni.<br>
        Questo può ridurre l'engagement del lettore.
    """,
    "weak_verb": """
        <b>Verbi Deboli</b><br>
        Indica verbi privi di una forte carica emotiva.<br>
        Sostituirli con sinonimi più incisivi può dare vita al testo.
    """,
    "overused": """
        <b>Parole Eccessivamente Usate</b><br>
        Evidenzia parole che appaiono troppo frequentemente.<br>
        Utilizza sinonimi o cambia la struttura della frase per variare.
    """,
    "pronoun": """
        <b>Riferimenti Ambigui dei Pronomi</b><br>
        Indica pronomi ('lui', 'lei', 'esso', 'essi') con antecedenti poco chiari.<br>
        Un uso chiaro dei pronomi previene malintesi.
    """,
    "repetitive": """
        <b>Inizi di Frase Ripetitivi</b><br>
        Evidenzia sequenze di frasi che iniziano allo stesso modo.<br>
        Varietà negli inizi delle frasi mantiene l'attenzione del lettore.
    """
}

# Italian-specific linguistic data for analysis.
ITALIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"da"},
    # Capture weak adverbs ending with '-mente'
    "weak_patterns": [r'\b\w+mente\b'],
    "weak_terms": {"forse", "probabilmente", "magari", "sembra", "apparentemente", "un po'", "poco"},
    "standard_speech_verbs": {"dire", "chiedere"},
    "speech_verbs": {"dire", "chiedere", "sussurrare", "gridare", "borbottare", "esclamare"},
    # Example filtering words that may weaken the message.
    "filter_words": {"praticamente", "in realtà", "effettivamente", "letteralmente"},
    "telling_verbs": {"essere", "sembrare", "apparire", "diventare"},
    "emotion_words": {"triste", "felice", "arrabbiato", "eccitato", "nervoso", "spaventato",
                      "preoccupato", "imbarazzato", "deluso", "frustrato", "stupito", "confuso",
                      "orgoglioso", "soddisfatto"},
    "weak_verbs": {"essere"},
    "common_words": {"e", "in", "su", "con", "a", "ma", "o", "il", "lo", "la", "i", "gli", "le",
                     "un", "una", "del", "della"},
    "quote_pattern": r'“[^”]*”|\"[^\"]*\"'
}

class ItalianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded.
    model_loaded = pyqtSignal()

    def __init__(self):
        # Initialize using the Italian spaCy model and linguistic data.
        BaseTextAnalysis.__init__(self, "it_core_news_sm", ITALIAN_DATA)
        QObject.__init__(self)
        self.download_in_progress = False

    def initialize(self):
        """
        Initializes the spaCy model. If the model is not found, prompts the user to download it.
        """
        if super().initialize():
            return True
        if not self.download_in_progress and self.ask_for_download():
            self.download_in_progress = True
            threading.Thread(target=self.download_and_load_model, daemon=True).start()
        return False

    def ask_for_download(self):
        """
        Asks the user if they want to download the missing spaCy model.
        """
        msgBox = QMessageBox()
        msgBox.setWindowTitle("spaCy Model")
        msgBox.setText("The model 'it_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('it_core_news_sm')
            self.nlp = spacy.load('it_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates readability for Italian using the Gulpease Index.
        The Gulpease Index is calculated as:
            89 + ((300 * number_of_sentences - 10 * number_of_letters) / number_of_words)
        """
        words = text.split()
        num_words = len(words)
        # Split text into sentences using punctuation as delimiters.
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        # Count the number of letters (ignoring punctuation).
        num_letters = sum(len(re.sub(r'\W', '', word)) for word in words)
        if num_words == 0 or num_sentences == 0:
            return 0
        return 89 + ((300 * num_sentences - 10 * num_letters) / num_words)

    def get_tooltips(self):
        """Returns the Italian tooltips for text analysis."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Italian text analysis module.
    """
    global nlp
    analysis = ItalianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = ItalianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Italian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
