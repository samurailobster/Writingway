#!/usr/bin/env python
"""
text_analysis_nb.py

Norwegian-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis
import re

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Komplekse setninger</b><br>
        Fremhever setninger som er veldig lange eller har komplisert struktur, som kan være vanskelige å forstå.<br>
        Vurder å dele dem inn i kortere, mer tilgjengelige setninger.
    """,
    "weak": """
        <b>Svake formuleringer/passiv form</b><br>
        Markerer tekstdeler med upresist eller lite bestemt språk.<br>
        Inkluderer:<br>
        - Svake formuleringer (uklare eller nølende uttrykk)<br>
        - Passiv form (setninger hvor subjektet ikke utfører handlingen)<br>
        Eksempel: 'Ballen ble kastet' vs 'Jan kastet ballen'<br>
        Begge kan gjøre teksten mindre direkte.
    """,
    "nonstandard": """
        <b>Ikke-standard talerverb</b><br>
        Indikerer uvanlige verb som beskriver tale<br>
        (i stedet for vanlige som 'sa').<br>
        For kreative verb kan forvirre leseren.
    """,
    "filter": """
        <b>Filterord</b><br>
        Markerer ord som svekker budskapet<br>
        (som 'bare', 'virkelig', 'bokstavelig talt').<br>
        Å fjerne dem vil styrke tekstens klarhet.
    """,
    "telling": """
        <b>Fortelling i stedet for visning</b><br>
        Fremhever deler hvor følelser eller handlinger er direkte oppgitt<br>
        i stedet for å vise dem gjennom beskrivelser eller handlinger.<br>
        Dette kan redusere leserens engasjement.
    """,
    "weak_verb": """
        <b>Svake verb</b><br>
        Markerer verb uten tydelig emosjonell ladning.<br>
        Å erstatte dem med sterkere synonymer vil gi liv til teksten.
    """,
    "overused": """
        <b>Overbrukte ord</b><br>
        Indikerer ord som gjentas for ofte.<br>
        Bruk synonymer eller endre setningsstrukturen for variasjon.
    """,
    "pronoun": """
        <b>Uklare pronomenreferanser</b><br>
        Markerer pronomen ('han', 'hun', 'det', 'de') med uklar kontekst.<br>
        Tydelig bruk av pronomen forhindrer misforståelser.
    """,
    "repetitive": """
        <b>Gjentakende setningsstarter</b><br>
        Indikerer sekvenser av setninger som begynner likt.<br>
        Variasjon i setningsstarter holder på leserens oppmerksomhet.
    """
}

NORWEGIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"av"},
    "weak_patterns": [r'\b\w+(?:e|t)\b'],
    "weak_terms": {"kanskje", "muligens", "sannsynligvis", "antagelig", "ser ut til", "som om", "litt", "noe"},
    "standard_speech_verbs": {"si", "spørre"},
    "speech_verbs": {"si", "spørre", "hviske", "rope", "mumle", "utbryte"},
    "filter_words": {"så", "hørte", "følte", "la merke til", "tenkte", "lurte på", "observerte", "kikket", "lyttet", "kjente", "bestemte", "vurderte", "syntes", "dukket opp", "iakttok", "oppfattet", "forestilte seg"},
    "telling_verbs": {"være", "føle", "virke", "se ut", "fremstå", "bli"},
    "emotion_words": {"sint", "trist", "glad", "begeistret", "nervøs", "redd", "bekymret", "flau", "skuffet", "frustrert", "irritert", "urolig", "skremt", "lykkelig", "nedtrykt", "ulykkelig", "henrykt", "opprørt", "rasende", "henrykt", "sjokkert", "overrasket", "forvirret", "stolt", "fornøyd", "tilfreds", "entusiastisk", "sjalu"},
    "weak_verbs": {"være"},
    "common_words": {"og", "i", "på", "med", "til", "om", "men", "eller", "som", "er", "var", "har", "dette", "den", "det", "de", "der", "her", "min", "din", "hans", "hennes", "vår", "deres", "seg", "ikke", "ja", "nei", "fordi", "når", "hvis", "siden", "hvilken", "hvilket"},
    "quote_pattern": r'«[^»]*»|"[^"]*"'
}

class NorwegianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "nb_core_news_sm", NORWEGIAN_DATA)
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
        msgBox.setText("The model 'nb_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('nb_core_news_sm')
            self.nlp = spacy.load('nb_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Norwegian using the LIX (Läsbarhetsindex/Lesbarhetsindeks).
        LIX is a readability measure commonly used for Scandinavian languages.
        
        Formula: LIX = A + B where:
        - A is the average sentence length (number of words / number of sentences)
        - B is the percentage of long words (words with more than 6 characters)
        
        Interpretation:
        - <30: Very easy
        - 30-40: Easy
        - 40-50: Medium
        - 50-60: Difficult
        - >60: Very difficult
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        
        # Count words with more than 6 characters
        num_long_words = sum(1 for word in words if len(word) > 6)
        
        if num_sentences == 0 or num_words == 0:
            return 0
            
        # Average sentence length
        avg_sentence_length = num_words / num_sentences
        
        # Percentage of long words
        percentage_long_words = (num_long_words / num_words) * 100
        
        # Calculate LIX
        lix = avg_sentence_length + percentage_long_words
        
        return lix
        
    def get_tooltips(self):
        """Returns tooltips in Norwegian."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Norwegian text analysis module.
    """
    global nlp
    analysis = NorwegianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = NorwegianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Norwegian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)