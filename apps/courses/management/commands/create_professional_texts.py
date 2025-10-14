"""
Django management command to create professional content for all Text chapters.
"""
import json
import random
from django.core.management.base import BaseCommand
from apps.courses.models import Chapter


class Command(BaseCommand):
    help = 'Create professional content for all Text chapters'

    def handle(self, *args, **options):
        self.stdout.write('📚 Criando conteúdo profissional para capítulos Text...')

        # Buscar todos os capítulos do tipo Text
        text_chapters = Chapter.objects.filter(type='Text')
        
        if not text_chapters.exists():
            self.stdout.write('⚠️ Nenhum capítulo Text encontrado')
            return

        # Pool de conteúdos educacionais profissionais
        educational_content = {
            'grammar_lessons': [
                {
                    'title': 'English Verb Tenses: A Complete Guide',
                    'category': 'Grammar',
                    'content': '''
<div class="lesson-content">
    <h2>Understanding English Verb Tenses</h2>
    
    <p>English verb tenses are fundamental building blocks of effective communication. They help us express when actions happen and their relationship to time.</p>
    
    <h3>1. Present Simple</h3>
    <p><strong>Form:</strong> Subject + base verb (+ s/es for third person singular)</p>
    <p><strong>Uses:</strong></p>
    <ul>
        <li>Habitual actions: "I drink coffee every morning."</li>
        <li>General truths: "The sun rises in the east."</li>
        <li>Scheduled events: "The train leaves at 8 PM."</li>
    </ul>
    
    <div class="example-box">
        <h4>Examples:</h4>
        <p>✅ "She <em>works</em> at a bank."</p>
        <p>✅ "They <em>play</em> tennis every weekend."</p>
    </div>
    
    <h3>2. Present Continuous</h3>
    <p><strong>Form:</strong> Subject + am/is/are + verb-ing</p>
    <p><strong>Uses:</strong></p>
    <ul>
        <li>Actions happening now: "I am writing a letter."</li>
        <li>Temporary situations: "She is staying with friends."</li>
        <li>Future arrangements: "We are meeting tomorrow."</li>
    </ul>
    
    <div class="practice-section">
        <h4>💡 Quick Practice:</h4>
        <p>Try forming sentences using these prompts:</p>
        <ol>
            <li>Your current activity (present continuous)</li>
            <li>Your daily routine (present simple)</li>
            <li>A scheduled event (present simple)</li>
        </ol>
    </div>
    
    <h3>Key Takeaways</h3>
    <div class="summary-box">
        <p>Remember: Choose your tense based on <em>when</em> and <em>how often</em> the action occurs. Present simple for habits and facts, present continuous for ongoing actions.</p>
    </div>
</div>
                    ''',
                    'reading_time': 8,
                    'difficulty': 'intermediate'
                },
                {
                    'title': 'Mastering English Articles: A, An, The',
                    'category': 'Grammar',
                    'content': '''
<div class="lesson-content">
    <h2>English Articles: Your Guide to A, An, and The</h2>
    
    <p>Articles are small words that make a big difference in English. They help specify whether we're talking about something general or specific.</p>
    
    <h3>Indefinite Articles: A and An</h3>
    <p>Use <strong>a</strong> and <strong>an</strong> when referring to something for the first time or something general.</p>
    
    <div class="rule-box">
        <h4>The Rule:</h4>
        <ul>
            <li><strong>A</strong> + consonant sounds: "a book", "a university" (you-niversity)</li>
            <li><strong>An</strong> + vowel sounds: "an apple", "an hour" (silent h)</li>
        </ul>
    </div>
    
    <h3>Definite Article: The</h3>
    <p>Use <strong>the</strong> when both speaker and listener know what you're referring to.</p>
    
    <div class="example-box">
        <h4>Examples:</h4>
        <p>🔸 "I saw <em>a</em> movie yesterday. <em>The</em> movie was fantastic!" (first mention → specific reference)</p>
        <p>🔸 "Please close <em>the</em> door." (both know which door)</p>
    </div>
    
    <h3>No Article (Zero Article)</h3>
    <p>Sometimes we don't use any article:</p>
    <ul>
        <li>General plural nouns: "Dogs are loyal animals."</li>
        <li>Abstract concepts: "Love is important."</li>
        <li>Most proper nouns: "Paris is beautiful."</li>
    </ul>
    
    <div class="practice-section">
        <h4>🎯 Practice Exercise:</h4>
        <p>Fill in the blanks with a, an, the, or no article:</p>
        <ol>
            <li>"I need ___ advice about ___ job interview."</li>
            <li>"___ cat is sleeping on ___ sofa."</li>
            <li>"She's ___ engineer at ___ company downtown."</li>
        </ol>
        <small><em>Answers: 1) no article, the; 2) The, the; 3) an, a</em></small>
    </div>
</div>
                    ''',
                    'reading_time': 6,
                    'difficulty': 'beginner'
                }
            ],
            'vocabulary_lessons': [
                {
                    'title': 'Business English Vocabulary Essentials',
                    'category': 'Vocabulary',
                    'content': '''
<div class="lesson-content">
    <h2>Essential Business English Vocabulary</h2>
    
    <p>Professional communication requires precise vocabulary. Master these essential business terms to sound confident and professional.</p>
    
    <h3>📊 Meeting & Presentation Terms</h3>
    <div class="vocab-section">
        <div class="term">
            <strong>Agenda</strong> /əˈdʒendə/ <br>
            <em>Definition:</em> A list of items to be discussed at a meeting<br>
            <em>Example:</em> "Let's review the agenda before we start."
        </div>
        
        <div class="term">
            <strong>Stakeholder</strong> /ˈsteɪkhoʊldər/ <br>
            <em>Definition:</em> A person with an interest or concern in something<br>
            <em>Example:</em> "We need to consider all stakeholders in this decision."
        </div>
        
        <div class="term">
            <strong>Deadline</strong> /ˈdedlaɪn/ <br>
            <em>Definition:</em> The latest time or date by which something should be completed<br>
            <em>Example:</em> "The project deadline is next Friday."
        </div>
    </div>
    
    <h3>💼 Finance & Strategy Terms</h3>
    <div class="vocab-section">
        <div class="term">
            <strong>ROI (Return on Investment)</strong><br>
            <em>Definition:</em> A measure of the efficiency of an investment<br>
            <em>Example:</em> "The marketing campaign showed excellent ROI."
        </div>
        
        <div class="term">
            <strong>Leverage</strong> /ˈlevərɪdʒ/ <br>
            <em>Definition:</em> To use something to maximum advantage<br>
            <em>Example:</em> "We can leverage our social media presence to reach more customers."
        </div>
    </div>
    
    <h3>🤝 Professional Phrases</h3>
    <div class="phrase-box">
        <h4>Formal Email Phrases:</h4>
        <ul>
            <li><strong>"I'm writing to follow up on..."</strong> - To continue a previous conversation</li>
            <li><strong>"Please don't hesitate to contact me..."</strong> - Offering further assistance</li>
            <li><strong>"I look forward to hearing from you"</strong> - Professional closing</li>
        </ul>
    </div>
    
    <div class="practice-section">
        <h4>🎯 Application Exercise:</h4>
        <p>Write a short email using at least 3 of the terms you learned. Imagine you're updating a colleague about a project status.</p>
    </div>
    
    <div class="tip-box">
        <h4>💡 Pro Tip:</h4>
        <p>Practice using these terms in context. Don't just memorize definitions—create your own sentences and scenarios!</p>
    </div>
</div>
                    ''',
                    'reading_time': 10,
                    'difficulty': 'intermediate'
                }
            ],
            'culture_lessons': [
                {
                    'title': 'English-Speaking Cultures Around the World',
                    'category': 'Culture',
                    'content': '''
<div class="lesson-content">
    <h2>Exploring English-Speaking Cultures</h2>
    
    <p>English is spoken as a native language in many countries, each with unique cultural aspects that influence communication styles and social norms.</p>
    
    <h3>🇺🇸 United States</h3>
    <div class="culture-section">
        <h4>Communication Style:</h4>
        <ul>
            <li><strong>Direct:</strong> Americans tend to be straightforward in communication</li>
            <li><strong>Informal:</strong> First names are used quickly in professional settings</li>
            <li><strong>Enthusiastic:</strong> Positive language and expressions are common</li>
        </ul>
        
        <div class="example-box">
            <p><strong>Typical greeting:</strong> "Hi there! How's it going?"</p>
            <p><strong>Making requests:</strong> "Could you please send me that report?"</p>
        </div>
    </div>
    
    <h3>🇬🇧 United Kingdom</h3>
    <div class="culture-section">
        <h4>Communication Style:</h4>
        <ul>
            <li><strong>Indirect:</strong> Often use understatement and subtle communication</li>
            <li><strong>Polite:</strong> "Please" and "thank you" are used frequently</li>
            <li><strong>Self-deprecating:</strong> Modest about achievements</li>
        </ul>
        
        <div class="example-box">
            <p><strong>Typical greeting:</strong> "Good morning! How are you today?"</p>
            <p><strong>Disagreeing politely:</strong> "I see your point, however, I wonder if we might consider..."</p>
        </div>
    </div>
    
    <h3>🇦🇺 Australia</h3>
    <div class="culture-section">
        <h4>Communication Style:</h4>
        <ul>
            <li><strong>Relaxed:</strong> Casual and friendly approach</li>
            <li><strong>Humorous:</strong> Jokes and banter are common</li>
            <li><strong>Egalitarian:</strong> Less formal hierarchy in communication</li>
        </ul>
        
        <div class="example-box">
            <p><strong>Typical greeting:</strong> "G'day! How ya going?"</p>
            <p><strong>Casual response:</strong> "No worries, mate!"</p>
        </div>
    </div>
    
    <h3>🌍 Cross-Cultural Communication Tips</h3>
    <div class="tips-section">
        <ol>
            <li><strong>Observe:</strong> Pay attention to how native speakers interact</li>
            <li><strong>Ask:</strong> When unsure, it's okay to ask about cultural norms</li>
            <li><strong>Adapt:</strong> Adjust your communication style to match the context</li>
            <li><strong>Be patient:</strong> Cultural understanding takes time to develop</li>
        </ol>
    </div>
    
    <div class="reflection-box">
        <h4>🤔 Cultural Reflection:</h4>
        <p>Think about your own culture. How does it influence your communication style? What similarities and differences do you notice with English-speaking cultures?</p>
    </div>
</div>
                    ''',
                    'reading_time': 12,
                    'difficulty': 'intermediate'
                }
            ]
        }

        # Contar quantos textos foram criados
        updated_count = 0

        for chapter in text_chapters:
            # Selecionar tipo de conteúdo baseado no contexto do capítulo
            content_lower = (chapter.content + chapter.title).lower()
            
            if any(word in content_lower for word in ['grammar', 'verb', 'tense', 'article', 'sentence']):
                content_type = 'grammar_lessons'
            elif any(word in content_lower for word in ['vocabulary', 'words', 'business', 'professional']):
                content_type = 'vocabulary_lessons'
            elif any(word in content_lower for word in ['culture', 'country', 'communication', 'social']):
                content_type = 'culture_lessons'
            else:
                # Default to grammar lessons
                content_type = 'grammar_lessons'

            # Selecionar conteúdo do tipo escolhido
            available_content = educational_content.get(content_type, educational_content['grammar_lessons'])
            selected_content = random.choice(available_content)

            # Atualizar o conteúdo do capítulo
            enhanced_content = f'''
<div class="professional-lesson">
    <div class="lesson-header">
        <h1>{selected_content['title']}</h1>
        <div class="lesson-meta">
            <span class="category">{selected_content['category']}</span>
            <span class="reading-time">📖 {selected_content['reading_time']} min read</span>
            <span class="difficulty">🎯 {selected_content['difficulty'].title()}</span>
        </div>
    </div>
    
    <div class="lesson-body">
        {selected_content['content']}
    </div>
    
    <div class="lesson-footer">
        <div class="progress-section">
            <h4>📈 Your Learning Journey</h4>
            <p>Complete this lesson to advance your understanding of {selected_content['category'].lower()}. Take notes on key concepts and practice the examples provided.</p>
        </div>
        
        <div class="next-steps">
            <h4>🎯 What's Next?</h4>
            <ul>
                <li>Review the key concepts covered in this lesson</li>
                <li>Practice with the examples provided</li>
                <li>Apply what you learned in real conversations</li>
                <li>Move on to the next chapter when you feel confident</li>
            </ul>
        </div>
    </div>
</div>

<style>
.professional-lesson {{
    max-width: 800px;
    margin: 0 auto;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
    color: #e2e8f0;
}}

.lesson-header {{
    border-bottom: 2px solid #6366f1;
    padding-bottom: 1rem;
    margin-bottom: 2rem;
}}

.lesson-meta {{
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;
    font-size: 0.875rem;
}}

.category, .reading-time, .difficulty {{
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.3);
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
}}

.lesson-body h2 {{
    color: #a78bfa;
    border-bottom: 1px solid rgba(167, 139, 250, 0.3);
    padding-bottom: 0.5rem;
}}

.lesson-body h3 {{
    color: #c084fc;
    margin-top: 2rem;
}}

.example-box, .rule-box, .vocab-section, .practice-section, .tip-box, .phrase-box, .culture-section, .tips-section, .reflection-box {{
    background: rgba(30, 41, 59, 0.5);
    border-left: 4px solid #6366f1;
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0.5rem;
}}

.term {{
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: rgba(15, 23, 42, 0.3);
    border-radius: 0.5rem;
}}

.lesson-footer {{
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid rgba(99, 102, 241, 0.3);
}}

.progress-section, .next-steps {{
    margin-bottom: 1.5rem;
}}
</style>
            '''

            chapter.content = enhanced_content
            chapter.save()
            
            updated_count += 1
            content_title = selected_content['title']
            content_category = selected_content['category']
            self.stdout.write(f'  ✅ Conteúdo criado para: {chapter.title} ({content_category}: {content_title})')

        self.stdout.write(
            self.style.SUCCESS(f'🎉 {updated_count} conteúdos profissionais criados com sucesso!')
        )