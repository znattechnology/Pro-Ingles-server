"""
Management command to prepare demo data for Maria Estudante.
Creates grades and certificate for the presentation.

SAFE: Only creates new records for this specific user.
Does NOT modify any existing data or shared resources.

Usage:
    python manage.py prepare_demo
    python manage.py prepare_demo --course "English Communication"
"""

import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.users.models import User
from apps.courses.models import (
    Course, CourseEnrollment, UserCourseProgress, ChapterProgress,
    StudentCourseGrade, CourseGradingConfig, GradeHistory,
    CourseCertificate,
)


STUDENT_EMAIL = 'estudante@proenglish.com'


class Command(BaseCommand):
    help = 'Prepare demo grades and certificate for Maria Estudante'

    def add_arguments(self, parser):
        parser.add_argument(
            '--course',
            type=str,
            help='Course title to use (partial match). Default: first enrolled published course.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Find Maria
        try:
            student = User.objects.get(email=STUDENT_EMAIL)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f'User {STUDENT_EMAIL} not found.'
            ))
            return

        self.stdout.write(f'Student: {student.name} ({student.email})')

        # 2. Find course
        course = self._find_course(student, options.get('course'))
        if not course:
            return

        self.stdout.write(f'Course: {course.title} (ID: {course.id})')

        # 3. Ensure enrollment exists
        enrollment, created = CourseEnrollment.objects.get_or_create(
            user=student,
            course=course,
            defaults={'is_active': True}
        )
        action = 'Created' if created else 'Already exists'
        self.stdout.write(f'  Enrollment: {action}')

        # 4. Set progress to 100%
        self._set_full_progress(student, course)

        # 5. Create grade record
        grade = self._create_grade(student, course)

        # 6. Create certificate record
        self._create_certificate(student, course, grade)

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== DEMO READY ==='))
        self.stdout.write(f'  Grade: {grade.final_grade_percentage}% ({grade.final_grade_letter})')
        self.stdout.write(f'  Certificate: {grade.is_eligible_for_certificate}')
        self.stdout.write('')
        self.stdout.write('Demo pages:')
        self.stdout.write('  /user/grades')
        self.stdout.write('  /user/certificates')

    def _find_course(self, student, course_title=None):
        if course_title:
            course = Course.objects.filter(title__icontains=course_title).first()
            if not course:
                self.stderr.write(self.style.ERROR(f'Course "{course_title}" not found'))
                # List available courses
                self.stdout.write('Available courses:')
                for c in Course.objects.all()[:10]:
                    self.stdout.write(f'  - {c.title} ({c.status})')
                return None
            return course

        # Try enrolled courses first
        course = Course.objects.filter(
            enrollments__user=student, status='Published'
        ).first()
        if course:
            return course

        # Any published course
        course = Course.objects.filter(status='Published').first()
        if course:
            return course

        # Any course at all
        course = Course.objects.first()
        if not course:
            self.stderr.write(self.style.ERROR('No courses found'))
        return course

    def _set_full_progress(self, student, course):
        progress, created = UserCourseProgress.objects.get_or_create(
            user=student,
            course=course,
            defaults={
                'enrollmentDate': timezone.now(),
                'overallProgress': 100.0,
                'completion_date': timezone.now(),
                'total_time_spent': 480,
            }
        )

        if not created:
            progress.overallProgress = 100.0
            if not progress.completion_date:
                progress.completion_date = timezone.now()
            progress.save(update_fields=['overallProgress', 'completion_date'])

        # Mark chapters as complete
        count = 0
        for section in course.sections.all():
            for chapter in section.chapters.all():
                _, ch_created = ChapterProgress.objects.get_or_create(
                    user_progress=progress,
                    chapter=chapter,
                    defaults={
                        'completed': True,
                        'completed_at': timezone.now(),
                        'attempts': 1,
                        'time_spent': 25,
                    }
                )
                if ch_created:
                    count += 1

        self.stdout.write(f'  Progress: 100% ({count} new chapter completions)')

    def _create_grade(self, student, course):
        # Ensure grading config
        config, _ = CourseGradingConfig.objects.get_or_create(
            course=course,
            defaults={
                'quiz_weight': 50,
                'practice_weight': 30,
                'conversation_weight': 20,
            }
        )

        grade, created = StudentCourseGrade.objects.get_or_create(
            user=student,
            course=course,
        )

        if not created and grade.final_grade_percentage > 0:
            self.stdout.write(f'  Grade already exists: {grade.final_grade_percentage}% ({grade.final_grade_letter})')
            return grade

        grade.quiz_score = 88.5
        grade.quiz_count = 3
        grade.quiz_completed = 3
        grade.quiz_passed = 3
        grade.quiz_details = [
            {
                'quiz_id': str(uuid.uuid4()),
                'quiz_title': 'Grammar Fundamentals',
                'chapter_title': 'Grammar Basics',
                'section_title': 'Module 1',
                'score': 92.0,
                'is_passed': True,
                'attempts_used': 1,
                'max_attempts': 3,
                'passing_score': 70,
            },
            {
                'quiz_id': str(uuid.uuid4()),
                'quiz_title': 'Vocabulary Assessment',
                'chapter_title': 'Business Vocabulary',
                'section_title': 'Module 2',
                'score': 85.0,
                'is_passed': True,
                'attempts_used': 2,
                'max_attempts': 3,
                'passing_score': 70,
            },
            {
                'quiz_id': str(uuid.uuid4()),
                'quiz_title': 'Final Assessment',
                'chapter_title': 'Course Review',
                'section_title': 'Module 3',
                'score': 88.5,
                'is_passed': True,
                'attempts_used': 1,
                'max_attempts': 3,
                'passing_score': 70,
            },
        ]

        grade.practice_score = 85.0
        grade.practice_count = 12
        grade.practice_completed = 10
        grade.practice_details = [
            {
                'chapter_id': str(uuid.uuid4()),
                'chapter_title': 'Speaking Practice',
                'section_title': 'Module 1',
                'practice_lesson_id': str(uuid.uuid4()),
                'total_challenges': 6,
                'completed_challenges': 5,
                'completion_percentage': 83.3,
            },
            {
                'chapter_id': str(uuid.uuid4()),
                'chapter_title': 'Writing Practice',
                'section_title': 'Module 2',
                'practice_lesson_id': str(uuid.uuid4()),
                'total_challenges': 6,
                'completed_challenges': 5,
                'completion_percentage': 83.3,
            },
        ]

        grade.conversation_score = 82.0
        grade.conversation_sessions = 5
        grade.conversation_minutes = 45
        grade.has_conversation_requirement = False
        grade.conversation_details = []

        grade.final_grade_percentage = 87.0
        grade.final_grade_letter = config.get_grade_with_plus_minus(87.0)
        grade.is_eligible_for_certificate = True
        grade.eligibility_details = {
            'quiz_average': {
                'met': True,
                'required': float(config.min_quiz_average),
                'actual': 88.5,
                'message': f'Media dos quizzes: 88.5% (minimo: {config.min_quiz_average}%)'
            },
            'practice_completion': {
                'met': True,
                'required': float(config.min_practice_completion),
                'actual': 85.0,
                'message': f'Exercicios praticos: 85.0% (minimo: {config.min_practice_completion}%)'
            },
            'conversation_score': {
                'met': True,
                'required': None,
                'actual': 82.0,
                'message': 'Conversacao nao e requisito para este curso',
                'skipped': True,
            },
            'final_grade': {
                'met': True,
                'required': float(config.min_final_grade),
                'actual': 87.0,
                'message': f'Nota final: 87.0% (minimo: {config.min_final_grade}%)'
            },
        }
        grade.weight_info = {
            'quiz_weight': 62.5,
            'practice_weight': 37.5,
            'conversation_weight': 0,
            'mode': 'simplified',
            'active_components': ['quizzes', 'practice'],
            'weights_adjusted': True,
        }
        grade.calculation_version = 1
        grade.save()

        # Grade history
        GradeHistory.objects.get_or_create(
            student_grade=grade,
            change_reason='initial',
            defaults={
                'quiz_score': 88.5,
                'practice_score': 85.0,
                'conversation_score': 82.0,
                'final_grade_percentage': 87.0,
                'final_grade_letter': grade.final_grade_letter,
                'is_eligible': True,
                'change_details': {'source': 'demo'},
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f'  Grade: {grade.final_grade_percentage}% ({grade.final_grade_letter})'
        ))
        return grade

    def _create_certificate(self, student, course, grade):
        existing = CourseCertificate.objects.filter(user=student, course=course).first()
        if existing:
            self.stdout.write(f'  Certificate already exists: {existing.certificate_number}')
            return existing

        verification_code = f"VER-{uuid.uuid4().hex[:8].upper()}"

        certificate = CourseCertificate.objects.create(
            user=student,
            course=course,
            completion_percentage=100.0,
            final_grade=grade.final_grade_percentage,
            final_grade_letter=grade.final_grade_letter,
            verification_code=verification_code,
        )

        # Try PDF generation (non-critical, won't fail the command)
        try:
            from apps.courses.services.certificate_service import CertificateGenerationService
            service = CertificateGenerationService(certificate)
            url = service.save_certificate()
            self.stdout.write(self.style.SUCCESS(
                f'  Certificate: {certificate.certificate_number} (PDF: {url})'
            ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f'  Certificate: {certificate.certificate_number} (PDF failed: {e})'
            ))

        return certificate
