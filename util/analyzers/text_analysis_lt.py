#!/usr/bin/env python
"""
text_analysis_lt.py

Lithuanian-specific text analysis module inheriting from BaseTextAnalysis.
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
        <b>Sudėtingi sakiniai</b><br>
        Paryškina labai ilgus arba sudėtingos struktūros sakinius, kuriuos gali būti sunku suprasti.<br>
        Apsvarstykite galimybę juos padalinti į trumpesnius, suprantamesnius sakinius.
    """,
    "weak": """
        <b>Silpnos formuluotės/pasyvas</b><br>
        Žymi teksto fragmentus su neapibrėžta arba netikslia kalba.<br>
        Apima:<br>
        - Silpnas formuluotes (neaiškius arba neapibrėžtus išsireiškimus)<br>
        - Pasyvinę balsą (sakinius, kuriuose veiksnys neatlieka veiksmo)<br>
        Pavyzdys: 'Kamuolys buvo mestas' vs 'Jonas metė kamuolį'<br>
        Abu gali padaryti tekstą mažiau tiesioginį.
    """,
    "nonstandard": """
        <b>Nestandartiniai kalbėjimo veiksmažodžiai</b><br>
        Nurodo neįprastus veiksmažodžius, apibūdinančius kalbą<br>
        (vietoj įprastų kaip 'pasakė').<br>
        Per daug kūrybingi veiksmažodžiai gali suklaidinti skaitytoją.
    """,
    "filter": """
        <b>Filtravimo žodžiai</b><br>
        Žymi žodžius, kurie silpnina pranešimą<br>
        (kaip 'tiesiog', 'tikrai', 'pažodžiui').<br>
        Jų pašalinimas sustiprins teksto aiškumą.
    """,
    "telling": """
        <b>Pasakojimas vietoj rodymo</b><br>
        Paryškina fragmentus, kur emocijos ar veiksmai yra tiesiogiai įvardijami<br>
        vietoj to, kad būtų parodomi per aprašymus ar veiksmus.<br>
        Tai gali sumažinti skaitytojo įsitraukimą.
    """,
    "weak_verb": """
        <b>Silpni veiksmažodžiai</b><br>
        Žymi veiksmažodžius be aiškaus emocinio krūvio.<br>
        Jų pakeitimas stipresniais sinonimais pagyvins tekstą.
    """,
    "overused": """
        <b>Per dažnai naudojami žodžiai</b><br>
        Nurodo žodžius, kurie kartojasi per dažnai.<br>
        Naudokite sinonimus arba keiskite sakinio struktūrą įvairovei.
    """,
    "pronoun": """
        <b>Neaiškūs įvardžių ryšiai</b><br>
        Žymi įvardžius ('jis', 'ji', 'tai', 'jie') su neaiškiu kontekstu.<br>
        Aiškus įvardžių vartojimas padeda išvengti nesusipratimų.
    """,
    "repetitive": """
        <b>Pasikartojančios sakinių pradžios</b><br>
        Nurodo sakinių sekas, prasidedančias vienodai.<br>
        Įvairovė sakinių pradžiose išlaiko skaitytojo dėmesį.
    """
}

LITHUANIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"per"},
    "weak_patterns": [r'\b\w+(?:o|e)\b'],
    "weak_terms": {"galbūt", "gali būti", "tikriausiai", "atrodo", "tarsi", "šiek tiek", "truputį"},
    "standard_speech_verbs": {"sakyti", "klausti"},
    "speech_verbs": {"sakyti", "klausti", "šnabždėti", "šaukti", "murmėti", "sušukti"},
    "filter_words": {"matė", "girdėjo", "jautė", "pastebėjo", "galvojo", "svarstė", "stebėjo", "žiūrėjo", "klausėsi", "užuodė", "nusprendė", "apsvarstė", "atrodė", "pasirodė", "pajuto", "suvokė", "įsivaizdavo"},
    "telling_verbs": {"būti", "jaustis", "atrodyti", "pasirodyti", "tapti"},
    "emotion_words": {"piktas", "liūdnas", "laimingas", "susijaudinęs", "nervingas", "išsigandęs", "susirūpinęs", "sugėdintas", "nusivylęs", "frustruotas", "suerzintas", "nerimastingas", "linksmas", "prislėgtas", "nelaimingas", "ekstaziškas", "įsiutęs", "sužavėtas", "šokiruotas", "nustebęs", "sutrikęs", "išdidus", "patenkintas", "pasitenkinęs", "entuziastingas", "pavydus"},
    "weak_verbs": {"būti"},
    "common_words": {"ir", "į", "ant", "iš", "su", "apie", "o", "bet", "arba", "kaip", "yra", "buvo", "turi", "tai", "to", "šis", "ši", "šie", "ten", "čia", "mano", "tavo", "jo", "jos", "mūsų", "jūsų", "jų", "ne", "taip", "ar", "nes", "kai", "jei", "kadangi", "kuris", "kuri", "kurie"},
    "quote_pattern": r'„[^"]*"|\"[^\"]*\"'
}

class LithuanianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "lt_core_news_sm", LITHUANIAN_DATA)
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
        msgBox.setText("The model 'lt_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('lt_core_news_sm')
            self.nlp = spacy.load('lt_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Lithuanian using an adapted version of the Fog Index
        (Indeksas skaitymo suprantamumui).
        
        The formula is adjusted to account for Lithuanian language specifics:
        - Longer average words in Lithuanian compared to English
        - Different syllable structure
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)

        # For Lithuanian, consider words with 4+ syllables as complex (adjusted from 3 for Polish)
        # Lithuanian has longer words on average
        vowels = 'aeiouyąęėįųū'
        num_difficult_words = sum(1 for word in words if len(re.findall(f'[{vowels}]', word.lower())) >= 4)

        if num_sentences == 0 or num_words == 0:
            return 0

        # Modified coefficient (0.4 to 0.35) to better reflect Lithuanian language characteristics
        return 0.35 * ((num_words / num_sentences) + 100 * (num_difficult_words / num_words))

    def get_tooltips(self):
        """Returns tooltips in Lithuanian."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Lithuanian text analysis module.
    """
    global nlp
    analysis = LithuanianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = LithuanianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Lithuanian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
