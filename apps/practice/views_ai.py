"""
AI Views for Practice App

Contains AI-powered endpoints for:
- Translation validation and suggestions
- Pronunciation analysis and reference audio generation

These views use external AI services (OpenAI, etc.) for intelligent analysis.
"""

import io
import uuid
import asyncio

from django.utils import timezone
from django.http import HttpResponse
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as status_module

from .models import PracticeChallenge, UserProgress, ChallengeProgress


# =============================================================================
# AI TRANSLATION ENDPOINTS
# =============================================================================

class AITranslationValidationView(APIView):
    """
    POST /api/v1/practice/validate-ai-translation/

    Validate user translation using AI analysis with detailed feedback
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Validate translation using AI with intelligent scoring"""
        from .services.ai_translation import AITranslationValidator

        # Extract request data
        source_text = request.data.get('source_text', '').strip()
        user_translation = request.data.get('user_translation', '').strip()
        challenge_id = request.data.get('challenge_id')
        difficulty_level = request.data.get('difficulty_level', 'intermediate')

        # Validate required fields
        if not source_text or not user_translation:
            return Response(
                {'error': 'source_text and user_translation are required'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        # Validate challenge exists if provided
        challenge = None
        if challenge_id:
            try:
                challenge = PracticeChallenge.objects.get(id=challenge_id)
            except PracticeChallenge.DoesNotExist:
                return Response(
                    {'error': 'Challenge not found'},
                    status=status_module.HTTP_404_NOT_FOUND
                )

        # Get user progress for hearts/points management
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )

        # Check if this is practice mode (challenge already completed)
        is_practice = False
        existing_progress = None
        if challenge:
            existing_progress = ChallengeProgress.objects.filter(
                user=request.user,
                challenge=challenge
            ).first()
            is_practice = existing_progress is not None

        # Check hearts for new challenges
        if not is_practice and user_progress.hearts == 0:
            return Response(
                {'error': 'hearts', 'message': 'No hearts remaining'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        try:
            # Validate translation using AI
            validator = AITranslationValidator()

            # Run async validation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    validator.validate_translation(
                        source_text=source_text,
                        user_translation=user_translation,
                        difficulty_level=difficulty_level
                    )
                )
            finally:
                loop.close()

            # Process results and update progress
            response_data = {
                'success': True,
                'ai_validation': {
                    'semantic_score': result.semantic_score,
                    'fluency_score': result.fluency_score,
                    'fidelity_score': result.fidelity_score,
                    'overall_score': result.overall_score,
                    'is_acceptable': result.is_acceptable,
                    'partial_credit': result.partial_credit
                },
                'feedback': {
                    'message': result.feedback,
                    'explanation': result.explanation,
                    'suggestions': result.suggestions
                },
                'user_answer': user_translation,
                'source_text': source_text
            }

            # Update challenge progress if challenge provided
            if challenge and result.is_acceptable:
                if existing_progress:
                    existing_progress.completed = True
                    existing_progress.save()
                    progress = existing_progress
                else:
                    progress = ChallengeProgress.objects.create(
                        user=request.user,
                        challenge=challenge,
                        completed=True
                    )

                response_data['challenge_progress'] = {
                    'id': str(progress.id),
                    'completed': progress.completed,
                    'completed_at': progress.completed_at
                }

            # Update user progress based on AI result
            if result.is_acceptable:
                if is_practice:
                    # Practice mode: restore hearts and add points
                    user_progress.add_hearts(1)
                else:
                    # New challenge: just add points
                    pass

                # Add points based on AI scoring
                points_earned = result.partial_credit
                user_progress.add_points(points_earned)

                response_data['points_earned'] = points_earned
            else:
                # Incorrect translation: reduce hearts if not practice
                if not is_practice and user_progress.hearts > 0:
                    user_progress.reduce_hearts()

                response_data['points_earned'] = 0

            # Add current user progress to response
            response_data['user_progress'] = {
                'hearts': user_progress.hearts,
                'points': user_progress.points
            }

            return Response(response_data, status=status_module.HTTP_200_OK)

        except Exception as e:
            print(f"AI Translation validation error: {e}")
            return Response(
                {'error': 'Translation validation failed', 'details': str(e)},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateTranslationSuggestionsView(APIView):
    """
    POST /api/v1/practice/generate-translation-suggestions/

    Generate multiple correct translation alternatives for teachers
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate translation alternatives using AI"""
        from .services.ai_translation import AITranslationValidator

        source_text = request.data.get('source_text', '').strip()
        difficulty_level = request.data.get('difficulty_level', 'intermediate')
        count = min(int(request.data.get('count', 3)), 5)  # Limit to 5 suggestions

        if not source_text:
            return Response(
                {'error': 'source_text is required'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        try:
            validator = AITranslationValidator()

            # Run async operation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                suggestions = loop.run_until_complete(
                    validator.generate_translation_suggestions(
                        source_text=source_text,
                        difficulty_level=difficulty_level,
                        count=count
                    )
                )
            finally:
                loop.close()

            return Response({
                'success': True,
                'source_text': source_text,
                'suggestions': suggestions,
                'difficulty_level': difficulty_level
            })

        except Exception as e:
            print(f"Translation suggestions error: {e}")
            return Response(
                {'error': 'Failed to generate suggestions', 'details': str(e)},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# AI PRONUNCIATION ENDPOINTS
# =============================================================================

class GeneratePronunciationExerciseView(APIView):
    """
    POST /api/v1/practice/generate-pronunciation-exercise/

    Generate pronunciation exercise with AI
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate pronunciation exercise using AI"""
        from .services.ai_pronunciation import AIPronunciationAnalyzer

        topic = request.data.get('topic', 'daily conversation')
        difficulty_level = request.data.get('difficulty_level', 'intermediate')
        exercise_type = request.data.get('exercise_type', 'sentence')

        try:
            analyzer = AIPronunciationAnalyzer()

            # Run async operation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                exercise_data = loop.run_until_complete(
                    analyzer.generate_pronunciation_exercise(
                        topic=topic,
                        difficulty_level=difficulty_level,
                        exercise_type=exercise_type
                    )
                )
            finally:
                loop.close()

            return Response({
                'success': True,
                'exercise': exercise_data,
                'generated_at': timezone.now(),
                'parameters': {
                    'topic': topic,
                    'difficulty_level': difficulty_level,
                    'exercise_type': exercise_type
                }
            })

        except Exception as e:
            print(f"Pronunciation exercise generation error: {e}")
            return Response(
                {'error': 'Failed to generate pronunciation exercise', 'details': str(e)},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateReferenceAudioView(APIView):
    """
    POST /api/v1/practice/generate-reference-audio/

    Generate reference audio pronunciation using TTS.
    If save_to_s3=true, uploads to S3 and returns URL.
    Otherwise returns audio binary directly.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate reference audio for pronunciation practice"""
        import boto3
        from .services.ai_pronunciation import AIPronunciationAnalyzer

        text = request.data.get('text', '').strip()
        voice = request.data.get('voice', 'alloy')  # alloy, echo, fable, onyx, nova, shimmer
        save_to_s3 = request.data.get('save_to_s3', False)
        challenge_id = request.data.get('challenge_id', '')

        if not text:
            return Response(
                {'error': 'text is required'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        try:
            analyzer = AIPronunciationAnalyzer()

            # Use sync version directly to avoid async issues
            audio_bytes = analyzer.generate_reference_audio_sync(text=text, voice=voice)

            if not audio_bytes or len(audio_bytes) == 0:
                print(f"TTS returned empty audio bytes for text: {text[:50]}...")
                return Response(
                    {'error': 'Failed to generate audio - empty response from TTS'},
                    status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # If save_to_s3 is requested, upload to S3 and return URL
            if save_to_s3:
                try:
                    s3_client = boto3.client(
                        's3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_S3_REGION_NAME
                    )

                    # Generate unique filename
                    unique_id = uuid.uuid4().hex[:8]
                    filename = f"reference-audio/{challenge_id or 'general'}/{unique_id}.mp3"

                    # Upload to S3
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=filename,
                        Body=audio_bytes,
                        ContentType='audio/mpeg'
                    )

                    # Generate a presigned URL for reading (valid for 1 year)
                    audio_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Key': filename
                        },
                        ExpiresIn=31536000  # 1 year in seconds
                    )

                    return Response({
                        'success': True,
                        'audio_url': audio_url,
                        'message': 'Reference audio generated and saved to S3'
                    })

                except Exception as s3_error:
                    print(f"S3 upload error: {s3_error}")
                    return Response(
                        {'error': 'Failed to upload audio to S3', 'details': str(s3_error)},
                        status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            # Return audio file directly (original behavior)
            response = HttpResponse(audio_bytes, content_type='audio/mpeg')
            response['Content-Disposition'] = f'attachment; filename="reference_{hash(text)}.mp3"'
            return response

        except Exception as e:
            print(f"Reference audio generation error: {e}")
            return Response(
                {'error': 'Failed to generate reference audio', 'details': str(e)},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIPronunciationAnalysisView(APIView):
    """
    POST /api/v1/practice/analyze-ai-pronunciation/

    Analyze student pronunciation using AI (Whisper + GPT-4).

    Request:
        - audio: Audio file (multipart/form-data)
        - expected_text: The text the student should pronounce
        - challenge_id: Optional challenge ID for progress tracking
        - difficulty_level: 'beginner', 'intermediate', or 'advanced'

    Response:
        - ai_analysis: Detailed pronunciation analysis scores
        - feedback: Suggestions and problematic words
        - user_progress: Updated hearts and points
        - ai_analyses_remaining: Remaining AI analyses for today
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Analyze pronunciation using AI with detailed feedback"""
        from .services.ai_pronunciation import AIPronunciationAnalyzer
        from apps.subscriptions.models import UserSubscription

        # Extract request data
        # Support both 'audio' and 'audio_file' for compatibility
        audio_file = request.FILES.get('audio') or request.FILES.get('audio_file')
        expected_text = request.data.get('expected_text', '').strip()
        challenge_id = request.data.get('challenge_id')
        difficulty_level = request.data.get('difficulty_level', 'intermediate')

        # Validate required fields
        if not audio_file or not expected_text:
            return Response(
                {'error': 'audio file and expected_text are required'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        # Check AI analyses limit from subscription
        ai_analyses_remaining = -1  # -1 = unlimited
        try:
            subscription = UserSubscription.objects.select_related('plan').get(user=request.user)
            if subscription.is_active():
                if not subscription.can_use_ai_analysis():
                    return Response(
                        {
                            'error': 'ai_limit',
                            'message': 'Limite diário de análises AI atingido',
                            'ai_analyses_remaining': 0,
                            'limit': subscription.plan.daily_ai_analyses_limit
                        },
                        status=status_module.HTTP_429_TOO_MANY_REQUESTS
                    )
                ai_analyses_remaining = subscription.get_ai_analyses_remaining()
        except UserSubscription.DoesNotExist:
            # No subscription - use default limit of 5
            pass

        # Validate challenge exists if provided
        challenge = None
        if challenge_id:
            try:
                challenge = PracticeChallenge.objects.get(id=challenge_id)
            except PracticeChallenge.DoesNotExist:
                return Response(
                    {'error': 'Challenge not found'},
                    status=status_module.HTTP_404_NOT_FOUND
                )

        # Get user progress for hearts/points management
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )

        # Check if this is practice mode (challenge already completed)
        is_practice = False
        existing_progress = None
        if challenge:
            existing_progress = ChallengeProgress.objects.filter(
                user=request.user,
                challenge=challenge
            ).first()
            is_practice = existing_progress is not None

        # Check hearts for new challenges
        if not is_practice and user_progress.hearts == 0:
            return Response(
                {'error': 'hearts', 'message': 'No hearts remaining'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        try:
            # Convert uploaded file to BytesIO
            audio_bytes = io.BytesIO(audio_file.read())
            audio_bytes.name = audio_file.name

            # Analyze pronunciation using AI
            analyzer = AIPronunciationAnalyzer()

            # Run async analysis in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    analyzer.analyze_pronunciation(
                        audio_file=audio_bytes,
                        expected_text=expected_text,
                        difficulty_level=difficulty_level
                    )
                )
            finally:
                loop.close()

            # Process results and update progress
            response_data = {
                'success': True,
                'ai_analysis': {
                    'transcribed_text': result.transcribed_text,
                    'expected_text': result.expected_text,
                    'pronunciation_score': result.pronunciation_score,
                    'fluency_score': result.fluency_score,
                    'clarity_score': result.clarity_score,
                    'overall_score': result.overall_score,
                    'is_acceptable': result.is_acceptable,
                    'partial_credit': result.partial_credit,
                    'confidence_level': result.confidence_level
                },
                'feedback': {
                    'message': result.feedback,
                    'problematic_words': result.problematic_words,
                    'suggestions': result.suggestions
                }
            }

            # Update challenge progress if challenge provided
            if challenge and result.is_acceptable:
                if existing_progress:
                    existing_progress.completed = True
                    existing_progress.save()
                    progress = existing_progress
                else:
                    progress = ChallengeProgress.objects.create(
                        user=request.user,
                        challenge=challenge,
                        completed=True
                    )

                response_data['challenge_progress'] = {
                    'id': str(progress.id),
                    'completed': progress.completed,
                    'completed_at': progress.completed_at
                }

            # Update user progress based on AI result
            if result.is_acceptable:
                if is_practice:
                    # Practice mode: restore hearts and add points
                    user_progress.add_hearts(1)

                # Add points based on AI scoring
                points_earned = result.partial_credit
                user_progress.add_points(points_earned)

                response_data['points_earned'] = points_earned
            else:
                # Incorrect pronunciation: reduce hearts if not practice
                if not is_practice and user_progress.hearts > 0:
                    user_progress.reduce_hearts()

                response_data['points_earned'] = 0

            # Add current user progress to response
            response_data['user_progress'] = {
                'hearts': user_progress.hearts,
                'points': user_progress.points
            }

            # Use one AI analysis and update remaining count
            try:
                subscription = UserSubscription.objects.select_related('plan').get(user=request.user)
                if subscription.is_active():
                    subscription.use_ai_analysis()
                    ai_analyses_remaining = subscription.get_ai_analyses_remaining()
            except UserSubscription.DoesNotExist:
                pass

            # Add AI analyses remaining to response
            response_data['ai_analyses_remaining'] = ai_analyses_remaining

            return Response(response_data, status=status_module.HTTP_200_OK)

        except Exception as e:
            print(f"AI Pronunciation analysis error: {e}")
            return Response(
                {'error': 'Pronunciation analysis failed', 'details': str(e)},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )
