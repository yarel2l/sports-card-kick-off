# Sports Card Kick-Off

A comprehensive sports card marketplace aggregator and intelligence platform powered by AI. This platform aggregates data from multiple sports card marketplaces, provides intelligent search capabilities using natural language processing, and delivers real-time pricing and population data to collectors and investors.

[![Tests](https://github.com/yarel2l/sports-card-kick-off/actions/workflows/tests.yml/badge.svg)](https://github.com/yarel2l/sports-card-kick-off/actions/workflows/tests.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Features

- **🔍 Intelligent Search**: Natural language processing for card queries
- **🤖 AI-Powered Scraping**: LangChain/LangGraph orchestrated web scraping
- **📊 Multi-Source Aggregation**: Data from eBay, PSA, 130Point, COMC, Goldin, and more
- **🔐 Secure Authentication**: JWT-based OAuth2 authentication
- **📈 Real-Time Data**: Live pricing, population reports, and market trends
- **📱 RESTful API**: Comprehensive API with OpenAPI/Swagger documentation
- **⚡ Async Processing**: Celery-based background task processing
- **🎯 User History**: Track search history and favorite cards

## 🏗️ Architecture

### Backend Stack
- **Framework**: Django 5.2+ with Django REST Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **Cache**: Redis
- **Task Queue**: Celery + Redis
- **WebSockets**: Django Channels
- **AI/ML**: LangChain, LangGraph, OpenAI, Anthropic, Google GenAI
- **Web Scraping**: Playwright, BeautifulSoup4
- **API Documentation**: drf-spectacular (OpenAPI 3.0)

### Project Structure
```
sports-card-kick-off/
├── apps/
│   ├── accounts/          # User authentication and management
│   ├── core/              # System configuration and utilities
│   ├── scraping/          # AI agents, orchestrators, and fetchers
│   └── search/            # Search API and history
├── config/
│   ├── settings/          # Django settings (base, local, production)
│   ├── channels/          # WebSocket configuration
│   └── integrations/      # AWS and external service integrations
├── internal_docs/         # Project documentation (not in repo)
└── logs/                  # Application logs (not in repo)
```

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 14+ (for production)
- Redis 6+ (for caching and Celery)
- Node.js 18+ (for Playwright browser automation)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yarel2l/sports-card-kick-off.git
   cd sports-card-kick-off
   ```

2. **Create and activate virtual environment**
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

5. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # Django Settings
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   DJANGO_SETTINGS_MODULE=config.settings.local
   
   # Database (SQLite for local development)
   DATABASE_URL=sqlite:///db.sqlite3
   
   # Redis
   REDIS_URL=redis://localhost:6379/0
   
   # Celery
   CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   
   # AI API Keys (optional for development)
   OPENAI_API_KEY=your-openai-key
   ANTHROPIC_API_KEY=your-anthropic-key
   GOOGLE_API_KEY=your-google-key
   HUGGINGFACE_API_KEY=your-huggingface-key
   
   # Email (optional)
   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
   ```

6. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Load initial data (optional)**
   ```bash
   python manage.py loaddata initial_sites
   ```

### Running the Application

#### Development Server

1. **Start Redis** (in a separate terminal)
   ```bash
   redis-server
   ```

2. **Start Celery worker** (in a separate terminal)
   ```bash
   celery -A config worker -l info
   ```

3. **Start Celery beat** (optional, for scheduled tasks)
   ```bash
   celery -A config beat -l info
   ```

4. **Start Django development server**
   ```bash
   python manage.py runserver
   ```

5. **Access the application**
   - API: http://localhost:8000/api/v1/
   - Admin Panel: http://localhost:8000/admin/
   - API Documentation: http://localhost:8000/api/schema/swagger-ui/
   - ReDoc: http://localhost:8000/api/schema/redoc/

### Running Tests

Run all tests:
```bash
python manage.py test
```

Run tests with coverage:
```bash
coverage run --source='apps' manage.py test
coverage report
coverage html  # Generate HTML report
```

Run specific app tests:
```bash
python manage.py test apps.accounts
python manage.py test apps.search
python manage.py test apps.scraping
```

Run with verbosity:
```bash
python manage.py test --verbosity=2
```

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/v1/auth/register/` - Register new user
- `POST /api/v1/auth/login/` - Login and get JWT tokens
- `POST /api/v1/auth/logout/` - Logout (blacklist refresh token)
- `POST /api/v1/auth/token/refresh/` - Refresh access token
- `GET /api/v1/auth/me/` - Get current user profile
- `PATCH /api/v1/auth/me/` - Update user profile

### Search Endpoints
- `POST /api/v1/search/` - Create new search
- `GET /api/v1/search/history/` - Get user search history
- `GET /api/v1/search/stats/` - Get user statistics
- `GET /api/v1/search/sites/` - Get available target sites
- `GET /api/v1/search/{id}/` - Get search details
- `GET /api/v1/search/{id}/results/` - Get search results
- `POST /api/v1/search/{id}/cancel/` - Cancel pending search

### System Configuration (Admin only)
- `GET /api/v1/system-config/` - Get system configuration
- `PATCH /api/v1/system-config/` - Update system configuration

Full API documentation is available at `/api/schema/swagger-ui/` when running the server.

## 🧪 Testing

The project includes comprehensive test coverage:

- **185 total tests** across all apps
- **Accounts**: 33 tests (authentication, user management)
- **Core**: 39 tests (system configuration)
- **Scraping**: 86 tests (agents, fetchers, schemas)
- **Search**: 27 tests (API endpoints, integration flows)

Test structure:
```
apps/
├── accounts/tests/
│   ├── test_auth_api.py
│   ├── test_models.py
│   └── test_password_api.py
├── core/tests/
│   ├── test_models.py
│   └── test_system_config_api.py
├── scraping/tests/
│   ├── test_agents.py
│   ├── test_fetchers.py
│   └── test_schemas.py
└── search/tests/
    ├── test_search_api.py
    └── test_search_integration.py
```

## 🔄 CI/CD

The project uses GitHub Actions for continuous integration. Tests are automatically run on every push to the `develop` branch.

See `.github/workflows/tests.yml` for configuration details.

## 🗄️ Database Schema

### Core Models

**User** (extends Django AbstractUser)
- Custom user model with UUID-based account_id
- Email-based authentication
- Profile fields (first_name, last_name, avatar)

**Search**
- User's search queries
- Status tracking (PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED, PARTIAL)
- Metrics (total_sites, successful_sites, failed_sites, total_items_found)
- Execution time tracking

**ScrapeResult**
- Individual card listings from target sites
- Price information, condition, grade
- Seller information
- Source URL and metadata

**TargetSite**
- Configuration for each marketplace
- Site-specific scraping parameters
- Active/inactive status

**SearchHistory**
- Historical record of completed searches
- Associated results and metadata
- Used for user statistics and trends

## 🛠️ Development

### Code Style

This project follows PEP 8 guidelines. Use tools like `black` and `flake8` for code formatting:

```bash
pip install black flake8
black .
flake8 apps/
```

### Live Scraping Validation

Unit tests parse fixture HTML so they are fast and deterministic. To validate an
agent against the **real** site (selectors drift over time), use the live
harness — it requires network access and a Playwright browser, so it is kept out
of the default test suite.

```bash
# One-time: install the browser
playwright install chromium

# Run an agent live and print parsed items
python manage.py scrape_live ebay "2018 Prizm Luka Doncic PSA 10"

# Save the raw search HTML to tune selectors offline
python manage.py scrape_live 130point "Mike Trout rookie" --dump-html /tmp/130.html

# Opt-in live integration tests (skipped by default)
RUN_LIVE_SCRAPE_TESTS=1 python manage.py test apps.scraping.tests.test_live_scraping
```

Available sources: `ebay`, `130point`, `comc`, `goldin`.

### Adding a New Target Site

1. Create a new agent in `apps/scraping/agents/`
2. Define the site schema in `apps/scraping/schemas/`
3. Update the orchestrator in `apps/scraping/orchestrators/`
4. Add site configuration in Django admin
5. Write tests in `apps/scraping/tests/`

### Environment-Specific Settings

- **Local Development**: `config/settings/local.py`
- **Production**: `config/settings/production.py`
- **Base Settings**: `config/settings/base.py`

Set the environment using `DJANGO_SETTINGS_MODULE` in your `.env` file.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Contact

Project Link: [https://github.com/yarel2l/sports-card-kick-off](https://github.com/yarel2l/sports-card-kick-off)

---

**Note**: This is an active development project. Features and documentation are continuously evolving.
