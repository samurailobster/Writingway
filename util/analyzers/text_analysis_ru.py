#!/usr/bin/env python
"""
text_analysis_ru.py

Russian-specific text analysis module inheriting from BaseTextAnalysis.
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
        <b>Сложные предложения</b><br>
        Выделяет очень длинные или структурно сложные предложения, которые могут быть трудны для понимания.<br>
        Рассмотрите возможность разделения их на более короткие, более доступные предложения.
    """,
    "weak": """
        <b>Слабые формулировки/пассивный залог</b><br>
        Обозначает фрагменты текста с неточным или нерешительным языком.<br>
        Включает:<br>
        - Слабые формулировки (неясные или нерешительные выражения)<br>
        - Пассивный залог (предложения, где субъект не выполняет действие)<br>
        Пример: 'Мяч был брошен' против 'Иван бросил мяч'<br>
        Оба могут делать текст менее прямым.
    """,
    "nonstandard": """
        <b>Нестандартные глаголы речи</b><br>
        Указывает на нетипичные глаголы, описывающие речь<br>
        (вместо обычных, как 'сказал').<br>
        Слишком творческие глаголы могут дезориентировать читателя.
    """,
    "filter": """
        <b>Фильтрующие слова</b><br>
        Обозначает слова, которые ослабляют сообщение<br>
        (как 'просто', 'действительно', 'буквально').<br>
        Удаление их усилит ясность текста.
    """,
    "telling": """
        <b>Рассказывание вместо показа</b><br>
        Выделяет фрагменты, где эмоции или действия представлены напрямую<br>
        вместо того, чтобы показать их через описания или действия.<br>
        Это может уменьшить вовлеченность читателя.
    """,
    "weak_verb": """
        <b>Слабые глаголы</b><br>
        Обозначает глаголы без выраженного эмоционального заряда.<br>
        Замена их более сильными синонимами оживит текст.
    """,
    "overused": """
        <b>Часто используемые слова</b><br>
        Указывает на слова, повторяющиеся слишком часто.<br>
        Используйте синонимы или измените структуру предложения для разнообразия.
    """,
    "pronoun": """
        <b>Неясные местоименные ссылки</b><br>
        Обозначает местоимения ('он', 'она', 'это', 'они') с неясным контекстом.<br>
        Ясное использование местоимений предотвращает недоразумения.
    """,
    "repetitive": """
        <b>Повторяющиеся начала предложений</b><br>
        Указывает на последовательности предложений, начинающихся одинаково.<br>
        Разнообразие в начале предложений удерживает внимание читателя.
    """
}

RUSSIAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"от", "с помощью"},
    "weak_patterns": [r'\b\w+(?:о|е)\b'],
    "weak_terms": {"может быть", "возможно", "вероятно", "кажется", "как будто", "немного", "несколько"},
    "standard_speech_verbs": {"сказать", "спросить"},
    "speech_verbs": {"сказать", "спросить", "прошептать", "крикнуть", "пробормотать", "воскликнуть"},
    "filter_words": {"видел", "слышал", "чувствовал", "заметил", "подумал", "задумался", "наблюдал", "смотрел", "слушал", "ощущал", "решил", "рассматривал", "казалось", "появился", "наблюдаемый", "почувствовал", "воспринимал", "воображал"},
    "telling_verbs": {"быть", "чувствовать", "казаться", "выглядеть", "появляться", "становиться"},
    "emotion_words": {"злой", "грустный", "счастливый", "взволнованный", "нервный", "испуганный", "обеспокоенный", "смущенный", "разочарованный", "расстроенный", "раздраженный", "тревожный", "напуганный", "радостный", "подавленный", "несчастный", "восторженный", "яростный", "восхищенный", "шокированный", "удивленный", "сбитый с толку", "гордый", "довольный", "удовлетворенный", "завистливый"},
    "weak_verbs": {"быть"},
    "common_words": {"и", "в", "на", "с", "к", "о", "а", "но", "или", "как", "есть", "суть", "был", "была", "было", "имеет", "имеют", "это", "этого", "этому", "этот", "эта", "эти", "там", "здесь", "мой", "твой", "его", "её", "наш", "ваш", "их", "себя", "не", "так", "ли", "потому", "когда", "если", "поскольку", "который", "которая", "которое"},
    "quote_pattern": r'«[^»]*»|\"[^\"]*\"'
}

class RussianTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "ru_core_news_sm", RUSSIAN_DATA)
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
        msgBox.setText("The model 'ru_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('ru_core_news_sm')
            self.nlp = spacy.load('ru_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Russian using the adapted Flesch Reading Ease formula.
        
        The formula is: 206.835 - (1.3 * ASL) - (60.1 * ASW)
        where:
        - ASL = average sentence length (number of words / number of sentences)
        - ASW = average syllables per word (number of syllables / number of words)
        
        Adapted for Russian language specifics.
        """
        # Split text into words and sentences
        words = re.findall(r'\b\w+\b', text.lower())
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]

        # Count words and sentences
        num_words = len(words)
        num_sentences = len(sentences)

        # Count syllables (approximation for Russian)
        vowels = 'аеёиоуыэюя'
        syllable_count = 0
        for word in words:
            count = sum(1 for char in word if char in vowels)
            # Ensure each word has at least one syllable
            syllable_count += max(1, count)

        # Avoid division by zero
        if num_sentences == 0 or num_words == 0:
            return 0

        # Calculate average sentence length and average syllables per word
        asl = num_words / num_sentences
        asw = syllable_count / num_words

        # Calculate Flesch Reading Ease adapted for Russian
        flesch_score = 206.835 - (1.3 * asl) - (60.1 * asw)

        # Ensure score is in the usual range (0-100)
        return max(0, min(100, flesch_score))

    def get_tooltips(self):
        """Returns tooltips in Russian."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Russian text analysis module.
    """
    global nlp
    analysis = RussianTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = RussianTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Russian spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
