#!/usr/bin/env python
"""
text_analysis_sv.py

Swedish-specific text analysis module inheriting from BaseTextAnalysis.
"""

import re
import threading

import spacy
import spacy.cli
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from util.base_text_analysis import BaseTextAnalysis

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Komplexa meningar</b><br>
        Framhäver meningar som är mycket långa eller har en komplicerad struktur vilket kan vara svårt att förstå.<br>
        Överväg att dela upp dem i kortare, mer lättillgängliga meningar.
    """,
    "weak": """
        <b>Svaga formuleringar/Passiv röst</b><br>
        Anger delar av texten med otydligt språk eller brist på bestämdhet.<br>
        Inkluderar svaga formuleringar (oklara eller obeslutsamma uttryck) samt passiv röst (meningar där subjektet inte utför handlingen).<br>
        Exempel: 'Bollen kastades' jämfört med 'John kastade bollen'. Båda kan göra texten mindre direkt.
    """,
    "nonstandard": """
        <b>Icke-standardiserade talverben</b><br>
        Anger ovanliga verb som används för att beskriva tal (istället för vanliga som 'sade').<br>
        Alltför kreativa talverb kan förvirra läsaren.
    """,
    "filter": """
        <b>Filterord</b><br>
        Anger ord som försvagar budskapet (som 'bara', 'verkligen', 'bokstavligen').<br>
        Att ta bort dem stärker textens tydlighet.
    """,
    "telling": """
        <b>Berättande istället för att visa</b><br>
        Framhäver passager där känslor eller handlingar anges direkt istället för att visas genom beskrivningar eller handlingar.<br>
        Detta kan minska läsarens engagemang.
    """,
    "weak_verb": """
        <b>Svaga verb</b><br>
        Anger verb som saknar stark känslomässig laddning.<br>
        Att ersätta dem med kraftfullare synonymer kan göra texten mer levande.
    """,
    "overused": """
        <b>Överanvända ord</b><br>
        Framhäver ord som förekommer för ofta.<br>
        Använd synonymer eller variera meningsstrukturen för att öka variationen.
    """,
    "pronoun": """
        <b>Oklara pronomenreferenser</b><br>
        Anger pronomen ('han', 'hon', 'den', 'de') med otydligt sammanhang.<br>
        Klar användning av pronomen förhindrar missförstånd.
    """,
    "repetitive": """
        <b>Repetitiva meningsinledningar</b><br>
        Framhäver sekvenser av meningar som inleds på samma sätt.<br>
        Variation i meningsinledningar håller läsarens intresse vid liv.
    """
}

# Swedish-specific linguistic data used for analysis
SWEDISH_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"av"},
    # A sample weak pattern (this can be adjusted as needed for Swedish language nuances)
    "weak_patterns": [r'\b\w+(?:ig)\b'],
    "weak_terms": {"kanske", "möjligen", "antagligen", "troligtvis"},
    "standard_speech_verbs": {"säga", "fråga"},
    "speech_verbs": {"säga", "fråga", "viska", "skrika", "mumla"},
    "filter_words": {"såg", "hörde", "kände", "noterade", "tänkte", "observerade"},
    "telling_verbs": {"vara", "känna sig", "verka", "se ut", "framträda", "bli"},
    "emotion_words": {"arg", "ledsen", "glad", "upphetsad", "nervös", "skrämd", "bekymrad",
                      "skamsen", "besviken", "frustrerad", "irriterad", "orolig", "rädd",
                      "lycklig", "deprimerad", "olycklig", "extatisk", "upprörd", "förvånad",
                      "förbryllad", "stolt", "nöjd"},
    "weak_verbs": {"vara"},
    "common_words": {"och", "i", "på", "av", "att", "det", "en", "den", "som", "är",
                     "var", "varit", "har", "med", "för", "om", "men"},
    "quote_pattern": r'“[^”]*”|\"[^\"]*\"'
}

class SwedishTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        # Initialize with the Swedish spaCy model and Swedish-specific data
        BaseTextAnalysis.__init__(self, "sv_core_news_sm", SWEDISH_DATA)
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
        msgBox.setText("The model 'sv_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('sv_core_news_sm')
            self.nlp = spacy.load('sv_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability of Swedish text using the LIX (Läsbarhetsindex) formula.
        LIX = (number of words / number of sentences) + ( (number of long words * 100) / number of words )
        Long words are defined as words with more than 6 characters.
        """
        words = re.findall(r'\w+', text)
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        num_long_words = sum(1 for word in words if len(word) > 6)
        if num_sentences == 0 or num_words == 0:
            return 0
        return (num_words / num_sentences) + (num_long_words * 100 / num_words)

    def get_tooltips(self):
        """Returns English tooltips for the Swedish analysis."""
        return TOOLTIP_TRANSLATIONS

# Global variable for the spaCy NLP model
nlp = None

def initialize():
    """
    Initializes the Swedish text analysis module.
    """
    global nlp
    analysis = SwedishTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = SwedishTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Swedish spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
