#!/usr/bin/env python
"""
text_analysis_de.py

German-specific text analysis module inheriting from BaseTextAnalysis.
Implements readability calculation using the Wiener Sachtextformel.
"""

import re
import threading

import spacy
import spacy.cli
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from .base_text_analysis import BaseTextAnalysis

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Komplexe Sätze</b><br>
        Hebt Sätze hervor, die sehr lang oder komplex strukturiert sind und schwer zu folgen sind.<br>
        Erwägen Sie, sie in kürzere, klarere Sätze aufzuteilen.
    """,
    "weak": """
        <b>Schwache Formulierungen/passiv</b><br>
        Markiert Textstellen, in denen die Sprache unpräzise oder wenig bestimmt ist.<br>
        Umfasst:<br>
        - Schwache Formulierungen (ungenaue oder zögerliche Ausdrücke)<br>
        - Passiv (Sätze, in denen das Subjekt nicht die Handlung ausführt)<br>
        Beispiel: 'Der Ball wurde geworfen' vs. 'Hans warf den Ball'
    """,
    "nonstandard": """
        <b>Unkonventionelle Sprechverben</b><br>
        Identifiziert ungewöhnliche oder seltene Verben, die zum Sprechen verwendet werden<br>
        (statt gängiger Verben wie 'sagen').<br>
        Zu kreative Verben können den Leser verwirren.
    """,
    "filter": """
        <b>Filterwörter</b><br>
        Markiert Wörter, die den Inhalt abschwächen oder verdecken<br>
        (wie 'eben', 'wirklich', 'bloß').<br>
        Das Entfernen kann die Klarheit des Textes verbessern.
    """,
    "telling": """
        <b>Wörtliche Darstellung statt Anschauung</b><br>
        Hebt Stellen hervor, an denen Informationen direkt wiedergegeben werden<br>
        statt durch Beschreibung oder Handlung gezeigt zu werden.<br>
        Dies kann den Text weniger ansprechend machen.
    """,
    "weak_verb": """
        <b>Schwache Verben</b><br>
        Kennzeichnet Verben, die keinen starken Aktions- oder Emotionsgehalt haben.<br>
        Der Austausch gegen präzisere Verben kann den Text dynamischer machen.
    """,
    "overused": """
        <b>Überbeanspruchte Wörter</b><br>
        Identifiziert Wörter, die zu häufig vorkommen und den Text monoton machen.<br>
        Verwenden Sie Synonyme oder formulieren Sie um, um Abwechslung zu schaffen.
    """,
    "pronoun": """
        <b>Unklare Pronomenbezüge</b><br>
        Markiert Pronomen (z.B. 'er', 'sie', 'es', 'sie') ohne klare Bezugnahme.<br>
        Klare Pronomenbezüge vermeiden Verwirrung.
    """,
    "repetitive": """
        <b>Wiederholte Satzanfänge</b><br>
        Hebt Sätze hervor, die immer wieder gleich beginnen.<br>
        Variieren Sie die Satzanfänge, um das Interesse des Lesers zu erhalten.
    """
}

GERMAN_DATA = {
    "passive_deps": {"nsubjpass", "auxpass"},
    "agent_markers": {"von"},
    "weak_patterns": [r'\b\w+lich\b'],
    "weak_terms": {"vielleicht", "möglicherweise", "anscheinend", "scheinbar"},
    "standard_speech_verbs": {"sagen", "fragen"},
    "speech_verbs": {"sagen", "fragen", "flüstern", "rufen", "murmeln", "verkünden"},
    "filter_words": {"sah", "hörte", "fühlte", "bemerkt", "dachte", "überlegte", "beobachtete", "schaute", "lauschte"},
    "telling_verbs": {"sein", "fühlen", "scheinen", "wirken", "erscheinen", "werden"},
    "emotion_words": {"wütend", "traurig", "glücklich", "aufgeregt", "nervös", "ängstlich", "besorgt", "beschämt", "enttäuscht", "frustriert", "verärgert", "unsicher", "erschrocken", "freudig", "deprimiert"},
    "weak_verbs": {"sein"},
    "common_words": {"der", "die", "das", "ein", "eine", "und", "oder", "in", "auf", "zu", "von", "mit", "ist", "sind", "war", "waren", "haben", "hat"},
    "quote_pattern": r'„[^“]*”|\"[^\"]*\"'
}

class GermanTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "de_core_news_sm", GERMAN_DATA)
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
        msgBox.setText("The model 'de_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('de_core_news_sm')
            self.nlp = spacy.load('de_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for German using the Wiener Sachtextformel.
        The formula used is an example and may need adjustment.
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        # Count words with three or more vowels (simplistic measure for "difficult" words)
        num_difficult_words = sum(1 for word in words if len(re.findall(r'[aeiouäöü]', word.lower())) >= 3)
        if num_sentences == 0 or num_words == 0:
            return 0
        # Example formula similar to Wiener Sachtextformel:
        return 0.4 * ((num_words / num_sentences) + 100 * (num_difficult_words / num_words))

    def get_tooltips(self):
        """Returns tooltips in German."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the German text analysis module.
    """
    global nlp
    analysis = GermanTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = GermanTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("German spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
