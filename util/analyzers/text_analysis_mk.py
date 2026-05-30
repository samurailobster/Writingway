#!/usr/bin/env python
"""
text_analysis_mk.py

Macedonian-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis
import re

# Tooltip translations for Macedonian
TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Комплексни реченици</b><br>
        Идентификува многу долги или сложни структури на речениците кои можат да бидат тешки за разбирање.<br>
        Размислете за нивно делење на пократки, појасни реченици.
    """,
    "weak": """
        <b>Слаби формулации/пасивен глас</b><br>
        Означува делови од текстот со непоопределен или нежаран јазик.<br>
        Вклучува:<br>
        - Слаби формулации (нејасни или неподредени изрази)<br>
        - Пасивен глас (реченици каде субјектот не извршува акцијата)<br>
        Пример: 'Топката беше фрлена' vs 'Јан фрли топката'<br>
        И двете може да направат текстот помалку директен.
    """,
    "nonstandard": """
        <b>Нетрадиционални глаголи за говорење</b><br>
        Означува нетипични глаголи што ги опишуваат говорот<br>
        (наместо обичните како 'рече').<br>
        Прекумерно креативни глаголи може да забунат читателот.
    """,
    "filter": """
        <b>Зборови кои филтрираат</b><br>
        Означува зборови кои ослабуваат пораката<br>
        (како 'само', 'вистински', 'буквално').<br>
        Нивното отстранување може да ја зголеми јасноста на текстот.
    """,
    "telling": """
        <b>Преткажување наместо покажување</b><br>
        Означува делови каде што емоциите или акцијата се наведуваат директно<br>
        наместо да се покажат преку описи или дејства.<br>
        Ова може да ја намали ангажираноста на читателот.
    """,
    "weak_verb": """
        <b>Слаби глаголи</b><br>
        Означува глаголи без јасен емоционален набој.<br>
        Заменувањето со појачани синоними може да го оживее текстот.
    """,
    "overused": """
        <b>Прекумерно употребувани зборови</b><br>
        Означува зборови што се повторуваат премногу често.<br>
        Користете синоними или променете ја структурата на речениците за да ги разнообразите.
    """,
    "pronoun": """
        <b>Нејасни референци на заменки</b><br>
        Означува заменки ('тој', 'таа', 'тоа', 'тие') со нејасен контекст.<br>
        Јасната употреба на заменките спречува недоразбирања.
    """,
    "repetitive": """
        <b>Повеќето почетоци на реченици</b><br>
        Означува серија на реченици кои започнуваат на истиот начин.<br>
        Разновидноста во започнувањето на речениците ги одржува читателите ангажирани.
    """
}

# Macedonian-specific linguistic data
MACEDONIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"од"},
    "weak_patterns": [r'\b\w+(?:о|е)\b'],
    "weak_terms": {"можеби", "веројатно", "изгледа", "како да", "малку", "некако"},
    "standard_speech_verbs": {"кажам", "прашам"},
    "speech_verbs": {"кажам", "прашам", "шаптам", "извикам", "муркнам"},
    "filter_words": {"видел", "чува", "чув", "забележал", "размислил", "набљудувал", "гледал", "слушал", "осетил", "одлучил", "се појавил", "забележал", "се осетил"},
    "telling_verbs": {"биде", "се чувствува", "изгледа", "се појавува", "станува"},
    "emotion_words": {"лош", "тажен", "среќен", "возбуден", "нервен", "страшен", "загрижен", "осрамнет", "разочаран", "фрустриран", "задоволен", "ентусијастичен", "завистлив"},
    "weak_verbs": {"биде"},
    "common_words": {"и", "во", "на", "со", "за", "од", "а", "но", "ќе", "не", "да", "се", "тоа", "ова", "тие"},
    "quote_pattern": r'„[^”]*”|\"[^\"]*\"'
}


class MacedonianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "mk_core_news_sm", MACEDONIAN_DATA)
        QObject.__init__(self)
        self.download_in_progress = False

    def initialize(self):
        """
        Initializes the spaCy model for Macedonian. If the model is not found, prompts the user to download it.
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
        msgBox.setText("The model 'mk_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('mk_core_news_sm')
            self.nlp = spacy.load('mk_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability (Индекс на читливост) for Macedonian using a variant of the Fog Index.
        A word is considered difficult if it contains at least 2 vowels (а, е, и, о, у).
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        num_difficult_words = sum(1 for word in words if len(re.findall(r'[аеиоу]', word.lower())) >= 2)
        if num_sentences == 0 or num_words == 0:
            return 0
        return 0.4 * ((num_words / num_sentences) + 100 * (num_difficult_words / num_words))

    def get_tooltips(self):
        """Returns tooltips in Macedonian."""
        return TOOLTIP_TRANSLATIONS


# Global variable for the spaCy model instance
nlp = None

def initialize():
    """
    Initializes the Macedonian text analysis module.
    """
    global nlp
    analysis = MacedonianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = MacedonianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Macedonian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
