# 📋 ProEnglish CMS - Sistema de Gestão de Conteúdo

## 🎯 Visão Geral

O ProEnglish CMS é um sistema completo de gestão de conteúdo para a landing page, desenvolvido especificamente para atender às necessidades do mercado angolano. Permite atualização dinâmica de todos os elementos da página sem necessidade de redeploy.

## 🏗️ Arquitetura

### Backend (Django)
- **Models**: 10 modelos principais para diferentes tipos de conteúdo
- **API REST**: Endpoints completos com Django REST Framework
- **Admin Interface**: Interface administrativa com previsualização
- **Cache**: Sistema de cache Redis/Memcached integrado
- **Middleware**: Otimizações de performance e cache

### Frontend (Next.js)
- **Integration Library**: `/lib/cms.ts` para integração
- **TypeScript Types**: Tipagem completa dos dados
- **Fallback System**: Dados de fallback caso CMS não esteja disponível
- **SSG/ISR**: Geração estática com revalidação incremental

## 📊 Modelos de Dados

### 1. LandingPageSettings
Configurações gerais do site:
- Informações básicas (título, descrição, keywords)
- Contatos (email, telefone, WhatsApp)
- Redes sociais
- Analytics (Google Analytics, Facebook Pixel)
- Modo manutenção

### 2. HeroSection
Seção principal da landing page:
- Badge promocional
- Headlines principais
- Descrição
- Botões CTA
- Prova social e ratings
- Mídia (imagens/vídeos)

### 3. StatItem
Estatísticas exibidas:
- Valor (ex: "10K+")
- Label (ex: "Angolanos aprendendo")
- Seção onde aparece
- Ícone opcional

### 4. Company
Empresas parceiras:
- Nome e logo
- Categoria (petróleo, bancário, telecom, etc.)
- Configurações de exibição (hero, ticker)
- Website e descrição

### 5. ServiceItem
Serviços oferecidos:
- Título e descrição
- Metadados (estudantes, nível, duração)
- Features e tópicos do currículo
- Empresas alvo
- Configurações visuais

### 6. PricingTier
Planos de preços:
- Informações básicas (título, ícone)
- Preços (mensal/anual em AOA)
- Features incluídas
- Benefícios específicos para Angola
- Design (popular, inverso)

### 7. Feature
Funcionalidades da plataforma:
- Título e descrição
- Ícone e gradientes
- Benefícios e casos de uso
- Configuração de layout (grid columns)

### 8. Testimonial
Depoimentos de clientes:
- Informações do cliente
- Texto e resultado alcançado
- Rating e verificação
- Setor e localização

### 9. FAQItem
Perguntas frequentes:
- Pergunta e resposta
- Categoria
- Keywords para SEO

### 10. CallToAction
Chamadas para ação:
- Títulos e descrições
- Botões (primário/secundário)
- Posicionamento na página
- Elementos visuais

### 11. SeoSettings
Configurações SEO por página:
- Meta tags
- Open Graph
- Twitter Cards
- Schema.org
- Configurações de indexação

## 🔌 API Endpoints

### Endpoints Principais
```
GET  /api/v1/cms/landing-page-data/    # Todos os dados em uma request
GET  /api/v1/cms/settings/             # Configurações
GET  /api/v1/cms/hero/                 # Seções hero
GET  /api/v1/cms/services/             # Serviços
GET  /api/v1/cms/pricing/              # Planos de preços
GET  /api/v1/cms/testimonials/         # Depoimentos
POST /api/v1/cms/clear-cache/          # Limpar cache (admin)
GET  /api/v1/cms/stats-summary/        # Estatísticas do CMS
GET  /api/v1/cms/health/               # Health check
POST /api/v1/cms/preview/              # Preview de mudanças
```

### Resposta Principal
```json
{
  "settings": { ... },
  "hero": { ... },
  "hero_stats": [ ... ],
  "hero_companies": [ ... ],
  "ticker_companies": [ ... ],
  "services": [ ... ],
  "pricing_tiers": [ ... ],
  "features": [ ... ],
  "testimonials": [ ... ],
  "faqs": [ ... ],
  "ctas": [ ... ],
  "seo": { ... },
  "last_updated": "2025-09-13T04:59:31.998076Z"
}
```

## 🖥️ Interface Admin

### Acesso
- URL: `http://localhost:8001/admin/cms/`
- Requer login de administrador Django

### Funcionalidades
- **CRUD Completo**: Criar, editar, deletar todos os conteúdos
- **Preview**: Visualização de imagens e conteúdo
- **Ordenação**: Drag & drop para reordenar elementos
- **Filtros**: Filtros avançados por categoria, status, etc.
- **Busca**: Busca em texto completo
- **Validação**: Validação de dados em tempo real

### Configurações Especiais
- **LandingPageSettings**: Apenas uma instância permitida
- **Order Fields**: Campos de ordem para controlar sequência
- **Active Flags**: Flags para ativar/desativar conteúdo
- **Image Previews**: Preview de imagens no admin

## 💻 Integração Frontend

### Instalação
```typescript
// lib/cms.ts já criado
import { fetchLandingPageData, CMSLandingPageData } from '@/lib/cms';
```

### Uso Básico
```typescript
// Em um Server Component
export default async function LandingPage() {
  const cmsData = await fetchLandingPageData();
  
  if (!cmsData) {
    // Fallback para dados estáticos
    return <StaticLandingPage />;
  }

  return (
    <div>
      <Hero data={cmsData.hero} stats={cmsData.hero_stats} />
      <Services data={cmsData.services} />
      <Pricing data={cmsData.pricing_tiers} />
      {/* ... outros componentes */}
    </div>
  );
}
```

### Transformações de Dados
```typescript
// Transformar dados do CMS para componentes existentes
const exploreWorlds = transformServicesToExploreWorlds(cmsData);
const pricingTiers = transformPricingTiers(cmsData);
```

### Cache e Revalidação
```typescript
// Next.js ISR - revalida a cada 15 minutos
export const revalidate = 900;

// Ou fetch com cache customizado
const response = await fetch(`${CMS_API_BASE}/landing-page-data/`, {
  next: { revalidate: 900 }
});
```

## ⚡ Cache e Performance

### Sistema de Cache
- **Redis/Memcached**: Cache de dados da API
- **CDN**: Cache de assets estáticos
- **Browser Cache**: Headers de cache apropriados
- **Middleware**: Cache automático de responses

### Estratégias
1. **Endpoint Principal**: Cache de 15 minutos
2. **Seções Individuais**: Cache de 10 minutos
3. **Imagens**: Cache de 24 horas
4. **Cache Busting**: Timestamp de última atualização

### Headers de Cache
```
Cache-Control: public, max-age=900
X-Cache: HIT/MISS
X-Response-Time: 0.123s
Vary: Accept-Encoding
```

## 🛠️ Comandos Úteis

### Desenvolvimento
```bash
# Criar migrações
python manage.py makemigrations cms

# Aplicar migrações
python manage.py migrate

# Popular com dados iniciais
python manage.py populate_cms

# Limpar cache
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Criar superuser
python manage.py createsuperuser
```

### API Testing
```bash
# Testar endpoint principal
curl "http://localhost:8001/api/v1/cms/landing-page-data/"

# Testar health check
curl "http://localhost:8001/api/v1/cms/health/"

# Limpar cache (requer autenticação)
curl -X POST "http://localhost:8001/api/v1/cms/clear-cache/" \
  -H "Authorization: Bearer <token>"
```

## 📱 Modo Manutenção

### Ativação
1. Admin → Landing Page Settings
2. Marcar "Maintenance Mode"
3. Definir mensagem personalizada
4. Salvar

### Comportamento
- Usuários normais: Veem página de manutenção
- Admins: Acesso normal para testes
- API: Retorna status 503 com mensagem

## 🔒 Segurança

### Permissões
- **Leitura**: Público (API endpoints GET)
- **Escrita**: Apenas administradores
- **Cache**: Diferenciado por tipo de usuário
- **Middleware**: Proteção contra ataques

### Validação
- **Input Sanitization**: Dados limpos antes de salvar
- **Image Validation**: Validação de tipos de arquivo
- **XSS Protection**: Escape de conteúdo HTML
- **CSRF Protection**: Tokens CSRF em forms

## 📈 Monitoramento

### Métricas Disponíveis
- **Response Time**: Tempo de resposta das APIs
- **Cache Hit Rate**: Taxa de acerto do cache
- **Error Rate**: Taxa de erro
- **Content Updates**: Frequência de atualizações

### Logs
```python
# Performance logs
logger.warning(f"Slow CMS request: {request.path} took {duration:.3f}s")

# Cache logs
logger.info(f"Cache HIT: {cache_key}")
logger.info(f"Cache MISS: {cache_key}")
```

## 🚀 Deploy e Produção

### Variáveis de Ambiente
```bash
# Frontend
NEXT_PUBLIC_CMS_API_URL=https://api.proenglish.ao/api/v1/cms

# Backend
CORS_ALLOWED_ORIGINS=https://proenglish.ao,https://www.proenglish.ao
USE_S3=True
REDIS_URL=redis://redis:6379/0
```

### Checklist de Deploy
- [ ] Migrações aplicadas
- [ ] Dados iniciais populados
- [ ] Cache configurado (Redis)
- [ ] CDN configurado para assets
- [ ] Monitoramento ativo
- [ ] Backup de dados configurado

## 🔧 Manutenção

### Tarefas Regulares
1. **Backup**: Backup diário do banco de dados
2. **Cache Cleanup**: Limpeza de cache expirado
3. **Image Optimization**: Otimização de imagens
4. **Performance Review**: Análise de performance

### Troubleshooting
```bash
# Verificar saúde da API
curl "http://localhost:8001/api/v1/cms/health/"

# Verificar cache
python manage.py shell -c "
from django.core.cache import cache;
print('Cache working:', cache.get('test') is None)
"

# Verificar logs
tail -f logs/django.log | grep cms
```

## 📚 Próximos Passos

### Melhorias Futuras
1. **A/B Testing**: Sistema de testes A/B
2. **Analytics**: Integração com Google Analytics
3. **Multi-idioma**: Suporte a múltiplos idiomas
4. **Workflow**: Sistema de aprovação de conteúdo
5. **Versionamento**: Histórico de mudanças
6. **API Rate Limiting**: Controle de rate limiting
7. **Real-time Updates**: WebSockets para updates em tempo real

### Integrações
- **CDN**: CloudFlare/AWS CloudFront
- **Storage**: AWS S3 para assets
- **Monitoring**: Sentry/DataDog
- **Analytics**: Google Analytics 4
- **Email**: SendGrid/AWS SES

---

## 📞 Suporte

Para dúvidas sobre o CMS:
1. Consulte esta documentação
2. Verifique os logs de erro
3. Teste os endpoints de health check
4. Entre em contato com a equipe de desenvolvimento

**Status**: ✅ Produção Ready
**Versão**: 1.0.0
**Última Atualização**: Setembro 2025