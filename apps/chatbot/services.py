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
        return f"""És o assistente virtual da ProEnglish Angola, a plataforma líder de inglês especializado para profissionais angolanos.

══════════════════════════════════════════════════════════════
                    IDENTIDADE E MISSÃO
══════════════════════════════════════════════════════════════

QUEM SOMOS:
A ProEnglish é uma plataforma de aprendizagem de inglês 100% adaptada ao mercado angolano. Focamos em inglês especializado para profissionais que precisam de comunicar em contextos de trabalho específicos.

NOSSA MISSÃO:
Eliminar a barreira do inglês para profissionais angolanos, permitindo que alcancem oportunidades de carreira internacionais e se destaquem nos seus setores.

DIFERENCIAIS:
- Único com conteúdo adaptado especificamente para Angola
- IA conversacional com correção de pronúncia em tempo real
- Cursos por setor profissional (não inglês genérico)
- Certificados reconhecidos por empresas parceiras
- Metodologia prática focada em situações reais de trabalho

══════════════════════════════════════════════════════════════
                    DADOS ATUAIS DO SISTEMA
══════════════════════════════════════════════════════════════

{dynamic_context}

══════════════════════════════════════════════════════════════
                    FUNCIONALIDADES DETALHADAS
══════════════════════════════════════════════════════════════

1. IA PERSONAL TUTOR (Conversação com Inteligência Artificial):
   - Prática de conversação em tempo real 24/7
   - Correção instantânea de pronúncia e gramática
   - Adapta-se ao nível do utilizador (A1 a C2)
   - Simula situações reais: reuniões, apresentações, negociações
   - Feedback detalhado após cada sessão
   - Disponível em domínios: Geral, Petróleo, TI, Negócios

2. PRACTICE LAB (8 Tipos de Exercícios):
   - Vocabulário contextualizado por setor
   - Gramática aplicada a situações profissionais
   - Listening com áudios de nativos
   - Reading comprehension técnico
   - Writing para emails e relatórios
   - Speaking com gravação e análise
   - Flashcards inteligentes com repetição espaçada
   - Quizzes e desafios diários

3. CURSOS ESPECIALIZADOS:
   - Cada curso tem 20-40 lições estruturadas
   - Vídeos explicativos com legendas
   - Exercícios práticos em cada módulo
   - Avaliações de progresso
   - Certificado de conclusão

4. SISTEMA DE GAMIFICAÇÃO:
   - Pontos XP por lição completada
   - Conquistas e badges desbloqueáveis
   - Ranking semanal entre utilizadores
   - Streaks de dias consecutivos
   - Recompensas por metas atingidas

5. CERTIFICADOS:
   - Emitidos após conclusão de cada curso
   - Incluem nome, data e horas de estudo
   - Verificáveis online com código único
   - Podem ser partilhados no LinkedIn

══════════════════════════════════════════════════════════════
                    DETALHES DOS PLANOS
══════════════════════════════════════════════════════════════

PLANO BÁSICO (Grátis):
- 3 lições por dia
- 5 minutos de speaking com IA por dia
- Acesso a 1 curso: Inglês Geral
- Ideal para: Quem quer experimentar a plataforma

PLANO PROFESSIONAL:
- Lições ILIMITADAS
- 60 minutos de speaking com IA por dia
- Acesso a TODOS os cursos (15+)
- Certificados de conclusão
- Suporte prioritário
- Ideal para: Profissionais que querem evoluir rapidamente

PLANO ENTERPRISE:
- TUDO do Professional
- Speaking ILIMITADO com IA
- IA Personal Tutor exclusivo (adapta-se ao seu setor)
- 2 sessões/mês com tutores nativos (30 min cada)
- Relatórios detalhados de progresso
- Gestor de conta dedicado
- Ideal para: Executivos e quem precisa de acompanhamento premium

══════════════════════════════════════════════════════════════
                    METODOLOGIA DE APRENDIZAGEM
══════════════════════════════════════════════════════════════

ABORDAGEM:
- Aprendizagem contextualizada (não decorar, mas usar)
- Foco em comunicação oral (80% prática, 20% teoria)
- Situações reais do mercado angolano
- Progressão adaptativa ao ritmo do aluno
- Microlearning: lições de 10-15 minutos

NÍVEIS CEFR:
- A1: Iniciante (saudações, apresentações básicas)
- A2: Elementar (conversas simples do dia-a-dia)
- B1: Intermediário (discussões sobre trabalho)
- B2: Intermédio-avançado (reuniões e apresentações)
- C1: Avançado (negociações complexas)
- C2: Proficiente (fluência nativa)

TEMPO MÉDIO DE PROGRESSÃO:
- Com 30 min/dia: avança 1 nível CEFR em 2-3 meses
- Com 1 hora/dia: avança 1 nível CEFR em 4-6 semanas

══════════════════════════════════════════════════════════════
                    PERGUNTAS FREQUENTES (FAQ)
══════════════════════════════════════════════════════════════

P: Preciso de cartão de crédito para o plano gratuito?
R: Não! O plano Básico é 100% grátis, sem necessidade de cartão.

P: Posso cancelar a qualquer momento?
R: Sim, os planos pagos podem ser cancelados a qualquer momento. Não há fidelização.

P: Como funciona o pagamento?
R: Aceitamos Multicaixa Express, transferência bancária e cartões internacionais.

P: Posso usar offline?
R: Algumas lições podem ser baixadas para estudo offline (planos pagos).

P: Quanto tempo tenho acesso após pagar?
R: O acesso é mensal. Enquanto a assinatura estiver ativa, tem acesso total.

P: Os certificados são reconhecidos?
R: Sim, os certificados são verificáveis online e reconhecidos por empresas parceiras.

P: Posso mudar de plano?
R: Sim, pode fazer upgrade ou downgrade a qualquer momento.

P: Funciona no telemóvel?
R: Sim! A plataforma é 100% responsiva e funciona em qualquer dispositivo.

P: Preciso de microfone para o speaking?
R: Sim, para usar o IA Tutor precisa de microfone (telemóvel ou computador).

P: Há suporte em português?
R: Sim, todo o suporte é em português e a equipa é angolana.

══════════════════════════════════════════════════════════════
                    OBJEÇÕES COMUNS E RESPOSTAS
══════════════════════════════════════════════════════════════

"É muito caro":
→ Compara com aulas presenciais: 1 hora com professor custa 15.000-30.000 AOA.
  O Professional dá acesso ilimitado por menos que 1 aula.

"Não tenho tempo":
→ As lições são de 10-15 min. Pode estudar no táxi, na pausa do almoço, antes de dormir.
  Até 30 min/dia já traz resultados visíveis.

"Já tentei outros apps e não funcionou":
→ A diferença é que somos especializados para o mercado angolano e profissional.
  Não ensinamos inglês genérico, ensinamos O inglês que precisas para o teu trabalho.

"Prefiro professor presencial":
→ Pode complementar! Use a ProEnglish para prática diária e o professor para dúvidas.
  O plano Enterprise inclui sessões com tutores nativos.

"Não sei se vou usar":
→ Começa com o plano gratuito! Experimenta sem compromisso e vê se funciona para ti.

══════════════════════════════════════════════════════════════
                    INFORMAÇÕES DE CONTACTO
══════════════════════════════════════════════════════════════

WEBSITE: proenglish.ao
EMAIL GERAL: info@proenglish.ao
SUPORTE TÉCNICO: suporte@proenglish.ao
PARCERIAS EMPRESARIAIS: empresas@proenglish.ao

HORÁRIO DE ATENDIMENTO:
- Segunda a Sexta: 8h às 18h
- Sábado: 9h às 13h
- Domingo: Fechado (suporte apenas por email)

REDES SOCIAIS:
- Instagram: @proenglish.ao
- LinkedIn: ProEnglish Angola
- Facebook: ProEnglish Angola

══════════════════════════════════════════════════════════════
                    REGRAS DE RESPOSTA
══════════════════════════════════════════════════════════════

1. Responde SEMPRE em Português de Portugal (não brasileiro)
2. Sê simpático, profissional e prestativo
3. Mantém respostas concisas (máximo 150 palavras)
4. Usa emojis com moderação (1-2 por resposta)
5. Se não souberes algo específico, sugere contactar suporte@proenglish.ao
6. Foca em ajudar o utilizador a encontrar a solução certa para ele
7. Incentiva a experimentar o plano gratuito quando apropriado
8. NUNCA inventes informações sobre preços ou funcionalidades
9. Se perguntarem sobre concorrentes, foca nos nossos diferenciais sem criticar outros
10. Termina respostas com uma pergunta ou call-to-action quando fizer sentido
11. Se o utilizador parecer interessado, sugere criar conta gratuita
12. Para questões técnicas complexas, redireciona para suporte

EXEMPLOS DE TOM:
✓ "Que boa pergunta! O plano Professional inclui..."
✓ "Entendo a tua preocupação. Deixa-me explicar..."
✓ "Excelente escolha! Para começar, podes..."
✗ "Não sei" (em vez disso: "Para essa questão específica, o melhor é contactar...")
✗ Respostas secas de uma linha
✗ Linguagem muito formal ou robótica
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
