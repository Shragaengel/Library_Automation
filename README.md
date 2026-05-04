# OpenLibrary Automation Suite

End-to-end Playwright automation for [openlibrary.org](https://openlibrary.org).
Covers book search, reading list management, and performance measurement.

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
### Requirements

- Python 3.11+
- Chromium (auto-installed by Playwright)
- ~500 MB free disk for browser binaries
- Active internet connection for E2E tests
---

## Quick Start — Full Flow Example

```python
from runner.library_test_runner import LibraryTestRunner
from utils.config_loader import Config

# Single entry point — Facade pattern
runner = LibraryTestRunner(page=page, config=Config())
summary = await runner.run_full_flow(
    query="Dune", 
    max_year=1980, 
    limit=5,
)

print(summary)
# {
#   'urls_found': 5,
#   'urls_added': 5,
#   'verification_passed': True,
#   'performance_report_path': 'reports/performance_report.json'
# }
```

## Running Tests

```bash
# Fast feedback — unit tests only (~5 s, no browser)
pytest -m "not e2e" -v

# Full E2E suite with Allure report
pytest -m e2e -v

# Single test file
pytest tests/test_filters.py -v

# Generate and open Allure report
allure serve reports/allure-results
```

---

## Test Markers

| Marker | Meaning | Run command |
|---|---|---|
| *(none)* | All tests | `pytest` |
| `e2e` | Full browser tests — slow, need network | `pytest -m e2e` |
| `requires_auth` | Needs `.env` with credentials | `pytest -m requires_auth` |
| `not e2e` | Unit tests only — fast, no browser | `pytest -m "not e2e"` |
| `search` | Book search tests | `pytest -m search` |
| `reading_list` | Reading list tests | `pytest -m reading_list` |
| `performance` | Performance measurement tests | `pytest -m performance` |
| `smoke` | Quick sanity checks | `pytest -m smoke` |

---

## Architecture

```
openlibrary_automation/
├── pages/           # Page Object Model (POM) classes
│   ├── base_page.py              Template Method base
│   ├── home_page.py              Search form
│   ├── search_results_page.py    Result extraction + pagination
│   ├── book_detail_page.py       Reading-status dropdown
│   ├── login_page.py             Credentials form
│   ├── reading_list_page.py      Want-to-Read shelf
│   └── models.py                 Frozen dataclasses (BookSearchResult)
├── services/        # Orchestration layer
│   ├── search_service.py              Task 1 — search + filter
│   ├── reading_list_service.py        Task 2+3 — add books + verify count
│   └── performance_service.py         Task 4 — page-load measurement
├── strategies/      # Strategy pattern — reading-status actions
│   └── reading_strategy.py   WantToRead / AlreadyRead / Currently / Random
├── factories/       # Factory Method — page object creation by name
│   └── page_factory.py
├── decorators/      # Function decorators
│   └── measure_performance.py   @measure_performance(threshold_ms, page_name)
├── reporters/       # Report builders
│   ├── performance_collector.py          Singleton measurement accumulator
│   └── performance_report_builder.py     Builder -> performance_report.json
├── runner/          # Facade — single entry point for the full flow
│   └── library_test_runner.py   LibraryTestRunner.run_full_flow()
├── utils/           # Cross-cutting utilities
│   ├── config_loader.py    Config singleton (YAML + .env)
│   ├── exceptions.py       Custom exception hierarchy
│   ├── filters.py          Pure filter functions (no Playwright)
│   ├── logger.py           get_logger() factory
│   ├── models.py           Credentials dataclass
│   ├── page_metrics.py     Browser Performance API capture
│   └── smart_locator.py    Chain of Responsibility — 6 fallback strategies
├── tests/           # pytest test files
└── data/            # Parametrised test data (JSON)
```

---

## Design Patterns

| Pattern | Location | Purpose |
|---|---|---|
| Page Object Model | `pages/` | Encapsulate page interactions, keep tests clean |
| Template Method | `BasePage.navigate()` | Hook-based navigation lifecycle |
| Chain of Responsibility | `SmartLocator` | 6-strategy fallback locator resolution |
| Singleton | `Config`, `PerformanceCollector` | Single source of truth for config / metrics |
| Strategy | `strategies/reading_strategy.py` | Swap reading-status action without changing callers |
| Factory Method | `factories/page_factory.py` | Decouple test code from concrete page classes |
| Builder | `PerformanceReportBuilder` | Incremental JSON report construction |
| Facade | `LibraryTestRunner` | Single run_full_flow() hides all service complexity |
| Decorator | `@measure_performance` | Non-invasive timing of async functions |

---

## Exam Tasks

| Task | Function | Location |
|---|---|---|
| 1 | `search_books_by_title_under_year(query, max_year, limit)` | `services/search_service.py` |
| 2 | `add_books_to_reading_list(urls)` | `services/reading_list_service.py` |
| 3 | `assert_reading_list_count(expected_count)` | `services/reading_list_service.py` |
| 4 | `measure_page_performance(url, threshold_ms)` | `services/performance_service.py` |

---

## Limitations

- Reading-list count reflects the **total** Want-to-Read shelf, not just books
  added in the current run. Tests use `>=` comparisons for reliability.
- `load_time_ms` may be `0` when the browser serves a cached page.
- The `@measure_performance` decorator records to `PerformanceCollector`,
  which must be `reset()` between test runs to avoid cross-test accumulation.
