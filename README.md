# OpenLibrary Automation Suite

End-to-end automation framework for [openlibrary.org](https://openlibrary.org),
built with **Playwright + Python** following clean-architecture principles.

---

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows (Git Bash / MSYS2)
# source venv/bin/activate     # macOS / Linux

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install chromium

# 4. Configure credentials
cp .env.example .env
# Edit .env and fill in OPENLIBRARY_USER and OPENLIBRARY_PASS
```

---

## Running Tests

```bash
# Run the full suite
pytest

# Run a specific marker
pytest -m search
pytest -m performance

# Generate and open Allure report
allure serve reports/allure-results
```

---

## Architecture Overview

> _To be completed during implementation._

```
openlibrary_automation/
├── pages/        # Page Object Model (POM) classes
├── services/     # Business-level orchestration (search, reading list)
├── strategies/   # Strategy pattern (e.g. add-to-list button variants)
├── factories/    # Factory pattern (page / browser creation)
├── decorators/   # Function decorators (performance measurement)
├── reporters/    # Report builders (HTML, JSON, Allure)
├── runner/       # Facade orchestrators (high-level test flows)
├── utils/        # Cross-cutting utilities (config, logging, locators)
├── tests/        # pytest test files + conftest
└── data/         # External test-data files (JSON / CSV / YAML)
```

---

## Design Patterns Used

> _To be completed during implementation._

- **Page Object Model (POM)** –
- **Strategy** –
- **Factory** –
- **Decorator** –
- **Facade** –

---

## Limitations

> _To be completed during implementation._
