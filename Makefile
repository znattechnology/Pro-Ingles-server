# Makefile for Tuwi Backend Testing and Development

.PHONY: help test test-unit test-integration test-coverage test-fast test-security test-performance
.DEFAULT_GOAL := help

# Variables
PYTHON = python
PYTEST = pytest
COVERAGE = coverage
DJANGO_SETTINGS = core.test_settings
MANAGE = $(PYTHON) manage.py
DOCKER = docker
DOCKER_COMPOSE = docker-compose

help: ## Show this help message
	@echo "🧪 Tuwi Backend Testing Commands"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# TEST EXECUTION COMMANDS
# =============================================================================

test: ## Run all tests
	@echo "🚀 Running all tests..."
	$(PYTEST) --tb=short --disable-warnings

test-unit: ## Run unit tests only
	@echo "🔬 Running unit tests..."
	$(PYTEST) tests/unit/ --tb=short -v

test-integration: ## Run integration tests only
	@echo "🔗 Running integration tests..."
	$(PYTEST) tests/integration/ --tb=short -v

test-fast: ## Run fast tests (exclude slow tests)
	@echo "⚡ Running fast tests..."
	$(PYTEST) -m "not slow" --tb=short

test-critical: ## Run critical business logic tests
	@echo "🎯 Running critical tests..."
	$(PYTEST) -m "critical" --tb=short -v

test-api: ## Run API tests only
	@echo "🌐 Running API tests..."
	$(PYTEST) -m "api" --tb=short -v

test-auth: ## Run authentication tests
	@echo "🔐 Running authentication tests..."
	$(PYTEST) -m "auth" --tb=short -v

test-security: ## Run security tests
	@echo "🔒 Running security tests..."
	$(PYTEST) -m "security" --tb=short -v

test-performance: ## Run performance tests
	@echo "⚡ Running performance tests..."
	$(PYTEST) -m "performance" --tb=short -v

# =============================================================================
# COVERAGE COMMANDS
# =============================================================================

test-coverage: ## Run tests with coverage report
	@echo "📊 Running tests with coverage..."
	$(COVERAGE) run --source='apps' -m pytest
	$(COVERAGE) report --show-missing
	$(COVERAGE) html
	@echo "📈 Coverage report generated in htmlcov/"

test-coverage-xml: ## Generate XML coverage report for CI
	@echo "📊 Generating XML coverage report..."
	$(COVERAGE) run --source='apps' -m pytest
	$(COVERAGE) xml
	@echo "📈 Coverage XML report generated"

coverage-report: ## Show coverage report
	@echo "📊 Coverage Report:"
	$(COVERAGE) report --show-missing

coverage-html: ## Generate HTML coverage report
	@echo "📈 Generating HTML coverage report..."
	$(COVERAGE) html
	@echo "📈 Coverage report available at htmlcov/index.html"

# =============================================================================
# PARALLEL EXECUTION
# =============================================================================

test-parallel: ## Run tests in parallel (faster)
	@echo "🚀 Running tests in parallel..."
	$(PYTEST) -n auto --tb=short

test-parallel-coverage: ## Run parallel tests with coverage
	@echo "🚀 Running parallel tests with coverage..."
	$(COVERAGE) run --source='apps' --parallel-mode -m pytest -n auto
	$(COVERAGE) combine
	$(COVERAGE) report --show-missing

# =============================================================================
# SPECIFIC APP TESTING
# =============================================================================

test-users: ## Test users app
	@echo "👤 Testing users app..."
	$(PYTEST) tests/unit/models/test_user_models.py tests/integration/api/test_auth_api.py -v

test-courses: ## Test courses app
	@echo "🎓 Testing courses app..."
	$(PYTEST) tests/unit/models/test_course_models.py tests/integration/api/test_course_api.py -v

test-practice: ## Test practice app
	@echo "🏃 Testing practice app..."
	$(PYTEST) apps/practice/tests.py -v

test-subscriptions: ## Test subscriptions app
	@echo "💳 Testing subscriptions app..."
	$(PYTEST) apps/subscriptions/ -v

# =============================================================================
# QUALITY ASSURANCE
# =============================================================================

test-quality: ## Run comprehensive quality tests
	@echo "🎯 Running comprehensive quality tests..."
	$(PYTEST) tests/ --tb=short --cov=apps --cov-report=html --cov-report=term-missing
	@echo "📊 Quality report completed"

test-ci: ## Run tests for CI environment
	@echo "🔄 Running CI tests..."
	$(COVERAGE) run --source='apps' -m pytest --tb=short --junit-xml=test-results.xml
	$(COVERAGE) xml
	@echo "📊 CI test results generated"

# =============================================================================
# DATABASE AND SETUP
# =============================================================================

test-setup: ## Set up test environment
	@echo "🛠️ Setting up test environment..."
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) manage.py migrate --settings=$(DJANGO_SETTINGS)
	@echo "✅ Test environment ready"

test-db-reset: ## Reset test database
	@echo "🔄 Resetting test database..."
	$(PYTHON) manage.py flush --noinput --settings=$(DJANGO_SETTINGS)
	$(PYTHON) manage.py migrate --settings=$(DJANGO_SETTINGS)
	@echo "✅ Test database reset"

# =============================================================================
# DEBUGGING AND DEVELOPMENT
# =============================================================================

test-debug: ## Run tests with debugging
	@echo "🐛 Running tests with debugging..."
	$(PYTEST) --tb=long --capture=no -v

test-failed: ## Re-run only failed tests
	@echo "🔄 Re-running failed tests..."
	$(PYTEST) --lf --tb=short

test-watch: ## Watch for file changes and run tests
	@echo "👀 Watching for changes..."
	find . -name "*.py" | entr -c make test-fast

# =============================================================================
# REPORTING AND ANALYSIS
# =============================================================================

test-report: ## Generate comprehensive test report
	@echo "📋 Generating test report..."
	$(PYTEST) --html=test-report.html --self-contained-html --tb=short
	@echo "📄 Test report generated: test-report.html"

test-metrics: ## Show test metrics
	@echo "📊 Test Metrics:"
	@echo "=================="
	@find tests/ -name "*.py" -not -name "__*" | wc -l | xargs echo "Test files:"
	@grep -r "def test_" tests/ | wc -l | xargs echo "Test functions:"
	@grep -r "@pytest.mark" tests/ | wc -l | xargs echo "Test markers:"

# =============================================================================
# CLEAN UP
# =============================================================================

clean-test: ## Clean test artifacts
	@echo "🧹 Cleaning test artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf test-report.html
	rm -rf test-results.xml
	rm -rf coverage.xml
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "✅ Test artifacts cleaned"

# =============================================================================
# EXAMPLES AND DOCUMENTATION
# =============================================================================

test-examples: ## Show testing examples
	@echo "📚 Testing Examples:"
	@echo "==================="
	@echo "make test                    # Run all tests"
	@echo "make test-unit               # Unit tests only"
	@echo "make test-coverage           # Tests with coverage"
	@echo "make test-fast               # Exclude slow tests"
	@echo "make test-parallel           # Parallel execution"
	@echo "make test-critical           # Critical tests only"
	@echo ""
	@echo "Pytest commands:"
	@echo "pytest tests/unit/models/test_user_models.py::TestUserModel::test_create_user"
	@echo "pytest -k 'test_login' -v"
	@echo "pytest -m 'not slow' --tb=short"

# =============================================================================
# INSTALLATION
# =============================================================================

install-test-deps: ## Install test dependencies
	@echo "📦 Installing test dependencies..."
	$(PYTHON) -m pip install pytest pytest-django factory-boy coverage
	$(PYTHON) -m pip install pytest-xdist pytest-mock responses freezegun
	$(PYTHON) -m pip install pytest-html pytest-cov
	@echo "✅ Test dependencies installed"

# =============================================================================
# CI/CD PIPELINE COMMANDS
# =============================================================================

test-cms: ## Executar apenas testes do CMS
	$(MANAGE) test apps.cms.tests --keepdb --parallel --verbosity=1

test-users: ## Executar apenas testes de usuários
	$(MANAGE) test apps.users.tests --keepdb --parallel --verbosity=1

test-subscriptions: ## Executar apenas testes de assinaturas
	$(MANAGE) test apps.subscriptions.tests --keepdb --parallel --verbosity=1

test-courses: ## Executar apenas testes básicos de courses
	$(MANAGE) test apps.courses.api.tests.test_student_practice_courses_basic --keepdb --parallel --verbosity=1

test-courses-all: ## Executar todos os testes de courses (pode demorar)
	$(MANAGE) test apps.courses.api.tests --keepdb --parallel --verbosity=1

test-practice: ## Executar apenas testes de practice
	$(MANAGE) test apps.practice.tests --keepdb --parallel --verbosity=1

test-critical: ## Executar testes críticos (CMS, Users, Subscriptions, Courses)
	@echo "🧪 Executando testes críticos..."
	$(MANAGE) test apps.cms.tests apps.users.tests apps.subscriptions.tests --keepdb --parallel --verbosity=1
	$(MANAGE) test apps.courses.api.tests.test_student_practice_courses_basic --keepdb --parallel --verbosity=1
	$(MANAGE) test apps.practice.tests --keepdb --parallel --verbosity=1

test-ci: ## Executar testes como no CI/CD
	@echo "🤖 Simulando ambiente CI/CD..."
	$(MANAGE) check --deploy
	$(MANAGE) migrate
	$(MANAGE) test apps.cms.tests apps.users.tests apps.subscriptions.tests --keepdb --parallel --verbosity=1
	$(MANAGE) test apps.courses.api.tests.test_student_practice_courses_basic --keepdb --parallel --verbosity=1
	$(MANAGE) test apps.practice.tests --keepdb --parallel --verbosity=1

docker-test: ## Executar testes no Docker
	@echo "🐳 Executando testes no Docker..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up --build --abort-on-container-exit

ci-simulate: ## Simular pipeline CI/CD localmente
	@echo "🤖 Simulando pipeline CI/CD..."
	$(MAKE) test-ci
	@echo "✅ Simulação do pipeline concluída!"

pre-deploy: ## Verificações antes do deploy
	@echo "🚀 Verificações pré-deploy..."
	$(MAKE) test-critical
	$(MANAGE) check --deploy
	@echo "✅ Pronto para deploy!"