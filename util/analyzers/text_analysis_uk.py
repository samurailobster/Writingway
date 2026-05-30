#!/usr/bin/env python
"""
text_analysis_uk.py

Ukrainian-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis
import re

# Ukrainian tooltip translations
TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Складні речення</b><br>
        Виділяє речення, які є дуже довгими або мають складну структуру, що може ускладнювати розуміння.<br>
        Розгляньте можливість поділу їх на коротші, більш доступні речення.
    """,
    "weak": """
        <b>Слабкі формулювання/пасивний стан</b><br>
        Вказує на фрагменти тексту з нечіткою або невиразною мовою.<br>
        Охоплює:<br>
        - Слабкі формулювання (недостатньо точні або нерішучі вирази)<br>
        - Пасивний стан (речення, де підмет не виконує дію)<br>
        Приклад: 'М'яч був кинутий' проти 'Іван кинув м'яч'<br>
        Обидва можуть робити текст менш прямим.
    """,
    "nonstandard": """
        <b>Нестандартні дієслова мовлення</b><br>
        Вказує на нетипові дієслова, що описують мовлення<br>
        (замість загальноприйнятих, як 'сказав').<br>
        Надто креативні дієслова можуть дезорієнтувати читача.
    """,
    "filter": """
        <b>Фільтруючі слова</b><br>
        Вказує на слова, які ослаблюють послання<br>
        (такі як 'саме', 'справді', 'буквально').<br>
        Їх видалення посилить ясність тексту.
    """,
    "telling": """
        <b>Оповідання замість показу</b><br>
        Виділяє фрагменти, де емоції або дії подані напряму<br>
        замість того, щоб показувати їх через описи або дії.<br>
        Це може знижувати залученість читача.
    """,
    "weak_verb": """
        <b>Слабкі дієслова</b><br>
        Вказує на дієслова без вираженого емоційного навантаження.<br>
        Замініть їх на сильніші синоніми для оживлення тексту.
    """,
    "overused": """
        <b>Надмірно вживані слова</b><br>
        Вказує на слова, що повторюються занадто часто.<br>
        Використовуйте синоніми або змініть порядок слів для урізноманітнення.
    """,
    "pronoun": """
        <b>Незрозумілі посилання займенників</b><br>
        Вказує на займенники ('він', 'вона', 'це', 'вони') без чіткого контексту.<br>
        Чітке вживання займенників запобігає непорозумінням.
    """,
    "repetitive": """
        <b>Повторювані початки речень</b><br>
        Вказує на послідовності речень, які починаються однаково.<br>
        Різноманітність початків речень утримує увагу читача.
    """
}

# Ukrainian-specific data
UKRAINIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"за"},
    "weak_patterns": [r'\b\w+(?:о|е)\b'],
    "weak_terms": {"може", "можливо", "ймовірно", "напевно", "схоже", "як ніби", "трохи", "дещо"},
    "standard_speech_verbs": {"сказати", "запитати"},
    "speech_verbs": {"сказати", "запитати", "шепотіти", "закричати", "бурмотіти", "вигукнути"},
    "filter_words": {"бачив", "чуяв", "відчував", "зауважив", "подумав", "розмірковував", "здавалось", "з'явився", "спостерігав", "дивився", "слухав", "відчув", "вирішив", "розглядав", "здалося", "з'явилося", "помітив", "відчував", "восприймав", "уявляв собі"},
    "telling_verbs": {"бути", "відчувати себе", "здаватися", "виглядати", "з'являтися", "ставати"},
    "emotion_words": {"злий", "сумний", "щасливий", "збуджений", "нервовий", "переляканий", "схвильований", "сором'язливий", "розчарований", "розлючений", "тривожний", "зляканий", "радісний", "пригнічений", "невдоволений", "екстатичний", "знервований", "розгніваний", "захоплений", "приголомшений", "здивований", "спантеличений", "гордий", "задоволений", "вдоволений", "ентузіастичний", "заздрісний"},
    "weak_verbs": {"бути"},
    "common_words": {"і", "в", "на", "з", "до", "про", "але", "або", "як", "є", "був", "була", "було", "має", "мають", "це", "цього", "цьому", "цей", "ця", "ці", "там", "тут", "мій", "твій", "його", "її", "наш", "ваш", "їх", "себе", "не", "так", "чи", "бо", "коли", "якщо", "тому що", "який", "яка", "яке"},
    "quote_pattern": r'«[^»]*»|\"[^\"]*\"'
}

class UkrainianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "uk_core_news_sm", UKRAINIAN_DATA)
        QObject.__init__(self)
        self.download_in_progress = False

    def initialize(self):
        """
        Initializes the spaCy model for Ukrainian. If the model is not found, prompts the user to download it.
        """
        if super().initialize():
            return True
        if not self.download_in_progress and self.ask_for_download():
            self.download_in_progress = True
            threading.Thread(target=self.download_and_load_model, daemon=True).start()
        return False

    def ask_for_download(self):
        """
        Asks the user if they want to download the missing spaCy model for Ukrainian.
        """
        msgBox = QMessageBox()
        msgBox.setWindowTitle("spaCy Model")
        msgBox.setText("Не знайдено модель 'uk_core_news_sm'. Бажаєте завантажити її?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model for Ukrainian and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('uk_core_news_sm')
            self.nlp = spacy.load('uk_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Помилка під час завантаження моделі: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Ukrainian text using the Flesch Reading Ease formula adapted for Ukrainian.
        Formula: 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
        This is a naive approximation serving as the Індекс читабельності.
        """
        words = text.split()
        num_words = len(words)
        # Split text into sentences using punctuation as delimiters
        sentences = re.split(r'[.!?…]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)

        # Define Ukrainian vowels
        vowels = "аеєиіїоуюя"
        syllable_count = 0
        for word in words:
            # Count vowels in each word as a rough estimate of syllables
            syllable_count += sum(1 for char in word.lower() if char in vowels)
        
        if num_sentences == 0 or num_words == 0:
            return 0
        reading_ease = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (syllable_count / num_words)
        return reading_ease
        
    def get_tooltips(self):
        """Returns tooltips in Ukrainian."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Ukrainian text analysis module.
    """
    global nlp
    analysis = UkrainianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given Ukrainian text.
    """
    analysis = UkrainianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Ukrainian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
