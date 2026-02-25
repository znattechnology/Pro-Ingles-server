"""
Text Validation Service - Unified text answer validation with typo tolerance

This service provides consistent text validation across all challenge types
that require text input (FILL_BLANK, TRANSLATION, etc.).

Uses SequenceMatcher for fuzzy matching with configurable similarity threshold.
"""

from difflib import SequenceMatcher
from typing import Tuple, List, Optional
import logging
import unicodedata
import re

logger = logging.getLogger(__name__)


class TextValidationService:
    """
    Unified text validation service with typo tolerance.

    Default tolerance is 85% similarity, which allows for minor typos
    while still requiring substantial correctness.

    For TRANSLATION challenges, uses more aggressive normalization
    and lower tolerance (70%) to accept semantic variations.
    """

    DEFAULT_TOLERANCE = 0.85  # 85% similarity threshold
    STRICT_TOLERANCE = 0.95   # 95% for stricter matching
    LENIENT_TOLERANCE = 0.75  # 75% for more forgiving matching
    TRANSLATION_TOLERANCE = 0.70  # 70% for translation (more flexible)

    @staticmethod
    def remove_accents(text: str) -> str:
        """
        Remove accents from text for more flexible comparison.

        Examples:
            "Ouça" -> "Ouca"
            "você" -> "voce"
            "número" -> "numero"
        """
        if not text:
            return ""
        # Normalize to NFD (decomposed form), remove combining characters
        normalized = unicodedata.normalize('NFD', text)
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for comparison.

        - Converts to lowercase
        - Strips leading/trailing whitespace
        - Collapses multiple spaces into single space

        Args:
            text: Raw text input

        Returns:
            Normalized text string
        """
        if not text:
            return ""
        return ' '.join(text.lower().strip().split())

    @staticmethod
    def normalize_for_translation(text: str) -> str:
        """
        Aggressive normalization for translation comparison.

        - Converts to lowercase
        - Removes accents (ç->c, á->a, etc.)
        - Removes punctuation
        - Collapses multiple spaces
        - Strips whitespace

        This allows "Ouça e circule" to match "ouca e circule"

        Args:
            text: Raw text input

        Returns:
            Heavily normalized text string
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remove accents
        text = TextValidationService.remove_accents(text)

        # Remove punctuation (keep only letters, numbers, spaces)
        text = re.sub(r'[^\w\s]', '', text)

        # Collapse spaces and strip
        text = ' '.join(text.strip().split())

        return text

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two texts.

        Uses Python's SequenceMatcher which implements the Ratcliff/Obershelp
        pattern-matching algorithm.

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0

        norm1 = TextValidationService.normalize_text(text1)
        norm2 = TextValidationService.normalize_text(text2)

        if norm1 == norm2:
            return 1.0

        return SequenceMatcher(None, norm1, norm2).ratio()

    @staticmethod
    def validate(
        user_answer: str,
        correct_answer: str,
        tolerance: float = DEFAULT_TOLERANCE
    ) -> Tuple[bool, float]:
        """
        Validate user answer against correct answer with typo tolerance.

        Args:
            user_answer: The user's submitted answer
            correct_answer: The correct answer to compare against
            tolerance: Minimum similarity ratio to accept (default 0.85)

        Returns:
            Tuple of (is_correct: bool, similarity: float)
        """
        user_normalized = TextValidationService.normalize_text(user_answer)
        correct_normalized = TextValidationService.normalize_text(correct_answer)

        # Exact match (fast path)
        if user_normalized == correct_normalized:
            logger.debug(f"Exact match: '{user_answer}'")
            return True, 1.0

        # Calculate similarity
        similarity = SequenceMatcher(None, user_normalized, correct_normalized).ratio()
        is_correct = similarity >= tolerance

        if is_correct:
            logger.info(
                f"Accepted with typo tolerance: '{user_answer}' vs '{correct_answer}' "
                f"(similarity: {similarity:.2%}, threshold: {tolerance:.2%})"
            )
        else:
            logger.debug(
                f"Rejected: '{user_answer}' vs '{correct_answer}' "
                f"(similarity: {similarity:.2%}, threshold: {tolerance:.2%})"
            )

        return is_correct, similarity

    @staticmethod
    def validate_against_multiple(
        user_answer: str,
        correct_answers: List[str],
        tolerance: float = DEFAULT_TOLERANCE
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Validate user answer against multiple correct answers.

        Useful when a challenge has multiple acceptable correct answers.

        Args:
            user_answer: The user's submitted answer
            correct_answers: List of acceptable correct answers
            tolerance: Minimum similarity ratio to accept

        Returns:
            Tuple of (is_correct: bool, best_similarity: float, matched_answer: str or None)
        """
        if not correct_answers:
            logger.warning("No correct answers provided for validation")
            return False, 0.0, None

        best_similarity = 0.0
        matched_answer = None

        for correct_answer in correct_answers:
            is_correct, similarity = TextValidationService.validate(
                user_answer, correct_answer, tolerance
            )

            if is_correct:
                return True, similarity, correct_answer

            if similarity > best_similarity:
                best_similarity = similarity
                matched_answer = correct_answer

        return False, best_similarity, matched_answer

    @staticmethod
    def validate_translation(
        user_answer: str,
        correct_answers: List[str],
        tolerance: float = None
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Validate translation with aggressive normalization.

        Uses more flexible matching specifically designed for translations:
        - Removes accents (á->a, ç->c, etc.)
        - Removes punctuation
        - Lower tolerance (70% default)

        This allows variations like:
        - "Ouça e circule" ≈ "ouca e circule"
        - "você ouve" ≈ "voce ouve"

        Args:
            user_answer: The user's submitted translation
            correct_answers: List of acceptable correct translations
            tolerance: Minimum similarity ratio (default 0.70 for translations)

        Returns:
            Tuple of (is_correct: bool, best_similarity: float, matched_answer: str or None)
        """
        if tolerance is None:
            tolerance = TextValidationService.TRANSLATION_TOLERANCE

        if not correct_answers:
            logger.warning("No correct answers provided for translation validation")
            return False, 0.0, None

        # Normalize user answer aggressively
        user_normalized = TextValidationService.normalize_for_translation(user_answer)

        best_similarity = 0.0
        matched_answer = None

        for correct_answer in correct_answers:
            # Normalize correct answer the same way
            correct_normalized = TextValidationService.normalize_for_translation(correct_answer)

            # Exact match after normalization (fast path)
            if user_normalized == correct_normalized:
                logger.info(f"Translation exact match (after normalization): '{user_answer}' == '{correct_answer}'")
                return True, 1.0, correct_answer

            # Calculate similarity on normalized texts
            similarity = SequenceMatcher(None, user_normalized, correct_normalized).ratio()

            if similarity >= tolerance:
                logger.info(
                    f"Translation accepted: '{user_answer}' ≈ '{correct_answer}' "
                    f"(similarity: {similarity:.2%}, threshold: {tolerance:.2%})"
                )
                return True, similarity, correct_answer

            if similarity > best_similarity:
                best_similarity = similarity
                matched_answer = correct_answer

        logger.debug(
            f"Translation rejected: '{user_answer}', best match: '{matched_answer}' "
            f"(similarity: {best_similarity:.2%}, threshold: {tolerance:.2%})"
        )

        return False, best_similarity, matched_answer

    @staticmethod
    def get_feedback_message(similarity: float, tolerance: float = DEFAULT_TOLERANCE) -> str:
        """
        Generate user-friendly feedback based on similarity score.

        Args:
            similarity: Calculated similarity ratio
            tolerance: The threshold used for validation

        Returns:
            Feedback message string
        """
        if similarity >= 1.0:
            return "Perfeito!"
        elif similarity >= tolerance:
            return "Correto! (pequeno erro de digitação aceito)"
        elif similarity >= tolerance - 0.10:
            return "Quase! Verifique a ortografia."
        elif similarity >= 0.5:
            return "Parcialmente correto. Tente novamente."
        else:
            return "Incorreto. Revise o conteúdo."
