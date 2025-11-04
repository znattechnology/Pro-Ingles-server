"""
Script para popular conquistas específicas para usuários de teste
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.practice.models import Achievement, UserAchievement, UserProgress, PracticeChallenge, ChallengeProgress
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Popular conquistas para usuários de teste'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email do usuário específico para popular conquistas',
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Popular conquistas para todos os usuários estudantes',
        )

    def handle(self, *args, **options):
        if options['user_email']:
            self.populate_for_user(options['user_email'])
        elif options['all_users']:
            self.populate_for_all_students()
        else:
            # Por padrão, popular para Maria Estudante
            self.populate_for_user('estudante@proenglish.com')

    def populate_for_user(self, email):
        """Popular conquistas para um usuário específico"""
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'🎯 Populando conquistas para: {user.name}')
            
            # Simular progresso de desafios
            self.simulate_challenge_progress(user)
            
            # Criar conquistas baseadas no progresso simulado
            self.create_user_achievements(user)
            
            self.stdout.write(f'✅ Conquistas criadas para {user.name}')
            
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuário com email {email} não encontrado')

    def populate_for_all_students(self):
        """Popular conquistas para todos os estudantes"""
        students = User.objects.filter(role='student')
        
        for student in students:
            self.stdout.write(f'🎯 Populando conquistas para: {student.name}')
            self.simulate_challenge_progress(student)
            self.create_user_achievements(student)
        
        self.stdout.write(f'✅ Conquistas criadas para {students.count()} estudantes')

    def simulate_challenge_progress(self, user):
        """Simular progresso em desafios"""
        challenges = PracticeChallenge.objects.all()
        
        if not challenges:
            self.stdout.write('⚠️ Nenhum desafio encontrado')
            return
        
        # Simular progresso em alguns desafios (entre 5 e 15)
        num_challenges = min(random.randint(5, 15), len(challenges))
        selected_challenges = random.sample(list(challenges), num_challenges)
        
        for challenge in selected_challenges:
            ChallengeProgress.objects.get_or_create(
                user=user,
                challenge=challenge,
                defaults={'completed': True}
            )
        
        self.stdout.write(f'  📚 Progresso simulado em {num_challenges} desafios')

    def create_user_achievements(self, user):
        """Criar conquistas baseadas no progresso do usuário"""
        achievements = Achievement.objects.all()
        
        # Obter progresso do usuário
        user_progress = UserProgress.objects.filter(user=user).first()
        challenges_completed = ChallengeProgress.objects.filter(user=user, completed=True).count()
        
        for achievement in achievements:
            # Verificar se o usuário já tem esta conquista
            user_achievement, created = UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
                defaults={
                    'current_progress': 0,
                    'is_unlocked': False
                }
            )
            
            if not created and user_achievement.is_unlocked:
                continue  # Pular se já desbloqueada
            
            # Determinar progresso baseado no tipo de conquista
            progress = self.calculate_progress(achievement, user, user_progress, challenges_completed)
            
            # Atualizar progresso
            user_achievement.current_progress = progress
            user_achievement.is_unlocked = progress >= achievement.requirement_target
            
            if user_achievement.is_unlocked:
                user_achievement.unlocked_at = user_achievement.unlocked_at or user_achievement.created_at
                
            user_achievement.save()
            
            if user_achievement.is_unlocked:
                self.stdout.write(f'  🏆 Desbloqueou: {achievement.title}')
            else:
                self.stdout.write(f'  📈 Progresso em {achievement.title}: {progress}/{achievement.requirement_target}')

    def calculate_progress(self, achievement, user, user_progress, challenges_completed):
        """Calcular progresso baseado no tipo de conquista"""
        
        if achievement.requirement_type == 'challenges_completed':
            return challenges_completed
        
        elif achievement.requirement_type == 'lessons_completed':
            # Simular lições completadas (baseado em desafios / 3)
            return max(1, challenges_completed // 3)
        
        elif achievement.requirement_type == 'points_earned':
            if user_progress:
                return user_progress.points
            else:
                # Simular pontos baseados em desafios
                return challenges_completed * 10
        
        elif achievement.requirement_type == 'streak_days':
            # Simular sequência de dias (entre 1 e 10)
            return random.randint(1, min(10, achievement.requirement_target))
        
        elif achievement.requirement_type == 'special_beta':
            # Conquista especial para usuários beta
            return 1
        
        elif achievement.requirement_type == 'early_bird':
            # Simular conquista de madrugador (50% chance)
            return 1 if random.random() > 0.5 else 0
        
        else:
            # Progresso padrão aleatório
            return random.randint(0, achievement.requirement_target)

    def show_user_achievements(self, user):
        """Mostrar conquistas do usuário"""
        user_achievements = UserAchievement.objects.filter(user=user).order_by('-is_unlocked', 'achievement__order')
        
        self.stdout.write(f'\n🏆 CONQUISTAS DE {user.name.upper()}:')
        
        unlocked_count = 0
        total_points = 0
        
        for ua in user_achievements:
            status = "🔓 DESBLOQUEADA" if ua.is_unlocked else f"🔒 {ua.current_progress}/{ua.achievement.requirement_target}"
            
            if ua.is_unlocked:
                unlocked_count += 1
                total_points += ua.achievement.points
            
            self.stdout.write(f'  {ua.achievement.icon} {ua.achievement.title} - {status}')
            self.stdout.write(f'    {ua.achievement.description}')
            self.stdout.write(f'    Categoria: {ua.achievement.category} | {ua.achievement.points} pontos')
            self.stdout.write('')
        
        self.stdout.write(f'📊 RESUMO: {unlocked_count}/{user_achievements.count()} conquistas desbloqueadas')
        self.stdout.write(f'💎 PONTOS TOTAIS: {total_points} pontos de conquistas')