#!/usr/bin/env python
"""
text_analysis_hr.py

Croatian-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
import re
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis

# Tooltip translations in Croatian
TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Složene rečenice</b><br>
        Ističe rečenice koje su vrlo duge ili imaju složenu strukturu, što ih može učiniti teškim za razumijevanje.<br>
        Razmislite o njihovom dijeljenju u kraće, pristupačnije rečenice.
    """,
    "weak": """
        <b>Slabiji izrazi/pasivni glas</b><br>
        Označava dijelove teksta s neodređenim ili neodlučnim jezikom.<br>
        Obuhvaća:<br>
        - Slabe izraze (nejasni ili neodlučni izrazi)<br>
        - Pasivni glas (rečenice u kojima subjekt ne izvršava radnju)<br>
        Primjer: 'Lopta je bačena' vs 'Ivan je bacio loptu'<br>
        Oba mogu učiniti tekst manje direktnim.
    """,
    "nonstandard": """
        <b>Nestandardni glagoli govora</b><br>
        Označava neuobičajene glagole za govor<br>
        (umjesto uobičajenih poput 'rekao').<br>
        Previše kreativni glagoli mogu zbuniti čitatelja.
    """,
    "filter": """
        <b>Filter riječi</b><br>
        Označava riječi koje slabe poruku<br>
        (poput 'upravo', 'stvarno', 'doslovno').<br>
        Njihovo uklanjanje može poboljšati jasnoću teksta.
    """,
    "telling": """
        <b>Opisivanje umjesto prikazivanja</b><br>
        Ističe dijelove gdje su emocije ili radnje izravno navedene<br>
        umjesto prikazivanja kroz opise ili akcije.<br>
        To može smanjiti angažman čitatelja.
    """,
    "weak_verb": """
        <b>Slabi glagoli</b><br>
        Označava glagole bez izraženog emocionalnog naboja.<br>
        Zamjena s jačim sinonimima može oživjeti tekst.
    """,
    "overused": """
        <b>Prečesto korištene riječi</b><br>
        Označava riječi koje se previše ponavljaju.<br>
        Koristite sinonime ili promijenite strukturu rečenice za raznolikost.
    """,
    "pronoun": """
        <b>Nedovoljno jasni zamjenice</b><br>
        Označava zamjenice ('on', 'ona', 'to', 'oni') s nejasnim kontekstom.<br>
        Jasno korištenje zamjenica sprječava nesporazume.
    """,
    "repetitive": """
        <b>Ponavljajući početci rečenica</b><br>
        Označava niz rečenica koje započinju na isti način.<br>
        Raznolikost početaka rečenica održava pažnju čitatelja.
    """
}

# Croatian-specific linguistic data
CROATIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"od"},
    "weak_patterns": [r'\b\w+(?:o|e)\b'],
    "weak_terms": {"možda", "vjerojatno", "čini se", "kao da", "malo"},
    "standard_speech_verbs": {"reći", "pitati"},
    "speech_verbs": {"reći", "pitati", "šaptati", "viknuti", "mrmljati", "uzviknuti"},
    "filter_words": {"vidio", "čuo", "osjetio", "primijetio", "pomislio", "razmišljao", "gledao", "slušao"},
    "telling_verbs": {"biti", "osjećati se", "činiti se", "izgledati", "pojavljivati se", "postati"},
    "emotion_words": {"ljut", "tužan", "sretan", "uzbuđen", "nervozan", "uplašen", "zabrinut", "posramljen", "razočaran", "frustriran", "irritiran", "nemiran", "preplašen", "radostan", "depresivan", "nesretan", "ekstatičan", "uznemiren", "bijesan", "oduševljen", "šokiran", "iznenađen", "zbunjen", "ponosan", "zadovoljan", "entuzijastičan", "zavidan"},
    "weak_verbs": {"biti"},
    "common_words": {"i", "u", "na", "s", "do", "o", "a", "ali", "ili", "kako", "je", "su", "bio", "bila", "bilo", "ima", "imaju", "to", "ovaj", "ta", "ti", "tamo", "ovdje", "moj", "tvoj", "njegov", "njena", "naš", "vaš", "njih", "se", "ne", "da", "jer", "ako", "koji", "koja", "koje"},
    "quote_pattern": r'„[^”]*”|\"[^\"]*\"'
}


class CroatianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "hr_core_news_sm", CROATIAN_DATA)
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
        msgBox.setText("The model 'hr_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('hr_core_news_sm')
            self.nlp = spacy.load('hr_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability (Indeks čitljivosti) for Croatian using an adaptation of the Flesch Reading Ease formula.
        
        Note: This is a rough approximation based on:
              RE = 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
        where syllables are approximated by counting vowel groups.
        """
        # Find words using a simple regex
        words = re.findall(r'\w+', text)
        num_words = len(words)
        # Split text into sentences by common punctuation marks
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        num_sentences = len(sentences)
        if num_sentences == 0 or num_words == 0:
            return 0
        syllable_count = 0
        # Approximate syllable count by counting contiguous groups of vowels
        for word in words:
            syllable_count += len(re.findall(r'[aeiouAEIOU]+', word))
        # Apply Flesch Reading Ease formula
        re_score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (syllable_count / num_words)
        return re_score

    def get_tooltips(self):
        """Returns tooltips in Croatian."""
        return TOOLTIP_TRANSLATIONS


nlp = None

def initialize():
    """
    Initializes the Croatian text analysis module.
    """
    global nlp
    analysis = CroatianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = CroatianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Croatian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
