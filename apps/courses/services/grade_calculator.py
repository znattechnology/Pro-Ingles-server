"""
Grade Calculator Service

This service handles all grade calculations for video courses:
- Quiz score aggregation from StudentQuizAttempt
- Practice score calculation from ChallengeProgress (via ChapterQuiz -> PracticeLesson)
- Conversation score aggregation from VapiSession
- Final grade calculation with configurable weights
- Certificate eligibility determination
- Dynamic weight adjustment when components don't exist
- CEFR level mapping for conversation sessions
"""

from typing import Optional, Dict, List, Tuple
from decimal import Decimal
from django.db import transaction
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone

from apps.courses.models import (
    Course, CourseSection, Chapter, ChapterQuiz, StudentQuizAttempt,
    StudentCourseGrade, CourseGradingConfig, GradeHistory
)
from apps.practice.models import ChallengeProgress, VapiSession, PracticeLesson
from apps.users.models import User


# Mapping from course levels to CEFR levels used in VapiSession
COURSE_LEVEL_TO_CEFR = {
    'Beginner': ['A1', 'A2'],
    'beginner': ['A1', 'A2'],
    'Elementary': ['A1', 'A2'],
    'elementary': ['A1', 'A2'],
    'Pre-Intermediate': ['A2', 'B1'],
    'pre-intermediate': ['A2', 'B1'],
    'Intermediate': ['B1', 'B2'],
    'intermediate': ['B1', 'B2'],
    'Upper-Intermediate': ['B2', 'C1'],
    'upper-intermediate': ['B2', 'C1'],
    'Advanced': ['C1', 'C2'],
    'advanced': ['C1', 'C2'],
    'Proficient': ['C1', 'C2'],
    'proficient': ['C1', 'C2'],
    'All Levels': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
    'all levels': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
    # Direct CEFR level mappings (in case course already uses CEFR)
    'A1': ['A1'],
    'A2': ['A2'],
    'B1': ['B1'],
    'B2': ['B2'],
    'C1': ['C1'],
    'C2': ['C2'],
}


class GradeCalculatorService:
    """
    Service for calculating student grades in video courses.

    The grading system combines three components:
    1. Quiz scores (default 50%) - From chapter quizzes
    2. Practice scores (default 30%) - From practice exercises linked to quizzes
    3. Conversation scores (default 20%) - From Vapi conversation sessions
    """

    CALCULATION_VERSION = 1

    def __init__(self, user: User, course: Course):
        self.user = user
        self.course = course
        self.config = self._get_or_create_config()

    def _get_or_create_config(self) -> CourseGradingConfig:
        """Get or create grading configuration for the course."""
        config, _ = CourseGradingConfig.objects.get_or_create(
            course=self.course,
            defaults={
                'quiz_weight': 50,
                'practice_weight': 30,
                'conversation_weight': 20,
            }
        )
        return config

    def calculate_quiz_scores(self) -> Dict:
        """
        Calculate quiz scores for the student.

        Returns dict with:
        - score: Average quiz score (0-100)
        - count: Total quizzes in course
        - completed: Quizzes completed by student
        - passed: Quizzes passed by student
        - details: Per-quiz scores
        """
        # Check if quiz component is enabled
        if not self.config.quiz_enabled:
            return {
                'score': 0.0,
                'count': 0,
                'completed': 0,
                'passed': 0,
                'details': [],
                'component_disabled': True
            }

        # Get all quizzes in the course
        quizzes = ChapterQuiz.objects.filter(
            chapter__section__course=self.course,
            is_active=True
        ).select_related('chapter', 'chapter__section')

        quiz_count = quizzes.count()

        if quiz_count == 0:
            return {
                'score': 0.0,
                'count': 0,
                'completed': 0,
                'passed': 0,
                'details': []
            }

        quiz_details = []
        total_score = 0.0
        completed_count = 0
        passed_count = 0

        for quiz in quizzes:
            # Get student's attempts for this quiz
            attempts = StudentQuizAttempt.objects.filter(
                student=self.user,
                chapter_quiz=quiz,
                is_completed=True
            )

            if attempts.exists():
                completed_count += 1

                # Use best attempt or latest based on config
                if self.config.use_best_quiz_attempt:
                    best_attempt = attempts.order_by('-score').first()
                else:
                    best_attempt = attempts.order_by('-created_at').first()

                score_percentage = best_attempt.score_percentage
                is_passed = best_attempt.is_passed

                if is_passed:
                    passed_count += 1

                total_score += score_percentage

                quiz_details.append({
                    'quiz_id': str(quiz.id),
                    'quiz_title': quiz.title,
                    'chapter_title': quiz.chapter.title,
                    'section_title': quiz.chapter.section.title,
                    'score': score_percentage,
                    'is_passed': is_passed,
                    'attempts_used': attempts.count(),
                    'max_attempts': quiz.max_attempts,
                    'passing_score': quiz.passing_score,
                })
            else:
                quiz_details.append({
                    'quiz_id': str(quiz.id),
                    'quiz_title': quiz.title,
                    'chapter_title': quiz.chapter.title,
                    'section_title': quiz.chapter.section.title,
                    'score': 0,
                    'is_passed': False,
                    'attempts_used': 0,
                    'max_attempts': quiz.max_attempts,
                    'passing_score': quiz.passing_score,
                })

        # Calculate average score
        average_score = total_score / quiz_count if quiz_count > 0 else 0.0

        return {
            'score': round(average_score, 2),
            'count': quiz_count,
            'completed': completed_count,
            'passed': passed_count,
            'details': quiz_details
        }

    def calculate_practice_scores(self) -> Dict:
        """
        Calculate practice exercise scores.

        Practice scores are based on completion of challenges linked to
        the course via ChapterQuiz -> PracticeLesson -> Units -> Challenges.

        Returns dict with:
        - score: Completion percentage (0-100)
        - count: Total challenges
        - completed: Challenges completed
        - details: Per-chapter breakdown
        """
        # Check if practice component is enabled
        if not self.config.practice_enabled:
            return {
                'score': 0.0,
                'count': 0,
                'completed': 0,
                'details': [],
                'component_disabled': True
            }

        # Get all practice lessons linked to this course's chapter quizzes
        chapter_quizzes = ChapterQuiz.objects.filter(
            chapter__section__course=self.course,
            is_active=True
        ).select_related('practice_lesson', 'chapter', 'chapter__section')

        practice_details = []
        total_challenges = 0
        completed_challenges = 0

        for quiz in chapter_quizzes:
            if not quiz.practice_lesson:
                continue

            # Get all challenges in the practice lesson's units
            from apps.practice.models import PracticeChallenge

            challenges = PracticeChallenge.objects.filter(
                unit__lesson=quiz.practice_lesson,
                is_active=True
            )

            chapter_total = challenges.count()

            if chapter_total == 0:
                continue

            # Count completed challenges for this user
            chapter_completed = ChallengeProgress.objects.filter(
                user=self.user,
                challenge__in=challenges,
                completed=True
            ).count()

            total_challenges += chapter_total
            completed_challenges += chapter_completed

            practice_details.append({
                'chapter_id': str(quiz.chapter.id),
                'chapter_title': quiz.chapter.title,
                'section_title': quiz.chapter.section.title,
                'practice_lesson_id': str(quiz.practice_lesson.id),
                'total_challenges': chapter_total,
                'completed_challenges': chapter_completed,
                'completion_percentage': round(
                    (chapter_completed / chapter_total) * 100 if chapter_total > 0 else 0, 2
                ),
            })

        # Calculate overall completion percentage
        completion_percentage = (
            (completed_challenges / total_challenges) * 100
            if total_challenges > 0 else 0.0
        )

        return {
            'score': round(completion_percentage, 2),
            'count': total_challenges,
            'completed': completed_challenges,
            'details': practice_details
        }

    def calculate_conversation_scores(self) -> Dict:
        """
        Calculate conversation practice scores from Vapi sessions.

        For video courses, we look at Vapi sessions that match the course level.
        Uses CEFR level mapping to correctly match course levels (Beginner, Intermediate, etc.)
        to VapiSession CEFR levels (A1, A2, B1, B2, C1, C2).

        Returns dict with:
        - score: Average conversation score (0-100)
        - sessions: Total sessions completed
        - minutes: Total practice minutes
        - details: Per-session breakdown
        - has_requirement: Whether course requires conversation practice
        """
        # Check if conversation component is enabled for this course
        if not self.config.conversation_enabled:
            return {
                'score': 0.0,
                'sessions': 0,
                'minutes': 0,
                'details': [],
                'has_requirement': False,
                'component_disabled': True
            }

        # Check if course has conversation requirement
        has_requirement = self.config.require_conversation_if_available

        # Get Vapi sessions for this user
        sessions = VapiSession.objects.filter(
            user=self.user
        ).order_by('-created_at')

        # If the course has a specific level, filter sessions by matching CEFR levels
        if hasattr(self.course, 'level') and self.course.level:
            course_level = self.course.level
            cefr_levels = COURSE_LEVEL_TO_CEFR.get(course_level, None)

            if cefr_levels:
                # Filter sessions by any matching CEFR level
                sessions = sessions.filter(level__in=cefr_levels)
            # If no mapping found and it's not empty, try direct match as fallback
            elif course_level:
                sessions = sessions.filter(level=course_level)

        session_count = sessions.count()

        if session_count == 0:
            return {
                'score': 0.0,
                'sessions': 0,
                'minutes': 0,
                'details': [],
                'has_requirement': has_requirement
            }

        # Aggregate scores
        aggregates = sessions.aggregate(
            avg_score=Avg('overall_score'),
            total_minutes=Sum('duration_minutes'),
            avg_fluency=Avg('fluency_score'),
            avg_pronunciation=Avg('pronunciation_score'),
            avg_grammar=Avg('grammar_score'),
            avg_vocabulary=Avg('vocabulary_score'),
        )

        # Get detailed session info (last 10)
        session_details = []
        for session in sessions[:10]:
            session_details.append({
                'session_id': session.session_id,
                'date': session.created_at.isoformat(),
                'level': session.level,
                'domain': session.domain,
                'duration_minutes': session.duration_minutes,
                'overall_score': session.overall_score,
                'fluency': session.fluency_score,
                'pronunciation': session.pronunciation_score,
                'grammar': session.grammar_score,
                'vocabulary': session.vocabulary_score,
            })

        return {
            'score': round(aggregates['avg_score'] or 0, 2),
            'sessions': session_count,
            'minutes': aggregates['total_minutes'] or 0,
            'fluency_average': round(aggregates['avg_fluency'] or 0, 2),
            'pronunciation_average': round(aggregates['avg_pronunciation'] or 0, 2),
            'grammar_average': round(aggregates['avg_grammar'] or 0, 2),
            'vocabulary_average': round(aggregates['avg_vocabulary'] or 0, 2),
            'details': session_details,
            'has_requirement': has_requirement
        }

    def calculate_final_grade(
        self,
        quiz_data: Dict,
        practice_data: Dict,
        conversation_data: Dict
    ) -> Tuple[float, str, Dict]:
        """
        Calculate final weighted grade with dynamic weight adjustment.

        This method automatically adjusts weights when components don't exist:
        - If quiz_count = 0, quiz weight is redistributed to other components
        - If practice_count = 0, practice weight is redistributed
        - If no conversation sessions, conversation weight is redistributed

        Returns:
        - final_percentage: Weighted average (0-100)
        - final_letter: Letter grade (A+, A, B+, etc.)
        - weight_info: Dict with actual weights used (for transparency)
        """
        # Determine which components are active (have content)
        quiz_active = quiz_data.get('count', 0) > 0 and self.config.quiz_enabled
        practice_active = practice_data.get('count', 0) > 0 and self.config.practice_enabled
        conversation_active = (
            conversation_data.get('has_requirement', False) and
            conversation_data.get('sessions', 0) > 0 and
            self.config.conversation_enabled and
            not conversation_data.get('component_disabled', False)
        )

        # Get configured weights
        quiz_weight = self.config.quiz_weight if quiz_active else 0
        practice_weight = self.config.practice_weight if practice_active else 0
        conversation_weight = self.config.conversation_weight if conversation_active else 0

        total_active_weight = quiz_weight + practice_weight + conversation_weight

        # If no components are active, return 0
        if total_active_weight == 0:
            return 0.0, 'N/A', {
                'quiz_weight': 0,
                'practice_weight': 0,
                'conversation_weight': 0,
                'mode': 'no_content',
                'message': 'Nenhum componente de avaliação disponível no curso'
            }

        # Normalize weights to sum to 100
        normalized_quiz = (quiz_weight / total_active_weight) * 100 if quiz_active else 0
        normalized_practice = (practice_weight / total_active_weight) * 100 if practice_active else 0
        normalized_conversation = (conversation_weight / total_active_weight) * 100 if conversation_active else 0

        # Calculate weighted components
        quiz_component = quiz_data['score'] * (normalized_quiz / 100)
        practice_component = practice_data['score'] * (normalized_practice / 100)
        conversation_component = conversation_data['score'] * (normalized_conversation / 100) if conversation_active else 0

        final_percentage = round(quiz_component + practice_component + conversation_component, 2)

        # Get letter grade
        final_letter = self.config.get_grade_with_plus_minus(final_percentage)

        # Build weight info for transparency
        active_components = []
        if quiz_active:
            active_components.append('quizzes')
        if practice_active:
            active_components.append('practice')
        if conversation_active:
            active_components.append('conversation')

        weight_info = {
            'quiz_weight': round(normalized_quiz, 1),
            'practice_weight': round(normalized_practice, 1),
            'conversation_weight': round(normalized_conversation, 1),
            'original_quiz_weight': self.config.quiz_weight,
            'original_practice_weight': self.config.practice_weight,
            'original_conversation_weight': self.config.conversation_weight,
            'mode': 'full' if len(active_components) == 3 else 'simplified',
            'active_components': active_components,
            'weights_adjusted': total_active_weight != 100
        }

        return final_percentage, final_letter, weight_info

    def check_certificate_eligibility(
        self,
        quiz_data: Dict,
        practice_data: Dict,
        conversation_data: Dict,
        final_percentage: float,
        weight_info: Dict = None
    ) -> Tuple[bool, Dict]:
        """
        Check if student meets all requirements for certificate.

        Dynamically adjusts requirements based on what components exist:
        - If no quizzes in course, quiz requirements are skipped
        - If no practice lessons linked, practice requirements are skipped
        - If no conversation sessions or component disabled, conversation requirements are skipped

        Returns:
        - is_eligible: Boolean indicating eligibility
        - details: Dict with each requirement's status
        """
        eligibility_details = {}
        all_met = True
        weight_info = weight_info or {}

        # Determine which components have content
        quiz_exists = quiz_data.get('count', 0) > 0 and self.config.quiz_enabled
        practice_exists = practice_data.get('count', 0) > 0 and self.config.practice_enabled
        conversation_exists = (
            conversation_data.get('sessions', 0) > 0 and
            self.config.conversation_enabled and
            not conversation_data.get('component_disabled', False)
        )

        # 1. Check minimum quiz average (only if quizzes exist)
        if quiz_exists:
            quiz_met = quiz_data['score'] >= self.config.min_quiz_average
            eligibility_details['quiz_average'] = {
                'met': quiz_met,
                'required': self.config.min_quiz_average,
                'actual': quiz_data['score'],
                'message': f"Média dos quizzes: {quiz_data['score']}% (mínimo: {self.config.min_quiz_average}%)"
            }
            if not quiz_met:
                all_met = False

            # 2. Check all quizzes passed (if required)
            if self.config.require_all_quizzes_passed:
                all_quizzes_passed = quiz_data['passed'] == quiz_data['count']
                eligibility_details['all_quizzes_passed'] = {
                    'met': all_quizzes_passed,
                    'required': quiz_data['count'],
                    'actual': quiz_data['passed'],
                    'message': f"Quizzes aprovados: {quiz_data['passed']}/{quiz_data['count']}"
                }
                if not all_quizzes_passed:
                    all_met = False
        else:
            eligibility_details['quiz_average'] = {
                'met': True,
                'required': None,
                'actual': 0,
                'message': "Sem quizzes configurados neste curso",
                'skipped': True
            }

        # 3. Check minimum practice completion (only if practice exists)
        if practice_exists:
            practice_met = practice_data['score'] >= self.config.min_practice_completion
            eligibility_details['practice_completion'] = {
                'met': practice_met,
                'required': self.config.min_practice_completion,
                'actual': practice_data['score'],
                'message': f"Exercícios práticos: {practice_data['score']}% completos (mínimo: {self.config.min_practice_completion}%)"
            }
            if not practice_met:
                all_met = False
        else:
            eligibility_details['practice_completion'] = {
                'met': True,
                'required': None,
                'actual': 0,
                'message': "Sem exercícios práticos vinculados neste curso",
                'skipped': True
            }

        # 4. Check conversation score (if required, enabled, and available)
        if self.config.conversation_enabled and conversation_data.get('has_requirement', False):
            if conversation_exists:
                conversation_met = conversation_data['score'] >= self.config.min_conversation_score
                eligibility_details['conversation_score'] = {
                    'met': conversation_met,
                    'required': self.config.min_conversation_score,
                    'actual': conversation_data['score'],
                    'message': f"Pontuação de conversação: {conversation_data['score']}% (mínimo: {self.config.min_conversation_score}%)"
                }
                if not conversation_met:
                    all_met = False
            else:
                # Conversation is required but no sessions
                eligibility_details['conversation_score'] = {
                    'met': False,
                    'required': self.config.min_conversation_score,
                    'actual': 0,
                    'message': "Nenhuma sessão de conversação completada no nível do curso"
                }
                all_met = False
        else:
            eligibility_details['conversation_score'] = {
                'met': True,
                'required': None,
                'actual': conversation_data.get('score', 0),
                'message': "Conversação não é requisito para este curso" if not self.config.require_conversation_if_available else "Componente de conversação desativado",
                'skipped': True
            }

        # 5. Check minimum final grade
        final_grade_met = final_percentage >= self.config.min_final_grade
        eligibility_details['final_grade'] = {
            'met': final_grade_met,
            'required': self.config.min_final_grade,
            'actual': final_percentage,
            'message': f"Nota final: {final_percentage}% (mínimo: {self.config.min_final_grade}%)"
        }
        if not final_grade_met:
            all_met = False

        # Add weight adjustment info if weights were adjusted
        if weight_info.get('weights_adjusted'):
            eligibility_details['weight_adjustment'] = {
                'met': True,
                'required': None,
                'actual': None,
                'message': f"Pesos ajustados automaticamente: {', '.join(weight_info.get('active_components', []))}",
                'info_only': True
            }

        return all_met, eligibility_details

    @transaction.atomic
    def calculate_and_save(self, change_reason: str = 'recalculation') -> StudentCourseGrade:
        """
        Calculate all grades and save to database.

        Args:
            change_reason: Reason for this calculation (for audit trail)

        Returns:
            StudentCourseGrade: Updated grade record
        """
        # Calculate all components
        quiz_data = self.calculate_quiz_scores()
        practice_data = self.calculate_practice_scores()
        conversation_data = self.calculate_conversation_scores()

        # Calculate final grade with dynamic weight adjustment
        final_percentage, final_letter, weight_info = self.calculate_final_grade(
            quiz_data, practice_data, conversation_data
        )

        # Check eligibility with weight info for context
        is_eligible, eligibility_details = self.check_certificate_eligibility(
            quiz_data, practice_data, conversation_data, final_percentage, weight_info
        )

        # Get or create grade record
        grade, created = StudentCourseGrade.objects.get_or_create(
            user=self.user,
            course=self.course,
            defaults={'calculation_version': self.CALCULATION_VERSION}
        )

        # Track if grade changed
        grade_changed = (
            created or
            grade.final_grade_percentage != final_percentage or
            grade.is_eligible_for_certificate != is_eligible
        )

        # Update grade record
        grade.quiz_score = quiz_data['score']
        grade.quiz_count = quiz_data['count']
        grade.quiz_completed = quiz_data['completed']
        grade.quiz_passed = quiz_data['passed']
        grade.quiz_details = quiz_data['details']

        grade.practice_score = practice_data['score']
        grade.practice_count = practice_data['count']
        grade.practice_completed = practice_data['completed']
        grade.practice_details = practice_data['details']

        grade.conversation_score = conversation_data['score']
        grade.conversation_sessions = conversation_data['sessions']
        grade.conversation_minutes = conversation_data['minutes']
        grade.conversation_details = conversation_data['details']
        grade.has_conversation_requirement = conversation_data['has_requirement']

        grade.final_grade_percentage = final_percentage
        grade.final_grade_letter = final_letter
        grade.is_eligible_for_certificate = is_eligible
        grade.eligibility_details = eligibility_details
        grade.weight_info = weight_info
        grade.calculation_version = self.CALCULATION_VERSION

        grade.save()

        # Create history entry if grade changed
        if grade_changed:
            GradeHistory.objects.create(
                student_grade=grade,
                quiz_score=quiz_data['score'],
                practice_score=practice_data['score'],
                conversation_score=conversation_data['score'],
                final_grade_percentage=final_percentage,
                final_grade_letter=final_letter,
                is_eligible=is_eligible,
                change_reason=change_reason,
                change_details={
                    'quiz_data': {
                        'score': quiz_data['score'],
                        'completed': quiz_data['completed'],
                        'passed': quiz_data['passed'],
                    },
                    'practice_data': {
                        'score': practice_data['score'],
                        'completed': practice_data['completed'],
                    },
                    'conversation_data': {
                        'score': conversation_data['score'],
                        'sessions': conversation_data['sessions'],
                    },
                    'config': {
                        'quiz_weight': self.config.quiz_weight,
                        'practice_weight': self.config.practice_weight,
                        'conversation_weight': self.config.conversation_weight,
                    },
                    'weight_info': weight_info
                }
            )

        return grade

    @classmethod
    def recalculate_for_course(cls, course: Course) -> int:
        """
        Recalculate grades for all enrolled students in a course.

        Returns:
            int: Number of grades updated
        """
        from apps.courses.models import CourseEnrollment

        enrollments = CourseEnrollment.objects.filter(
            course=course
        ).select_related('user')

        count = 0
        for enrollment in enrollments:
            calculator = cls(enrollment.user, course)
            calculator.calculate_and_save(change_reason='recalculation')
            count += 1

        return count

    @classmethod
    def trigger_update_on_quiz_complete(cls, user: User, chapter_quiz: ChapterQuiz):
        """
        Trigger grade recalculation when a quiz is completed.
        """
        course = chapter_quiz.chapter.section.course
        calculator = cls(user, course)
        return calculator.calculate_and_save(change_reason='quiz_completed')

    @classmethod
    def trigger_update_on_practice_complete(cls, user: User, challenge_progress: ChallengeProgress):
        """
        Trigger grade recalculation when a practice challenge is completed.

        This is more complex because we need to find which course(s) the
        challenge belongs to via ChapterQuiz -> PracticeLesson relationship.
        """
        # Find courses that have this challenge's lesson linked
        chapter_quizzes = ChapterQuiz.objects.filter(
            practice_lesson__units__challenges=challenge_progress.challenge
        ).select_related('chapter__section__course')

        grades = []
        courses_updated = set()

        for quiz in chapter_quizzes:
            course = quiz.chapter.section.course
            if course.id not in courses_updated:
                calculator = cls(user, course)
                grade = calculator.calculate_and_save(change_reason='practice_completed')
                grades.append(grade)
                courses_updated.add(course.id)

        return grades

    @classmethod
    def trigger_update_on_conversation_session(cls, user: User, vapi_session: VapiSession):
        """
        Trigger grade recalculation when a conversation session is completed.

        Updates grades for all courses the user is enrolled in that have
        conversation requirements enabled.
        """
        from apps.courses.models import CourseEnrollment

        enrollments = CourseEnrollment.objects.filter(
            user=user
        ).select_related('course')

        grades = []
        for enrollment in enrollments:
            try:
                config = enrollment.course.grading_config
                if config.require_conversation_if_available:
                    calculator = cls(user, enrollment.course)
                    grade = calculator.calculate_and_save(change_reason='conversation_session')
                    grades.append(grade)
            except CourseGradingConfig.DoesNotExist:
                pass

        return grades
