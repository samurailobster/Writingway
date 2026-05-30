#!/usr/bin/env python
"""
text_analysis_fi.py

Finnish-specific text analysis module inheriting from BaseTextAnalysis.
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
        <b>Monimutkaiset lauseet</b><br>
        Korostaa erittäin pitkiä tai rakenteeltaan monimutkaisia lauseita, jotka voivat olla vaikeita ymmärtää.<br>
        Harkitse niiden jakamista lyhyempiin, helpommin lähestyttäviin lauseisiin.
    """,
    "weak": """
        <b>Heikot ilmaisut/passiivi</b><br>
        Osoittaa epätarkkaa tai vähemmän vakuuttavaa kieltä.<br>
        Sisältää:<br>
        - Heikot ilmaisut (epäselvät tai epävarmat ilmaukset)<br>
        - Passiivi (lauseet, joissa tekijä ei suorita toimintaa)<br>
        Esimerkki: 'Pallo heitettiin' vs 'Matti heitti pallon'<br>
        Molemmat voivat tehdä tekstistä vähemmän suoraa.
    """,
    "nonstandard": """
        <b>Epätavalliset puhumisen verbit</b><br>
        Ilmaisee epätyypillisiä puhetta kuvaavia verbejä<br>
        (yleisten kuten 'sanoi' sijaan).<br>
        Liian luovat verbit voivat hämmentää lukijaa.
    """,
    "filter": """
        <b>Suodatinsanat</b><br>
        Osoittaa sanoja, jotka heikentävät viestiä<br>
        (kuten 'juuri', 'todella', 'kirjaimellisesti').<br>
        Niiden poistaminen parantaa tekstin selkeyttä.
    """,
    "telling": """
        <b>Kertominen näyttämisen sijaan</b><br>
        Korostaa kohtia, joissa tunteet tai toiminta ilmaistaan suoraan<br>
        sen sijaan, että ne näytettäisiin kuvausten tai toiminnan kautta.<br>
        Tämä voi vähentää lukijan sitoutumista.
    """,
    "weak_verb": """
        <b>Heikot verbit</b><br>
        Osoittaa verbejä ilman selkeää tunnelataa.<br>
        Niiden korvaaminen vahvemmilla synonyymeillä elävöittää tekstiä.
    """,
    "overused": """
        <b>Liikakäytetyt sanat</b><br>
        Osoittaa sanoja, jotka toistuvat liian usein.<br>
        Käytä synonyymejä tai muuta lauserakennetta monipuolisuuden vuoksi.
    """,
    "pronoun": """
        <b>Epäselvät pronominit</b><br>
        Osoittaa pronominit ('hän', 'se', 'ne'), joilla on epäselvä konteksti.<br>
        Pronominien selkeä käyttö estää väärinymmärryksiä.
    """,
    "repetitive": """
        <b>Toistuvat lauseiden alut</b><br>
        Osoittaa peräkkäisiä lauseita, jotka alkavat samalla tavalla.<br>
        Vaihtelevat lauseiden alut pitävät lukijan mielenkiintoa yllä.
    """
}

FINNISH_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"toimesta"},
    "weak_patterns": [r'\b\w+(?:a|än)\b'],
    "weak_terms": {"ehkä", "mahdollisesti", "todennäköisesti", "luultavasti", "vaikuttaa siltä", "kuin", "hieman", "jonkin verran"},
    "standard_speech_verbs": {"sanoa", "kysyä"},
    "speech_verbs": {"sanoa", "kysyä", "kuiskata", "huutaa", "mumista", "karjaista"},
    "filter_words": {"näki", "kuuli", "tunsi", "huomasi", "ajatteli", "mietti", "tarkkaili", "katsoi", "kuunteli", "aisti", "päätti", "harkitsi", "tuntui", "ilmestyi", "havaitsi", "koki", "käsitti", "kuvitteli"},
    "telling_verbs": {"olla", "tuntea", "vaikuttaa", "näyttää", "ilmestyä", "tulla"},
    "emotion_words": {"vihainen", "surullinen", "onnellinen", "innostunut", "hermostunut", "kauhistunut", "huolestunut", "häpeissään", "pettynyt", "turhautunut", "ärsyyntynyt", "levoton", "peloissaan", "iloinen", "masentunut", "onneton", "ekstaattinen", "hermostunut", "raivoissaan", "ihastunut", "järkyttynyt", "yllättynyt", "hämmentynyt", "ylpeä", "tyytyväinen", "tyydyttynyt", "innostunut", "kateellinen"},
    "weak_verbs": {"olla"},
    "common_words": {"ja", "että", "on", "ei", "hän", "se", "ovat", "oli", "olivat", "mutta", "tai", "kun", "jos", "koska", "mikä", "joka", "tämä", "nämä", "tuo", "nuo", "minun", "sinun", "hänen", "meidän", "teidän", "heidän", "ei", "kyllä", "miksi", "missä", "milloin", "miten", "kuka"},
    "quote_pattern": r'"[^"]*"|\"[^\"]*\"'
}

class FinnishTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "fi_core_news_sm", FINNISH_DATA)
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
        msgBox.setText("The model 'fi_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('fi_core_news_sm')
            self.nlp = spacy.load('fi_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Finnish using the LIX formula (Läsbarhetsindex).
        
        LIX is adapted for Finnish as it works well for other Nordic languages. The formula is:
        LIX = A/B + (C*100)/A
        where:
        A = number of words
        B = number of sentences
        C = number of long words (>6 characters)
        
        Lower values indicate easier texts.
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        num_long_words = sum(1 for word in words if len(word) > 6)
        
        if num_sentences == 0 or num_words == 0:
            return 0
            
        return (num_words / num_sentences) + (num_long_words * 100 / num_words)
        
    def get_tooltips(self):
        """Returns tooltips in Finnish."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Finnish text analysis module.
    """
    global nlp
    analysis = FinnishTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = FinnishTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Finnish spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)