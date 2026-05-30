#!/usr/bin/env python
"""
text_analysis_ko.py

Korean-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis
import re
import math

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>복잡한 문장</b><br>
        매우 길거나 복잡한 구조의 문장을 강조합니다. 이러한 문장은 이해하기 어려울 수 있습니다.<br>
        더 짧고 이해하기 쉬운 문장으로 나누는 것을 고려해보세요.
    """,
    "weak": """
        <b>약한 표현/수동태</b><br>
        불명확하거나 확신이 부족한 언어가 사용된 부분을 표시합니다.<br>
        다음을 포함합니다:<br>
        - 약한 표현 (불명확하거나 우유부단한 표현)<br>
        - 수동태 (주어가 행동을 수행하지 않는 문장)<br>
        예시: '공이 던져졌다' vs '철수가 공을 던졌다'<br>
        둘 다 텍스트를 덜 직접적으로 만들 수 있습니다.
    """,
    "nonstandard": """
        <b>비표준 말하기 동사</b><br>
        일반적이지 않은 말하기 동사를 표시합니다<br>
        (흔한 '말했다' 대신).<br>
        지나치게 창의적인 동사는 독자를 혼란스럽게 할 수 있습니다.
    """,
    "filter": """
        <b>필터 단어</b><br>
        메시지를 약화시키는 단어들을 표시합니다<br>
        ('바로', '정말로', '말 그대로' 등).<br>
        이런 단어들을 제거하면 텍스트가 더 명확해집니다.
    """,
    "telling": """
        <b>보여주기보다 말하기</b><br>
        감정이나 행동이 묘사나 행동을 통해 보여주는 대신<br>
        직접적으로 진술된 부분을 강조합니다.<br>
        이는 독자의 참여도를 낮출 수 있습니다.
    """,
    "weak_verb": """
        <b>약한 동사</b><br>
        감정적 강도가 뚜렷하지 않은 동사를 표시합니다.<br>
        더 강력한 동의어로 대체하면 텍스트가 생생해집니다.
    """,
    "overused": """
        <b>과도하게 사용된 단어</b><br>
        너무 자주 반복되는 단어를 표시합니다.<br>
        다양성을 위해 동의어를 사용하거나 문장 구조를 변경하세요.
    """,
    "pronoun": """
        <b>불명확한 대명사 참조</b><br>
        문맥이 불분명한 대명사('그', '그녀', '그것', '그들')를 표시합니다.<br>
        명확한 대명사 사용은 오해를 방지합니다.
    """,
    "repetitive": """
        <b>반복적인 문장 시작</b><br>
        같은 방식으로 시작하는 문장 시퀀스를 표시합니다.<br>
        다양한 문장 시작은 독자의 관심을 유지합니다.
    """
}

KOREAN_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"에 의해", "에게"},
    "weak_patterns": [r'\b\w+(?:다|었다|았다)\b'],
    "weak_terms": {"아마도", "어쩌면", "~인 것 같다", "~일 수도 있다", "~일지도 모른다", "조금", "약간"},
    "standard_speech_verbs": {"말했다", "물었다"},
    "speech_verbs": {"말했다", "물었다", "속삭였다", "외쳤다", "중얼거렸다", "소리쳤다"},
    "filter_words": {"보았다", "들었다", "느꼈다", "알아차렸다", "생각했다", "궁금해했다", "관찰했다", "쳐다봤다", "경청했다", "감지했다", "결정했다", "고려했다", "~인 것 같았다", "나타났다", "관찰했다", "느꼈다", "인식했다", "상상했다"},
    "telling_verbs": {"이다", "~이었다", "느꼈다", "보였다", "~처럼 보였다", "나타났다", "~이 되었다"},
    "emotion_words": {"화난", "슬픈", "행복한", "흥분한", "긴장한", "무서운", "걱정하는", "당황한", "실망한", "좌절한", "짜증난", "불안한", "두려운", "기쁜", "우울한", "불행한", "황홀한", "화가 난", "분노한", "기뻐하는", "충격받은", "놀란", "혼란스러운", "자랑스러운", "만족한", "흡족한", "열정적인", "질투하는"},
    "weak_verbs": {"이다", "있다", "하다"},
    "common_words": {"그리고", "에서", "에", "와", "으로", "에 대해", "하지만", "또는", "처럼", "이다", "있다", "이었다", "있었다", "가지고 있다", "가지고 있다", "그것", "그것의", "그것에게", "이", "저", "그", "저기", "여기", "나의", "너의", "그의", "그녀의", "우리의", "너희의", "그들의", "자신", "아니", "예", "인가", "왜냐하면", "때", "만약", "왜냐하면", "어떤", "누구", "무엇"},
    "quote_pattern": r'"[^"]*"|\'[^\']*\''
}

class KoreanTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "ko_core_news_sm", KOREAN_DATA)
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
        msgBox.setText("The model 'ko_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('ko_core_news_sm')
            self.nlp = spacy.load('ko_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Korean text.
        
        This implements a simplified Korean Readability Index (한글 가독성 지수)
        based on sentence length, syllable count, and character complexity.
        """
        # Count sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        
        if num_sentences == 0:
            return 0
            
        # Count words (Korean words are typically separated by spaces)
        words = text.split()
        num_words = len(words)
        
        if num_words == 0:
            return 0
            
        # Calculate average sentence length
        avg_sentence_length = num_words / num_sentences
        
        # Count syllables (Korean is syllabic, each Hangul character is one syllable)
        # We'll count Hangul characters as a proxy for syllables
        hangul_pattern = re.compile('[가-힣]')
        hangul_chars = hangul_pattern.findall(text)
        num_syllables = len(hangul_chars)
        
        if num_words == 0:
            return 0
            
        # Calculate syllables per word
        syllables_per_word = num_syllables / num_words
        
        # Calculate Korean readability index
        # Higher values indicate more difficult text
        # This formula is a simplification and adaptation for Korean
        readability_index = 0.4 * ((avg_sentence_length) + 100 * (syllables_per_word / 4.5))
        
        return readability_index
        
    def get_tooltips(self):
        """Returns tooltips in Korean."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Korean text analysis module.
    """
    global nlp
    analysis = KoreanTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = KoreanTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Korean spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)