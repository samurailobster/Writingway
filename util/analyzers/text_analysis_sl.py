#!/usr/bin/env python
"""
text_analysis_sl.py

Slovenian-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
import re
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis

# Translated tooltips in Slovenian
TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Sestavljeni stavki</b><br>
        Poudarja stavke, ki so zelo dolgi ali imajo zapleteno strukturo, kar jih lahko naredi težke za razumevanje.<br>
        Razmislite o razdelitvi na krajše, bolj razumljive stavke.
    """,
    "weak": """
        <b>Šibke formulacije/pasivni glas</b><br>
        Označuje dele besedila z nejasnim ali premalo odločenim jezikom.<br>
        Vključuje:<br>
        - Šibke formulacije (nejasni ali neodločeni izrazi)<br>
        - Pasivni glas (stavki, kjer subjekt ne izvaja dejanja)<br>
        Primer: 'Žoga je bila vržena' vs 'Jan je vrgel žogo'<br>
        Oba lahko povzročata manj neposreden tekst.
    """,
    "nonstandard": """
        <b>Nestandarden glagoli govora</b><br>
        Poudarja netipične glagole, ki opisujejo govor<br>
        (namesto običajnih, kot 'rekel').<br>
        Preveč kreativni glagoli lahko zmedejo bralca.
    """,
    "filter": """
        <b>Filtrirajoče besede</b><br>
        Označuje besede, ki oslabijo sporočilo<br>
        (npr. 'ravno', 'resnično', 'dobesedno').<br>
        Njihovo odstranitev bo izboljšala jasnost besedila.
    """,
    "telling": """
        <b>Pripovedovanje namesto prikazovanja</b><br>
        Poudarja dele, kjer so čustva ali dejanja neposredno podana<br>
        namesto da bi jih prikazali preko opisov ali dejanj.<br>
        To lahko zmanjša angažiranost bralca.
    """,
    "weak_verb": """
        <b>Šibki glagoli</b><br>
        Označuje glagole brez izrazitega čustvenega naboja.<br>
        Njihova zamenjava z močnejšimi sinonimi lahko oživi besedilo.
    """,
    "overused": """
        <b>Pretirano uporabljene besede</b><br>
        Poudarja besede, ki se preveč ponavljajo.<br>
        Uporabite sopomenke ali spremenite strukturo stavka za raznolikost.
    """,
    "pronoun": """
        <b>Neprecizno sklicevanje zaimkov</b><br>
        Označuje zaimke ('on', 'ona', 'to', 'oni') z nejasnim kontekstom.<br>
        Jasna raba zaimkov preprečuje nesporazume.
    """,
    "repetitive": """
        <b>Ponovljeni začetki stavkov</b><br>
        Poudarja zaporedja stavkov, ki se začnejo enako.<br>
        Raznolikost v začetkih stavkov ohranja pozornost bralca.
    """
}

# Slovenian linguistic data
SLOVENIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"od"},  # v slovenščini agent pasivnih stavkov je označen z "od"
    "weak_patterns": [r'\b\w+(?:a|o)\b'],  # primer preprostega vzorca (po potrebi prilagodite)
    "weak_terms": {"morda", "mogoče", "verjetno", "nekaj"},
    "standard_speech_verbs": {"reči", "vprašati"},
    "speech_verbs": {"reči", "vprašati", "povedati", "izjaviti", "šepetati", "zakričati"},
    "filter_words": {"videl", "slišal", "občutil", "opazil", "mislil", "spraševal", "ugotavljal", "gledal", "slušal"},
    "telling_verbs": {"biti", "počutiti se", "zdijo se", "izgledati", "pojavljati se", "postajati"},
    "emotion_words": {"jezen", "žalosten", "srečen", "navdušen", "zaskrbljen", "vznemirjen", "presenečen", "osupel", "razočaran"},
    "weak_verbs": {"biti"},
    "common_words": {"in", "v", "na", "z", "do", "o", "a", "ali", "kot", "je", "so", "bil", "bila", "bilo", "ima", "imajo", "to", "tega", "temu", "ta", "ti", "tam", "tu", "moj", "tvoj", "njegov", "njena", "naš", "vaš", "njih"},
    "quote_pattern": r'„[^”]*”|\"[^\"]*\"'
}


class SlovenianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "sl_core_news_sm", SLOVENIAN_DATA)
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
        msgBox.setText("The model 'sl_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('sl_core_news_sm')
            self.nlp = spacy.load('sl_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Slovenian using a variant of the Fog Index,
        here called the 'Slovenski indeks berljivosti'.
        
        The formula is:
            0.4 * ((words per sentence) + 100 * (difficult words / total words))
            
        A word is considered 'difficult' if it contains 3 or more vowels (a, e, i, o, u).
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        num_difficult_words = sum(
            1 for word in words if len(re.findall(r'[aeiou]', word.lower())) >= 3
        )
        if num_sentences == 0 or num_words == 0:
            return 0
        return 0.4 * ((num_words / num_sentences) + 100 * (num_difficult_words / num_words))

    def get_tooltips(self):
        """Returns tooltips in Slovenian."""
        return TOOLTIP_TRANSLATIONS


# Global variable for the spaCy language model
nlp = None

def initialize():
    """
    Initializes the Slovenian text analysis module.
    """
    global nlp
    analysis = SlovenianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = SlovenianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("The Slovenian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
