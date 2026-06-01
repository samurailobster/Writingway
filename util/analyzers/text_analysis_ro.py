#!/usr/bin/env python
"""
text_analysis_ro.py

Romanian-specific text analysis module inheriting from BaseTextAnalysis.
This module is adapted from the Polish version and configured for the Romanian language.
It uses the spaCy model "ro_core_news_sm" and provides language-specific data,
tooltip translations (translated to Romanian) and a custom readability index function.
"""

import re
import threading

import spacy
import spacy.cli
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from util.base_text_analysis import BaseTextAnalysis

# Romanian tooltip translations
TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Propoziții complexe</b><br>
        Evidențiază propoziții foarte lungi sau cu structură complicată, care pot fi greu de înțeles.<br>
        Luați în considerare împărțirea lor în propoziții mai scurte și mai accesibile.
    """,
    "weak": """
        <b>Formulări slabe/voce pasivă</b><br>
        Indică fragmente de text cu un limbaj imprecis sau puțin ferm.<br>
        Include:<br>
        - Formulări slabe (expresii neclare sau ezitante)<br>
        - Vocea pasivă (propoziții în care subiectul nu efectuează acțiunea)<br>
        Exemplu: 'Mingea a fost aruncată' vs 'Ion a aruncat mingea'<br>
        Ambele pot face ca textul să fie mai puțin direct.
    """,
    "nonstandard": """
        <b>Verbe de vorbire neconvenționale</b><br>
        Indică verbe neobișnuite care descriu vorbirea<br>
        (în locul celor comune, cum ar fi 'a spus').<br>
        Verbele prea creative pot dezorienta cititorul.
    """,
    "filter": """
        <b>Cuvinte de filtrare</b><br>
        Indică cuvinte care slăbesc mesajul<br>
        (ca 'chiar', 'de fapt', 'literal').<br>
        Eliminarea lor va întări claritatea textului.
    """,
    "telling": """
        <b>Povestire în loc de arătare</b><br>
        Evidențiază fragmente în care emoțiile sau acțiunile sunt expuse direct<br>
        în loc să fie arătate prin descrieri sau acțiuni.<br>
        Aceasta poate reduce implicarea cititorului.
    """,
    "weak_verb": """
        <b>Verbe slabe</b><br>
        Indică verbe fără o încărcătură emoțională clară.<br>
        Înlocuirea lor cu sinonime mai puternice va revitaliza textul.
    """,
    "overused": """
        <b>Cuvinte suprautilizate</b><br>
        Indică cuvinte care se repetă prea des.<br>
        Folosiți sinonime sau schimbați ordinea propoziției pentru diversificare.
    """,
    "pronoun": """
        <b>Referințe neclare la pronume</b><br>
        Indică pronume ('el', 'ea', 'acesta', 'ei') folosite fără context clar.<br>
        Utilizarea clară a pronumelor previne confuziile.
    """,
    "repetitive": """
        <b>Începuturi repetitive de propoziții</b><br>
        Indică secvențe de propoziții care încep la fel.<br>
        Diversitatea începuturilor de propoziții menține atenția cititorului.
    """
}

# Romanian-specific data
ROMANIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"de"},  # In Romanian passive constructions the marker is usually "de" or "de către"
    # A simple pattern that might capture some weak formulations; this may require further tuning.
    "weak_patterns": [r'\b\w+(?:ul|a)\b'],
    "weak_terms": {"poate", "probabil", "aparent", "posibil"},
    "standard_speech_verbs": {"a spune", "a întreba"},
    "speech_verbs": {"a spune", "a întreba", "a șopti", "a striga", "a murmura"},
    # Filter words that may weaken the text; this list can be extended.
    "filter_words": {"chiar", "de fapt", "literal", "aproape", "încă"},
    "telling_verbs": {"a fi", "a părea", "a se simți", "a arăta", "a deveni"},
    "emotion_words": {
        "furios", "trist", "fericit", "entuziasmat", "nervos", "înfricoșat",
        "îngrijorat", "rușinat", "dezamăgit", "frustrat", "iritat", "neliniștit",
        "înspăimântat", "bucuros", "deprimat", "nefericit", "extatic", "agitat",
        "mânie", "încântat", "șocat", "surprins", "confuz", "mândru", "mulțumit",
        "satisfăcut", "invidios"
    },
    "weak_verbs": {"a fi"},
    "common_words": {
        "și", "în", "pe", "la", "de", "cu", "sau", "dar", "cum", "este", "sunt",
        "a fost", "are", "au", "acesta", "aceasta", "aceste", "acelor", "acest",
        "aceea", "acolo", "aici", "meu", "tău", "al lui", "a ei", "nostru", "al vostru",
        "lor", "se", "nu", "da", "că"
    },
    "quote_pattern": r'„[^”]*”|\"[^\"]*\"'
}


class RomanianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        # Initialize BaseTextAnalysis with the Romanian spaCy model and language-specific data
        BaseTextAnalysis.__init__(self, "ro_core_news_sm", ROMANIAN_DATA)
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
        msgBox.setText("The model 'ro_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('ro_core_news_sm')
            self.nlp = spacy.load('ro_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates a readability index for Romanian text (Indicele de lizibilitate).
        This implementation is based on a Fog-like formula, adjusted with Romanian vowels.
        """
        words = text.split()
        num_words = len(words)
        # Split sentences on common punctuation marks
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        # Define Romanian vowels (including diacritics)
        pattern = re.compile(r'[aeiouăâî]', re.IGNORECASE)
        # A word is considered difficult if it contains 3 or more vowels.
        num_difficult_words = sum(1 for word in words if len(pattern.findall(word)) >= 3)
        if num_sentences == 0 or num_words == 0:
            return 0
        # Fog-like index adapted for Romanian
        return 0.4 * ((num_words / num_sentences) + 100 * (num_difficult_words / num_words))

    def get_tooltips(self):
        """
        Returns tooltip translations for Romanian.
        """
        return TOOLTIP_TRANSLATIONS


# Global variable to hold the spaCy model instance
nlp = None

def initialize():
    """
    Initializes the Romanian text analysis module.
    """
    global nlp
    analysis = RomanianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = RomanianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("The Romanian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
