#!/usr/bin/env python
"""
text_analysis_da.py

Danish-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
import math
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis
import re

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Komplekse sætninger</b><br>
        Fremhæver meget lange eller komplicerede sætninger, som kan være svære at forstå.<br>
        Overvej at opdele dem i kortere, mere forståelige sætninger.
    """,
    "weak": """
        <b>Svage formuleringer/passiv</b><br>
        Markerer tekstdele med upræcist eller ikke-bestemt sprog.<br>
        Inkluderer:<br>
        - Svage formuleringer (uklare eller tøvende udtryk)<br>
        - Passiv form (sætninger hvor subjektet ikke udfører handlingen)<br>
        Eksempel: 'Bolden blev kastet' vs 'Jan kastede bolden'<br>
        Begge kan gøre teksten mindre direkte.
    """,
    "nonstandard": """
        <b>Ikke-standard taleverbier</b><br>
        Indikerer usædvanlige verbier, der beskriver tale<br>
        (i stedet for almindelige som 'sagde').<br>
        For kreative verbier kan forvirre læseren.
    """,
    "filter": """
        <b>Filtrerende ord</b><br>
        Markerer ord, der svækker budskabet<br>
        (som 'lige', 'virkelig', 'bogstaveligt').<br>
        Fjernelse af dem vil styrke tekstens klarhed.
    """,
    "telling": """
        <b>Fortælling i stedet for visning</b><br>
        Fremhæver passager, hvor følelser eller handlinger er direkte angivet<br>
        i stedet for at vise dem gennem beskrivelser eller handlinger.<br>
        Dette kan reducere læserens engagement.
    """,
    "weak_verb": """
        <b>Svage verber</b><br>
        Markerer verber uden tydelig følelsesmæssig ladning.<br>
        Erstatning med stærkere synonymer vil gøre teksten mere levende.
    """,
    "overused": """
        <b>Overbrugte ord</b><br>
        Indikerer ord, der gentages for ofte.<br>
        Brug synonymer eller ændr sætningsstrukturen for mere variation.
    """,
    "pronoun": """
        <b>Uklare pronomenreferencer</b><br>
        Markerer pronomener ('han', 'hun', 'det', 'de') med uklar kontekst.<br>
        Tydelig brug af pronomener forhindrer misforståelser.
    """,
    "repetitive": """
        <b>Gentagne sætningsbegyndelser</b><br>
        Indikerer sekvenser af sætninger, der begynder ens.<br>
        Variation i sætningsbegyndelser holder læserens opmærksomhed.
    """
}

DANISH_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"af"},
    "weak_patterns": [r'\b\w+(?:e|t)\b'],
    "weak_terms": {"måske", "muligvis", "sandsynligvis", "formentlig", "synes at", "som om", "lidt", "noget"},
    "standard_speech_verbs": {"sige", "spørge"},
    "speech_verbs": {"sige", "spørge", "hviske", "råbe", "mumle", "udbryde"},
    "filter_words": {"så", "hørte", "følte", "bemærkede", "tænkte", "spekulerede", "observerede", "kiggede", "lyttede", "fornemmede", "besluttede", "overvejede", "syntes", "dukkede op", "iagttog", "oplevede", "opfattede", "forestillede sig"},
    "telling_verbs": {"være", "føle", "synes", "se ud", "dukke op", "blive"},
    "emotion_words": {"vred", "ked af det", "glad", "begejstret", "nervøs", "bange", "bekymret", "flov", "skuffet", "frustreret", "irriteret", "urolig", "bange", "lykkelig", "trist", "ulykkelig", "ekstatisk", "ophidset", "rasende", "henrykt", "chokeret", "overrasket", "forvirret", "stolt", "tilfreds", "tilfreds", "entusiastisk", "jaloux"},
    "weak_verbs": {"være"},
    "common_words": {"og", "i", "på", "med", "til", "om", "men", "eller", "som", "er", "var", "har", "havde", "dette", "den", "det", "de", "der", "her", "min", "din", "hans", "hendes", "vores", "jeres", "deres", "sig", "ikke", "ja", "nej", "hvis", "når", "fordi", "hvilken", "hvilke"},
    "quote_pattern": r'„[^"]*"|\"[^\"]*\"'
}

class DanishTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "da_core_news_sm", DANISH_DATA)
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
        msgBox.setText("The model 'da_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('da_core_news_sm')
            self.nlp = spacy.load('da_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Danish using the LIX (Läsbarhetsindex/Læsbarhedsindeks).
        
        LIX is a readability measure commonly used for Scandinavian languages including Danish.
        Formula: LIX = A/B + (C*100)/A, where:
        - A is the number of words
        - B is the number of sentences
        - C is the number of long words (more than 6 characters)
        
        Interpretation of LIX scores:
        - < 25: Very easy, children's books
        - 25-35: Easy, popular fiction
        - 35-45: Medium, newspaper text
        - 45-55: Difficult, official documents
        - > 55: Very difficult, technical literature
        """
        words = text.split()
        num_words = len(words)
        
        # Count sentences - split by period, exclamation mark, or question mark
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        
        # Count long words (more than 6 characters)
        num_long_words = sum(1 for word in words if len(word) > 6)
        
        if num_sentences == 0 or num_words == 0:
            return 0
            
        # Calculate LIX
        words_per_sentence = num_words / num_sentences
        percentage_long_words = (num_long_words * 100) / num_words
        lix = words_per_sentence + percentage_long_words
        
        return lix
        
    def get_tooltips(self):
        """Returns tooltips in Danish."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Danish text analysis module.
    """
    global nlp
    analysis = DanishTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = DanishTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Danish spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)