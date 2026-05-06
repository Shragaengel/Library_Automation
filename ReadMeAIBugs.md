# AI-Generated Code: Static Bug Analysis

> Static analysis of the buggy reference code provided in the exam.
> Each bug includes: location, description, impact, and fix.

---

## Bug #1: Missing `await` on async function call

**Location:** `reading_list_service.py` — `assert_reading_list_count()`

**Buggy code:**
```python
actual = reading_list.get_book_count()
```

**Problem:** `get_book_count()` is an `async` coroutine. Calling it without `await` returns a coroutine object instead of the actual integer count. The assertion then compares a coroutine object to an integer, which always fails or produces incorrect results.

**Impact:** The reading-list verification always fails or gives meaningless results.

**Fix:**
```python
actual = await reading_list.get_book_count()
```

---

## Bug #2: No type validation before `int()` conversion

**Location:** `search_service.py` — year parsing from search results

**Buggy code:**
```python
year = int(year_text.strip())
```

**Problem:** `year_text` is scraped from HTML and may contain non-numeric content (e.g. "Unknown", "c. 1954", "Dec 2001"). Calling `int()` on non-numeric text raises a `ValueError` that crashes the entire search loop.

**Impact:** A single book with a non-numeric year field aborts the entire search process — no results are returned.

**Fix:**
```python
year_text_clean = year_text.strip()
if not year_text_clean.isnumeric():
    continue  # skip entries without a valid numeric year
year = int(year_text_clean)
```

---

## Bug #3: Inner loop exceeds `limit` without breaking

**Location:** `search_service.py` — paginated result collection

**Buggy code:**
```python
while len(collected) < limit:
    results = await get_page_results(page_num)
    for item in results:
        collected.append(item)
    page_num += 1
```

**Problem:** The `while` condition only checks `len(collected) < limit` before processing a new page. Once inside the `for item in results` loop, there is no check — the entire page of results is appended. If `limit=5` and each page has 20 items, the first iteration collects 20 items (exceeding the limit by 15).

**Impact:** Returns more results than requested, causing unnecessary processing time and potentially overwhelming the reading-list service with too many books.

**Fix:**
```python
while len(collected) < limit:
    results = await get_page_results(page_num)
    for item in results:
        if len(collected) >= limit:
            break
        collected.append(item)
    page_num += 1
```

---

## Bug #4: Dead code — unreachable `return` after infinite loop

**Location:** `search_service.py` — paginated collection

**Buggy code:**
```python
while len(collected) < limit:
    # ... collection logic ...
    page_num += 1
return collected  # dead code if loop never terminates
```

**Problem:** If the search yields fewer results than `limit` and there are no more pages, the loop continues requesting empty pages indefinitely. There is no exit condition for "no more results available" — the code lacks a check like `if not results: break`.

**Impact:** Infinite loop when search results are fewer than the requested limit, hanging the automation forever.

**Fix:**
```python
while len(collected) < limit:
    results = await get_page_results(page_num)
    if not results:
        break  # no more pages available
    for item in results:
        if len(collected) >= limit:
            break
        collected.append(item)
    page_num += 1
```

---

## Bug #5: Login result not verified

**Location:** `reading_list_service.py` — `_ensure_logged_in()`

**Buggy code:**
```python
await login_page.login(username, password)
self._logged_in = True
```

**Problem:** The code sets `_logged_in = True` immediately after calling `login()` without verifying whether the login actually succeeded. If credentials are wrong or the site returns an error, the flag is still set to `True` and all subsequent operations fail silently with "not logged in" errors on the site.

**Impact:** The entire flow runs against unauthenticated pages, producing zero results with no clear error message.

**Fix:**
```python
await login_page.login(username, password)
assert await login_page.is_logged_in(), (
    "Login failed — credentials may be incorrect"
)
self._logged_in = True
```
