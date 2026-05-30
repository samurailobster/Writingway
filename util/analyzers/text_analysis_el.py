#!/usr/bin/env python
"""
text_analysis_el.py

Greek-specific text analysis module inheriting from BaseTextAnalysis.
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
        <b>Σύνθετες προτάσεις</b><br>
        Επισημαίνει προτάσεις που είναι πολύ μεγάλες ή έχουν περίπλοκη δομή, οι οποίες μπορεί να είναι δύσκολο να κατανοηθούν.<br>
        Εξετάστε το ενδεχόμενο να τις χωρίσετε σε μικρότερες, πιο προσιτές προτάσεις.
    """,
    "weak": """
        <b>Αδύναμες διατυπώσεις/παθητική φωνή</b><br>
        Υποδεικνύει τμήματα κειμένου με μη σαφή ή αποφασιστική γλώσσα.<br>
        Περιλαμβάνει:<br>
        - Αδύναμες διατυπώσεις (ασαφείς ή αναποφάσιστες εκφράσεις)<br>
        - Παθητική φωνή (προτάσεις όπου το υποκείμενο δεν εκτελεί την ενέργεια)<br>
        Παράδειγμα: 'Η μπάλα ρίχτηκε' αντί για 'Ο Γιάννης έριξε την μπάλα'<br>
        Και τα δύο μπορούν να κάνουν το κείμενο λιγότερο άμεσο.
    """,
    "nonstandard": """
        <b>Μη τυπικά ρήματα λόγου</b><br>
        Υποδεικνύει ασυνήθιστα ρήματα που περιγράφουν ομιλία<br>
        (αντί των συνηθισμένων όπως 'είπε').<br>
        Τα υπερβολικά δημιουργικά ρήματα μπορεί να μπερδέψουν τον αναγνώστη.
    """,
    "filter": """
        <b>Λέξεις φίλτρου</b><br>
        Υποδεικνύει λέξεις που αποδυναμώνουν το μήνυμα<br>
        (όπως 'απλά', 'πραγματικά', 'κυριολεκτικά').<br>
        Η αφαίρεσή τους θα ενισχύσει τη σαφήνεια του κειμένου.
    """,
    "telling": """
        <b>Αφήγηση αντί για επίδειξη</b><br>
        Επισημαίνει τμήματα όπου τα συναισθήματα ή οι ενέργειες δίνονται άμεσα<br>
        αντί να δείχνονται μέσω περιγραφών ή δράσεων.<br>
        Αυτό μπορεί να μειώσει τη συμμετοχή του αναγνώστη.
    """,
    "weak_verb": """
        <b>Αδύναμα ρήματα</b><br>
        Υποδεικνύει ρήματα χωρίς σαφές συναισθηματικό φορτίο.<br>
        Η αντικατάστασή τους με ισχυρότερα συνώνυμα θα ζωντανέψει το κείμενο.
    """,
    "overused": """
        <b>Υπερχρησιμοποιούμενες λέξεις</b><br>
        Υποδεικνύει λέξεις που επαναλαμβάνονται πολύ συχνά.<br>
        Χρησιμοποιήστε συνώνυμα ή αλλάξτε τη σύνταξη της πρότασης για ποικιλία.
    """,
    "pronoun": """
        <b>Ασαφείς αναφορές αντωνυμιών</b><br>
        Υποδεικνύει αντωνυμίες ('αυτός', 'αυτή', 'αυτό', 'αυτοί') με ασαφές πλαίσιο.<br>
        Η σαφής χρήση αντωνυμιών αποτρέπει τις παρεξηγήσεις.
    """,
    "repetitive": """
        <b>Επαναλαμβανόμενες αρχές προτάσεων</b><br>
        Υποδεικνύει ακολουθίες προτάσεων που ξεκινούν με τον ίδιο τρόπο.<br>
        Η ποικιλία στην έναρξη των προτάσεων διατηρεί την προσοχή του αναγνώστη.
    """
}

GREEK_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"από"},
    "weak_patterns": [r'\b\w+(?:ω|εί)\b'],
    "weak_terms": {"ίσως", "μπορεί", "πιθανόν", "φαίνεται", "κάπως", "λίγο", "μάλλον"},
    "standard_speech_verbs": {"λέω", "ρωτάω"},
    "speech_verbs": {"λέω", "ρωτάω", "ψιθυρίζω", "φωνάζω", "μουρμουρίζω", "αναφωνώ"},
    "filter_words": {"είδε", "άκουσε", "ένιωσε", "παρατήρησε", "σκέφτηκε", "αναρωτήθηκε", "παρακολούθησε", "κοίταξε", "άκουγε", "αισθάνθηκε", "αποφάσισε", "σκεφτόταν", "φαινόταν", "εμφανίστηκε", "παρατηρούσε", "ένιωθε", "αντιλαμβανόταν", "φανταζόταν"},
    "telling_verbs": {"είμαι", "νιώθω", "φαίνομαι", "μοιάζω", "εμφανίζομαι", "γίνομαι"},
    "emotion_words": {"θυμωμένος", "λυπημένος", "χαρούμενος", "ενθουσιασμένος", "νευρικός", "τρομαγμένος", "ανήσυχος", "ντροπιασμένος", "απογοητευμένος", "εκνευρισμένος", "φοβισμένος", "καταθλιπτικός", "δυστυχισμένος", "εκστατικός", "αναστατωμένος", "εξοργισμένος", "σοκαρισμένος", "έκπληκτος", "μπερδεμένος", "περήφανος", "ευχαριστημένος", "ικανοποιημένος", "ενθουσιώδης", "ζηλιάρης"},
    "weak_verbs": {"είμαι"},
    "common_words": {"και", "σε", "για", "από", "με", "το", "του", "της", "τα", "των", "ένα", "μια", "στο", "στη", "στον", "στην", "είναι", "ήταν", "έχει", "έχουν", "αυτό", "αυτός", "αυτή", "εκεί", "εδώ", "μου", "σου", "μας", "σας", "τους", "δεν", "ναι", "αν", "όταν", "επειδή", "γιατί", "που", "οποίος", "οποία", "οποίο"},
    "quote_pattern": r'«[^»]*»|\"[^\"]*\"'
}

class GreekTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "el_core_news_sm", GREEK_DATA)
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
        msgBox.setText("The model 'el_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('el_core_news_sm')
            self.nlp = spacy.load('el_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Greek using a simplified Flesch-Kincaid adaptation.
        
        This is an adaptation suitable for Greek text as there is no standardized 
        Greek-specific readability formula. 
        The formula uses syllable count approximation for Greek words.
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?;]+', text)  # Note: ';' is Greek question mark
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)

        # Estimate syllables by counting vowels (α, ε, η, ι, ο, υ, ω) and diphthongs
        vowels = 'αεηιουωάέήίόύώϊϋΐΰ'
        diphthongs = ['αι', 'οι', 'ει', 'υι', 'αυ', 'ευ', 'ηυ', 'ου']

        total_syllables = 0
        for word in words:
            word = word.lower()
            syllables = 0
            i = 0
            while i < len(word):
                # Check for diphthongs first
                is_diphthong = False
                if i < len(word) - 1:
                    for d in diphthongs:
                        if word[i:i+2] == d:
                            syllables += 1
                            is_diphthong = True
                            i += 2
                            break

                # If not a diphthong, check for single vowels
                if not is_diphthong:
                    if word[i] in vowels:
                        syllables += 1
                    i += 1

            # Ensure each word has at least one syllable
            if syllables == 0:
                syllables = 1

            total_syllables += syllables

        if num_sentences == 0 or num_words == 0:
            return 0

        # Simplified adaptation of Flesch-Kincaid for Greek
        average_sentence_length = num_words / num_sentences
        average_syllables_per_word = total_syllables / num_words

        # Formula: 206.835 - (1.015 * ASL) - (84.6 * ASW)
        # Adjusted for Greek text
        readability = 206.835 - (1.015 * average_sentence_length) - (84.6 * average_syllables_per_word)

        # Constrain to 0-100 range for easier interpretation
        return max(0, min(100, readability))

    def get_tooltips(self):
        """Returns tooltips in Greek."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Greek text analysis module.
    """
    global nlp
    analysis = GreekTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = GreekTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Greek spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
