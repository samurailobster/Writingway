#!/usr/bin/env python
"""
text_analysis_nl.py

Dutch-specific text analysis module inheriting from BaseTextAnalysis.
"""

import math
import re
import threading

import spacy
import spacy.cli
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from util.base_text_analysis import BaseTextAnalysis

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Complexe zinnen</b><br>
        Markeert zeer lange of ingewikkeld gestructureerde zinnen die moeilijk te begrijpen kunnen zijn.<br>
        Overweeg om ze op te splitsen in kortere, meer toegankelijke zinnen.
    """,
    "weak": """
        <b>Zwakke formuleringen/passieve stem</b><br>
        Wijst tekstfragmenten aan met onnauwkeurige of aarzelende taal.<br>
        Omvat:<br>
        - Zwakke formuleringen (vage of besluiteloze uitdrukkingen)<br>
        - Passieve stem (zinnen waarin het onderwerp niet de handeling uitvoert)<br>
        Voorbeeld: 'De bal werd gegooid' vs 'Jan gooide de bal'<br>
        Beide kunnen tekst minder direct maken.
    """,
    "nonstandard": """
        <b>Niet-standaard sprekende werkwoorden</b><br>
        Wijst op ongebruikelijke werkwoorden die spraak beschrijven<br>
        (in plaats van veelvoorkomende zoals 'zei').<br>
        Te creatieve werkwoorden kunnen de lezer in verwarring brengen.
    """,
    "filter": """
        <b>Filterwoorden</b><br>
        Wijst op woorden die de boodschap verzwakken<br>
        (zoals 'eigenlijk', 'echt', 'letterlijk').<br>
        Het verwijderen ervan zal de duidelijkheid van de tekst versterken.
    """,
    "telling": """
        <b>Vertellen in plaats van tonen</b><br>
        Markeert fragmenten waar emoties of acties direct worden benoemd<br>
        in plaats van ze te tonen door beschrijvingen of handelingen.<br>
        Dit kan de betrokkenheid van de lezer verminderen.
    """,
    "weak_verb": """
        <b>Zwakke werkwoorden</b><br>
        Wijst op werkwoorden zonder duidelijke emotionele lading.<br>
        Door ze te vervangen door sterkere synoniemen wordt de tekst levendiger.
    """,
    "overused": """
        <b>Overgebruikte woorden</b><br>
        Wijst op woorden die te vaak voorkomen.<br>
        Gebruik synoniemen of herstructureer zinnen voor meer variatie.
    """,
    "pronoun": """
        <b>Onduidelijke verwijzingen met voornaamwoorden</b><br>
        Wijst op voornaamwoorden ('hij', 'zij', 'het', 'zij') met onduidelijke context.<br>
        Duidelijk gebruik van voornaamwoorden voorkomt misverstanden.
    """,
    "repetitive": """
        <b>Herhalende zinsbeginnen</b><br>
        Wijst op reeksen zinnen die op dezelfde manier beginnen.<br>
        Variatie in zinsbeginnen houdt de aandacht van de lezer vast.
    """
}

DUTCH_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"door"},
    "weak_patterns": [r'\b\w+(?:lijk|ig)\b'],
    "weak_terms": {"misschien", "wellicht", "mogelijk", "waarschijnlijk", "lijkt", "enigszins", "beetje", "tamelijk"},
    "standard_speech_verbs": {"zeggen", "vragen"},
    "speech_verbs": {"zeggen", "vragen", "fluisteren", "schreeuwen", "mompelen", "uitroepen"},
    "filter_words": {"zien", "horen", "voelen", "opmerken", "denken", "overwegen", "observeren", "kijken", "luisteren", "waarnemen", "beslissen", "lijken", "verschijnen", "ervaren", "voorstellen"},
    "telling_verbs": {"zijn", "voelen", "lijken", "eruitzien", "verschijnen", "worden"},
    "emotion_words": {"boos", "verdrietig", "blij", "opgewonden", "zenuwachtig", "doodsbang", "bezorgd", "beschaamd", "teleurgesteld", "gefrustreerd", "geïrriteerd", "rusteloos", "bang", "vrolijk", "somber", "ongelukkig", "extatisch", "overstuur", "woedend", "verrukt", "geschokt", "verrast", "verward", "trots", "tevreden", "voldaan", "enthousiast", "jaloers"},
    "weak_verbs": {"zijn", "hebben"},
    "common_words": {"en", "in", "op", "van", "naar", "over", "maar", "of", "als", "is", "zijn", "was", "waren", "heeft", "hebben", "dit", "dat", "deze", "die", "hier", "daar", "mijn", "jouw", "haar", "onze", "jullie", "hun", "zich", "niet", "ja", "nee", "omdat", "wanneer", "want", "wie", "wat", "welke"},
    "quote_pattern": r'„[^"]*"|\"[^\"]*\"'
}

class DutchTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "nl_core_news_sm", DUTCH_DATA)
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
        msgBox.setText("The model 'nl_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('nl_core_news_sm')
            self.nlp = spacy.load('nl_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Dutch using the Flesch-Douma Index.
        
        This is an adaptation of the Flesch Reading Ease formula for Dutch language:
        Flesch-Douma = 206.84 - (0.77 * average sentence length in words) - (93 * average word length in syllables)
        
        Higher scores indicate easier readability:
        90-100: Very easy
        80-90: Easy
        70-80: Fairly easy
        60-70: Standard
        50-60: Fairly difficult
        30-50: Difficult
        0-30: Very difficult
        """
        # Count words
        words = text.split()
        num_words = len(words)

        # Count sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)

        # Estimate syllables (Dutch syllable counting is complex, this is a simplification)
        vowels = 'aeiouyàáâäéèêëïìîíòóôöùúûü'
        def count_syllables(word):
            word = word.lower()
            count = 0
            prev_is_vowel = False

            for char in word:
                is_vowel = char in vowels
                if is_vowel and not prev_is_vowel:
                    count += 1
                prev_is_vowel = is_vowel

            # Handle common Dutch silent 'e' at end of words
            if word.endswith('e') and count > 1:
                count -= 0.5

            return max(1, math.ceil(count))  # Every word has at least one syllable

        total_syllables = sum(count_syllables(word) for word in words)

        # Calculate metrics
        if num_sentences == 0 or num_words == 0:
            return 0

        avg_sentence_length = num_words / num_sentences
        avg_syllables_per_word = total_syllables / num_words

        # Flesch-Douma formula
        readability = 206.84 - (0.77 * avg_sentence_length) - (93 * avg_syllables_per_word)

        # Clamp the result to 0-100 range
        return max(0, min(100, readability))

    def get_tooltips(self):
        """Returns tooltips in Dutch."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Dutch text analysis module.
    """
    global nlp
    analysis = DutchTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = DutchTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Dutch spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
