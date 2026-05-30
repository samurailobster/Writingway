#!/usr/bin/env python
"""
text_analysis_pl.py

Polish-specific text analysis module inheriting from BaseTextAnalysis.
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
        <b>Złożone zdania</b><br>
        Wyróżnia zdania bardzo długie lub o skomplikowanej strukturze, które mogą być trudne do zrozumienia.<br>
        Rozważ podzielenie ich na krótsze, bardziej przystępne zdania.
    """,
    "weak": """
        <b>Słabe sformułowania/strona bierna</b><br>
        Oznacza fragmenty tekstu z językiem nieprecyzyjnym lub mało stanowczym.<br>
        Obejmuje:<br>
        - Słabe sformułowania (niejasne lub niezdecydowane wyrażenia)<br>
        - Stronę bierną (zdania gdzie podmiot nie wykonuje akcji)<br>
        Przykład: 'Piłka została rzucona' vs 'Jan rzucił piłką'<br>
        Oba mogą sprawiać, że tekst jest mniej bezpośredni.
    """,
    "nonstandard": """
        <b>Niestandardowe czasowniki mówienia</b><br>
        Wskazuje nietypowe czasowniki opisujące mowę<br>
        (zamiast powszechnych jak 'powiedział').<br>
        Zbyt kreatywne czasowniki mogą dezorientować czytelnika.
    """,
    "filter": """
        <b>Słowa filtrujące</b><br>
        Oznacza słowa, które osłabiają przekaz<br>
        (jak 'właśnie', 'naprawdę', 'dosłownie').<br>
        Usunięcie ich wzmocni klarowność tekstu.
    """,
    "telling": """
        <b>Opowiadanie zamiast pokazywania</b><br>
        Wyróżnia fragmenty gdzie emocje lub akcje są podane wprost<br>
        zamiast pokazać je przez opisy lub działania.<br>
        To może zmniejszać zaangażowanie czytelnika.
    """,
    "weak_verb": """
        <b>Słabe czasowniki</b><br>
        Oznacza czasowniki bez wyraźnego ładunku emocjonalnego.<br>
        Zastąpienie ich mocniejszymi synonimami ożywi tekst.
    """,
    "overused": """
        <b>Nadużywane słowa</b><br>
        Wskazuje słowa powtarzające się zbyt często.<br>
        Użyj synonimów lub zmień szyk zdania dla urozmaicenia.
    """,
    "pronoun": """
        <b>Niejasne odniesienia zaimków</b><br>
        Oznacza zaimki ('on', 'ona', 'to', 'oni') z niejasnym kontekstem.<br>
        Jasne użycie zaimków zapobiega nieporozumieniom.
    """,
    "repetitive": """
        <b>Powtarzające się początki zdań</b><br>
        Wskazuje sekwencje zdań zaczynające się tak samo.<br>
        Różnorodność w rozpoczęciach zdań utrzymuje uwagę czytelnika.
    """
}

POLISH_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"przez"},
    "weak_patterns": [r'\b\w+(?:o|e)\b'],
    "weak_terms": {"może", "być może", "prawdopodobnie", "chyba", "wydaje się", "jakby", "trochę", "nieco"},
    "standard_speech_verbs": {"powiedzieć", "zapytać"},
    "speech_verbs": {"powiedzieć", "zapytać", "wyszeptać", "krzyknąć", "mruknąć", "wykrzyknąć"},
    "filter_words": {"widział", "słyszał", "czuł", "zauważył", "pomyślał", "zastanawiał się", "obserwował", "patrzył", "słuchał", "wyczuł", "zdecydował", "rozważał", "wydawało się", "pojawił się", "zaobserwował", "odczuł", "postrzegał", "wyobrażał sobie"},
    "telling_verbs": {"być", "czuć się", "wydawać się", "wyglądać", "pojawiać się", "stawać się"},
    "emotion_words": {"zły", "smutny", "szczęśliwy", "podekscytowany", "nerwowy", "przerażony", "zmartwiony", "zawstydzony", "rozczarowany", "sfrustrowany", "zirytowany", "niespokojny", "przestraszony", "radosny", "przygnębiony", "nieszczęśliwy", "ekstatyczny", "zdenerwowany", "wściekły", "zachwycony", "zszokowany", "zaskoczony", "zdezorientowany", "dumny", "zadowolony", "usatysfakcjonowany", "entuzjastyczny", "zazdrosny"},
    "weak_verbs": {"być"},
    "common_words": {"i", "w", "na", "z", "do", "o", "a", "ale", "lub", "jak", "jest", "są", "był", "była", "było", "ma", "mają", "to", "tego", "temu", "ten", "ta", "te", "tam", "tu", "mój", "twój", "jego", "jej", "nasz", "wasz", "ich", "się", "nie", "tak", "czy", "bo", "gdy", "jeśli", "ponieważ", "który", "która", "które"},
    "quote_pattern": r'„[^”]*”|\"[^\"]*\"'
}

class PolishTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "pl_core_news_sm", POLISH_DATA)
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
        msgBox.setText("The model 'pl_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('pl_core_news_sm')
            self.nlp = spacy.load('pl_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Polish using the Fog Index.
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        num_difficult_words = sum(1 for word in words if len(re.findall(r'[aeiouyąęó]', word.lower())) >= 3)
        if num_sentences == 0 or num_words == 0:
            return 0
        return 0.4 * ((num_words / num_sentences) + 100 * (num_difficult_words / num_words))
        
    def get_tooltips(self):
        """Returns tooltips in Polish."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Polish text analysis module.
    """
    global nlp
    analysis = PolishTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = PolishTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Polish spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
