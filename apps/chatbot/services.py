"""
Chatbot Service - Intelligent Landing Page Assistant
Provides context-aware responses using OpenAI with dynamic database data
"""

import openai
import hashlib
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Serviço de Chatbot Inteligente para Landing Page

    Características:
    - Busca dados dinâmicos da base de dados
    - Usa GPT-3.5-turbo para respostas económicas
    - Cache de respostas para reduzir custos
    - Contexto de conversa mantido
    """

    CACHE_TTL = 3600  # 1 hora
    MAX_HISTORY = 10  # Últimas 10 mensagens

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def get_dynamic_context(self) -> str:
        """
        Busca dados dinâmicos da base de dados para contexto
        """
        context_parts = []

        # 1. Buscar planos de subscrição
        try:
            from apps.subscriptions.models import SubscriptionPlan
            plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')

            if plans.exists():
                plans_text = "PLANOS DISPONÍVEIS:\n"
                for plan in plans:
                    features = plan.features if isinstance(plan.features, list) else []
                    features_text = ", ".join(features[:5]) if features else "Recursos incluídos"
                    plans_text += f"- {plan.name}: {plan.price:,.0f} AOA/{plan.billing_cycle} - {features_text}\n"
                context_parts.append(plans_text)
        except Exception as e:
            logger.warning(f"Erro ao buscar planos: {e}")
            context_parts.append("""
PLANOS DISPONÍVEIS:
- Básico: Grátis - 3 lições/dia, 5 min speaking com IA
- Professional: 14.950 AOA/mês - Ilimitado, 15+ cursos, certificados
- Enterprise: 24.950 AOA/mês - Tudo + tutor exclusivo + sessões com nativos
""")

        # 2. Buscar cursos publicados
        try:
            from apps.courses.models import Course
            courses = Course.objects.filter(is_published=True).order_by('-created_at')[:10]

            if courses.exists():
                courses_text = "CURSOS DISPONÍVEIS:\n"
                for course in courses:
                    courses_text += f"- {course.title}\n"
                context_parts.append(courses_text)
        except Exception as e:
            logger.warning(f"Erro ao buscar cursos: {e}")
            context_parts.append("""
CURSOS DISPONÍVEIS:
- Inglês para Petróleo & Gás
- Inglês Bancário e Financeiro
- Inglês para Tecnologia e TI
- Inglês Executivo e Negócios
- Business English Geral
- Inglês para Atendimento ao Cliente
""")

        # 3. Estatísticas da plataforma (se disponíveis)
        try:
            from apps.users.models import User
            from apps.courses.models import Course, Enrollment

            total_users = User.objects.filter(is_active=True).count()
            total_courses = Course.objects.filter(is_published=True).count()

            if total_users > 0:
                stats_text = f"""
ESTATÍSTICAS DA PLATAFORMA:
- Utilizadores ativos: {total_users}+
- Cursos disponíveis: {total_courses}
"""
                context_parts.append(stats_text)
        except Exception as e:
            logger.warning(f"Erro ao buscar estatísticas: {e}")

        return "\n".join(context_parts)

    def build_system_prompt(self, dynamic_context: str) -> str:
        """
        Constrói o system prompt completo com contexto dinâmico
        """
        return f"""És o assistente virtual da ProEnglish Angola, uma plataforma de aprendizagem de inglês especializado para profissionais angolanos.

SOBRE A PROENGLISH:
- Plataforma de inglês especializado para o mercado de trabalho angolano
- Foco em setores: Petróleo & Gás, Banca, Tecnologia, Executivo
- IA Personal Tutor para prática de conversação em tempo real
- 8 tipos de exercícios interativos
- Certificados de conclusão
- Metodologia adaptada ao contexto angolano

{dynamic_context}

FUNCIONALIDADES PRINCIPAIS:
- IA Tutor: Conversação em tempo real com correção de pronúncia
- Practice Lab: Exercícios variados (vocabulário, gramática, listening, etc.)
- Cursos Especializados: Conteúdo específico para cada setor profissional
- Gamificação: Pontos, conquistas e rankings
- Certificados: Reconhecimento de conclusão de cursos

CONTACTOS:
- Website: proenglish.ao
- Email: suporte@proenglish.ao
- Horário de suporte: Segunda a Sexta, 8h às 18h

REGRAS DE RESPOSTA:
1. Responde SEMPRE em Português de Portugal
2. Sê simpático, profissional e prestativo
3. Mantém respostas concisas (máximo 150 palavras)
4. Usa emojis com moderação para tornar a conversa agradável
5. Se não souberes algo específico, sugere contactar o suporte
6. Foca em ajudar o utilizador a encontrar a solução certa
7. Incentiva a experimentar a plataforma quando apropriado
8. Nunca inventes informações sobre preços ou funcionalidades
"""

    def get_cache_key(self, message: str, history_hash: str) -> str:
        """Gera chave de cache única"""
        content = f"{message.lower().strip()}:{history_hash}"
        return f"chatbot:v1:{hashlib.md5(content.encode()).hexdigest()}"

    def get_history_hash(self, history: List[Dict]) -> str:
        """Gera hash do histórico para cache"""
        if not history:
            return "empty"
        # Usa últimas 3 mensagens para o hash
        recent = history[-3:] if len(history) > 3 else history
        content = str([(m.get('role'), m.get('content', '')[:50]) for m in recent])
        return hashlib.md5(content.encode()).hexdigest()[:8]

    async def chat(self,
                   message: str,
                   conversation_history: Optional[List[Dict]] = None,
                   session_id: Optional[str] = None) -> Dict:
        """
        Processa mensagem do utilizador e retorna resposta inteligente

        Args:
            message: Mensagem do utilizador
            conversation_history: Histórico da conversa (opcional)
            session_id: ID da sessão para tracking (opcional)

        Returns:
            Dict com resposta e metadata
        """
        try:
            history = conversation_history or []
            history_hash = self.get_history_hash(history)

            # Verificar cache
            cache_key = self.get_cache_key(message, history_hash)
            cached_response = cache.get(cache_key)

            if cached_response and not history:  # Só usa cache se não há histórico
                logger.info(f"💬 Chatbot: Cache hit para mensagem")
                return {
                    'response': cached_response,
                    'cached': True,
                    'session_id': session_id
                }

            # Buscar contexto dinâmico
            dynamic_context = self.get_dynamic_context()
            system_prompt = self.build_system_prompt(dynamic_context)

            # Construir mensagens para a API
            messages = [{"role": "system", "content": system_prompt}]

            # Adicionar histórico (limitado)
            if history:
                for msg in history[-self.MAX_HISTORY:]:
                    messages.append({
                        "role": msg.get('role', 'user'),
                        "content": msg.get('content', '')
                    })

            # Adicionar mensagem atual
            messages.append({"role": "user", "content": message})

            # Chamar OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Económico e rápido
                messages=messages,
                max_tokens=250,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )

            ai_response = response.choices[0].message.content.strip()

            # Guardar em cache (apenas para mensagens sem histórico complexo)
            if len(history) <= 2:
                cache.set(cache_key, ai_response, self.CACHE_TTL)

            logger.info(f"💬 Chatbot: Resposta gerada ({response.usage.total_tokens} tokens)")

            return {
                'response': ai_response,
                'cached': False,
                'tokens_used': response.usage.total_tokens,
                'session_id': session_id
            }

        except Exception as e:
            logger.error(f"❌ Chatbot error: {str(e)}")
            return {
                'response': "Desculpe, ocorreu um erro ao processar a sua mensagem. Por favor, tente novamente ou contacte-nos em suporte@proenglish.ao",
                'error': True,
                'session_id': session_id
            }

    def chat_sync(self,
                  message: str,
                  conversation_history: Optional[List[Dict]] = None,
                  session_id: Optional[str] = None) -> Dict:
        """
        Versão síncrona do chat para uso em views Django normais
        """
        import asyncio

        # Criar event loop se necessário
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Se já estamos num contexto async, executar diretamente
        if loop.is_running():
            # Criar uma nova thread para executar o async
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.chat(message, conversation_history, session_id)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                self.chat(message, conversation_history, session_id)
            )


# Instância singleton
chatbot_service = ChatbotService()
