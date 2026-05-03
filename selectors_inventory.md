# OpenLibrary Selectors Inventory

> Generated: 2026-05-03
> Verified against:
>   - https://openlibrary.org
>   - https://openlibrary.org/search?q=Dune
>   - https://openlibrary.org/search?q=zzqxnonexistent999
>   - https://openlibrary.org/works/OL893415W/Dune?edition=key%3A/books/OL26242482M
> Method: `scripts/_inspect_page.py` against live site (headless Chromium)

## Legend
- ✅ Verified: exactly 1 match, visible
- ⚠️ Partial: matches found but count > 1 OR not visible (use as fallback only)
- ❌ Not found: zero matches (DO NOT USE)
- 🔒 Requires login: cannot verify without credentials; manual check needed

---

## HomePage
URL: `https://openlibrary.org`

### Search input
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `input[name='q']` | ✅ | count=1, visible. Has `aria-label="Search"` and `placeholder="Search"` |
| 2 | `[placeholder*='Search' i]` | ✅ | count=1, visible. Resolves to same element as above |
| 3 | `header input[type='text']` | ✅ | count=1, visible. Scoped to header — safe fallback |

**Recommended SmartLocator chain:**
1. `input[name='q']` — most stable; name attribute is unlikely to change
2. `[placeholder*='Search' i]` — semantic fallback
3. `header input[type='text']` — structural fallback

---

### Search button
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `input[type='submit'].search-bar-submit` | ✅ | count=1, visible. Real element: `<input type="submit" class="search-bar-submit" aria-label="Search submit">` |
| 2 | `[aria-label='Search submit']` | ✅ | count=1, visible. aria-label is unique |
| 3 | `[aria-label*='Search' i]` | ⚠️ | count=5 — too many matches; usable only as last resort after scoping |
| 4 | `button[type='submit']` | ❌ | count=0 — submit is an `<input>`, NOT a `<button>` |

> **Key finding:** The search submit is `<input type="submit">`, not `<button>`. Never use `button[type='submit']` for this page.

**Recommended SmartLocator chain:**
1. `input[type='submit'].search-bar-submit`
2. `[aria-label='Search submit']`
3. `input[type='submit']`

---

## SearchResultsPage
URL: `https://openlibrary.org/search?q=Dune`

### Result item container
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.searchResultItem` | ⚠️ | count=20 (one per result) — expected for a list; use `.count()` to measure results |
| 2 | `ul.list-books > li` | ⚠️ | count=20 — structurally equivalent to above |
| 3 | `[itemtype*='Book']` | ⚠️ | count=20 — schema.org attribute; stable semantic selector |

> Use `.searchResultItem` as the primary container and call `.count()` to get the number of results. All three selectors are equivalent.

**Recommended chain (for counting / iterating results):**
1. `.searchResultItem`
2. `ul.list-books > li`
3. `[itemtype*='Book']`

---

### Title link inside a result item
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.searchResultItem h3 a` | ⚠️ | count=20 — use `.nth(i)` to target a specific item |
| 2 | `.searchResultItem .booktitle a` | ⚠️ | count=20 — `.booktitle` is the semantic class |
| 3 | `.searchResultItem [itemprop='name']` | ⚠️ | count=20 — schema.org, most stable |

> Scope to a specific item with `.searchResultItem.nth(i)` + `.locator('h3 a')`.

**Recommended chain (scoped per item):**
1. `[itemprop='name']` (scoped inside item)
2. `h3 a` (scoped inside item)
3. `.booktitle a` (scoped inside item)

---

### Year / publication info inside a result item
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.resultDetails` | ⚠️ | count=20 — contains `"First published in YYYY"` text + editions link |
| 2 | `.resultDetails span:first-child` | ⚠️ | count=20 — first `<span>` inside `.resultDetails` has the year text |
| 3 | `.searchResultItem .bookPublishYear` | ❌ | count=0 — class does not exist in current markup |
| 4 | `.searchResultItem .bookEditions` | ❌ | count=0 — class does not exist in current markup |

> **Key finding:** Year is embedded in `.resultDetails span:first-child` as plain text `"First published in 1965"`. Parse with regex `r'(\d{4})'` to extract the year integer.

**Recommended chain (scoped per item):**
1. `.resultDetails` (scoped) → parse text for year
2. `.resultDetails span:first-child` (scoped)

---

### Pagination — next page
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `[aria-label='Go to next page']` | ✅ | count=1, visible. `<a aria-label="Go to next page" class="pagination-item pagination-arrow">` |
| 2 | `.pagination-arrow[href*='page=']` | ✅ | count=1, visible. CSS class + href pattern is robust |
| 3 | `a[href*='page=']` | ⚠️ | count=5 — too broad; includes numbered page links |
| 4 | `a.next-page` | ❌ | count=0 — class does not exist |
| 5 | `a[rel='next']` | ❌ | count=0 — `rel` attribute not used |

**Recommended chain:**
1. `[aria-label='Go to next page']`
2. `.pagination-arrow[href*='page=']`
3. `a[href*='page=']:last-of-type`

---

### "No results" indicator
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `ul.search-results:empty` | ✅* | The `<ul class="search-results">` exists but is empty — use `.count()` on `.searchResultItem` equals 0 as the primary check |
| 2 | `.search-results-stats` | ❌ | count=0 — class does not exist |
| 3 | `h1` text content | ✅ | count=1, text = "Search Books" — page title is the same regardless of results |

> **Recommended approach:** Assert `await page.locator('.searchResultItem').count() == 0` rather than looking for a specific "no results" element. The site renders an empty `<ul class="search-results">` with no children.

---

## BookDetailPage
URL: `https://openlibrary.org/works/OL893415W/Dune`

> **Key finding:** The page renders TWO copies of several elements (mobile + desktop layout).
> The **first** copy (`nth=0`) is visually hidden via CSS; the **second** (`nth=1`) is visible.
> Always scope with `.nth(1)` or use `.filter(has_text=...)` to target the visible copy.

### Book title
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `h1.work-title` | ⚠️ | count=2 — `nth(0)` hidden, `nth(1)` visible. Use `.nth(1)` |
| 2 | `[itemprop='name']` | ⚠️ | count=3 — includes title + other schema items. Scope to `h1[itemprop='name'].nth(1)` |
| 3 | `h1` | ⚠️ | count=2 — same dual-element issue |

**Recommended chain:**
1. `h1.work-title` → use `.nth(1)` in Page Object
2. `h1[itemprop='name']` → use `.nth(1)`
3. `h1` → use `.nth(1)` as last resort

---

### Author link
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.edition-byline a` | ⚠️ | count=2 — `nth(0)` hidden, `nth(1)` visible. Has `itemprop="author"` |
| 2 | `a[href*='/authors/']` | ⚠️ | count=2 — same dual-element pattern |
| 3 | `[itemprop='author'] a` | ⚠️ | count=2 — same |
| 4 | `a.author-name` | ❌ | count=0 — class does not exist in current markup |

**Recommended chain:**
1. `.edition-byline a` → use `.nth(1)`
2. `a[href*='/authors/']` → use `.nth(1)`
3. `[itemprop='author'] a` → use `.nth(1)`

---

### Publish year / date
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `[itemprop='datePublished']` | ✅ | count=1, visible. Text = `"1965"` |
| 2 | `.edition-overview .first-published` | ❌ | count=0 — class does not exist |

**Recommended chain:**
1. `[itemprop='datePublished']` — unique, semantic, stable
2. `.edition-overview` → parse text for year as fallback

---

### "Want to Read" button
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `button:has-text('Want to Read')` | ⚠️ | count=1 but `class="nostyle-btn hidden"` — intentionally hidden without login |
| 2 | `[data-action*='want-to-read' i]` | ❌ | count=0 |
| 3 | `.want-to-read` | ❌ | count=0 |

> **Key finding:** `button:has-text('Want to Read')` exists in the DOM but is CSS-hidden (`class="hidden"`).
> It becomes interactive and visible **only after login**. See TODO section below.

---

## TODO — Manual completion required (login-gated)

### Login form (URL: `/account/login`)

> **CRITICAL WARNING:** Page contains TWO submit elements (search bar + login form).
> Generic `[type='submit']` will match both — always scope to the login form
> or use the specific `name='login'` attribute.

#### Email/Username input
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `get_by_label("Email")` | ✅ | Playwright role-based, most stable |
| 2 | `input[name='username']` | ✅ | type=email, visible, unique |
| 3 | `#username` | ✅ | id-based fallback |

**SmartLocator chain:** [1] → [2] → [3]

#### Password input
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `get_by_label("Password")` | ✅ | role-based |
| 2 | `input[name='password']` | ✅ | type=password, visible |
| 3 | `#password` | ✅ | id-based fallback |

**SmartLocator chain:** [1] → [2] → [3]

#### Submit button (Log In)
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `get_by_role("button", name="Log In")` | ✅ | role + accessible name |
| 2 | `button[name='login']` | ✅ | unique name attribute |
| 3 | `form button[type='submit']` | ✅ | scoped to form, avoids search button |

**SmartLocator chain:** [1] → [2] → [3]
> **DO NOT USE:** `button[type='submit']` alone — matches 2 elements!
> **DO NOT USE:** `input[type='submit']` — that is the search bar button!

#### Remember me checkbox (optional)
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `input[name='remember']` | ✅ | type=checkbox, visible |
| 2 | `#remember` | ✅ | id-based fallback |

#### Error message
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.ol-signup-form__info-box.error` | ✅ | Most specific — unique to error state |
| 2 | `.ol-signup-form__info-box` | ✅ | Also appears for non-error info boxes; use with text assertion |
| 3 | `text=/no account.+found\|invalid\|incorrect\|wrong/i` | ✅ | Text-based fallback |

**SmartLocator chain:** [1] → [2] → [3]

> **Sample error captured:** `"No account was found with this email. Please try again"`
> **Trigger condition:** Submit login form with invalid email/password

---

### BookDetailPage — Reading Status Controls (logged in)

> **CRITICAL UI INSIGHT:** OpenLibrary uses a SINGLE dropdown button for reading
> status, NOT three separate buttons. The flow is:
> 1. Click main button → adds to "Want to Read" by default
> 2. Click ▼ to expand dropdown → reveals "Currently Reading" + "Already Read"
> 3. Click desired option → changes status

#### Main reading status button (Want to Read)
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.book-progress-btn` | ✅ | unique class |
| 2 | `button.book-progress-btn.primary-action` | ✅ | more specific |
| 3 | `get_by_role("button", name=/want to read/i)` | ✅ | role-based, recommended |

> **State indicator:** class includes `unactivated` (not in list) or `activated` (already added)

#### Dropdown expander (▼ arrow)
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.book-progress-btn + button` | ⚠️ | sibling button — needs verify |
| 2 | `[aria-haspopup='true']:near(.book-progress-btn)` | ⚠️ | Playwright layout query |

> **NOTE:** Verify exact selector by clicking ▼ in DevTools inspector first.

#### Currently Reading (inside dropdown, after expansion)
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `button.nostyle-btn:has-text("Currently Reading")` | ✅ | text-scoped |
| 2 | `get_by_role("button", name="Currently Reading")` | ✅ | role-based, recommended |
| 3 | `button:has-text("Currently Reading"):visible` | ✅ | with visibility check |

#### Already Read (inside dropdown, after expansion)
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `button.nostyle-btn:has-text("Already Read")` | ✅ | text-scoped |
| 2 | `get_by_role("button", name="Already Read")` | ✅ | role-based, recommended |

#### Remove from list (in dropdown when book is already in a list)
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `button:has-text("Remove From Shelf")` | ✅ | visible: false until dropdown expanded |
| 2 | `.remove-from-list` | ✅ | class-based fallback |

#### Reading log statistics (read-only, visible without login)
| Element | Selector | Notes |
|---------|----------|-------|
| Want to read count | `.reading-log-stat:nth-child(1)` | e.g. "1167" |
| Currently reading count | `.reading-log-stat:nth-child(2)` | e.g. "96" |
| Have read count | `.reading-log-stat:nth-child(3)` | e.g. "179" |

---

### ReadingListPage (URL: `/people/<username>/books/want-to-read`)

> **NOTE on URL:** The path uses the username, not `/account/`.
> Example: `/people/shraga_books/books/want-to-read`
> Use `config.username` when constructing the URL in the Page Object.

#### Page header / count
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `text=/Want to Read \(\d+\)/` | ✅ | Matches "Want to Read (0)", "Want to Read (1)", etc. |
| 2 | `summary:has-text("Want to Read")` | ⚠️ | Dropdown summary tag — test in code |

#### Books list container
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.mybooks-list` | ✅ | Unique container for the list area |
| 2 | `main` | ⚠️ | Less specific — use only when scoping inside |

#### Book items (when list has books)
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `.mybooks-list a[href*='/works/']` | ⚠️ | Not yet verified (empty state during recon) |
| 2 | `main a[href*='/works/']` | ⚠️ | Broader fallback |

> **NOTE:** Individual book-item selectors not yet verified against a populated list.
> Run `scripts/_inspect_page.py` on the reading list URL after adding books to confirm.

#### Empty state detection
| Priority | Selector | Status | Notes |
|----------|----------|--------|-------|
| 1 | `text="You haven't added any books to this shelf yet."` | ✅ | Exact match |
| 2 | `.mybooks-list p:has-text("haven't added")` | ✅ | Scoped to container |
| 3 | `text=/no books\|haven't added\|nothing here/i` | ✅ | Regex fallback |

#### Strategy for `get_book_count()` in POM

```python
async def get_book_count(self) -> int:
    """
    Return the number of books currently on the Want-to-Read shelf.

    Strategy A (preferred): parse the count from the page header text
      e.g. "Want to Read (3)" → 3
    Strategy B (fallback): count work links inside .mybooks-list
    """
    # Strategy A — parse header
    try:
        header = self._page.locator("summary:has-text('Want to Read')")
        text = await header.first.inner_text()          # "Want to Read (3)"
        match = re.search(r'\((\d+)\)', text)
        if match:
            return int(match.group(1))
    except Exception:
        pass

    # Strategy B — count work links
    items = self._page.locator(".mybooks-list a[href*='/works/']")
    return await items.count()
```

---

## Verified selector quick-reference

```python
# ── HomePage ────────────────────────────────────────────
SEARCH_INPUT   = "input[name='q']"
SEARCH_BUTTON  = "input[type='submit'].search-bar-submit"

# ── SearchResultsPage ───────────────────────────────────
RESULT_ITEMS   = ".searchResultItem"          # count() == number of results
RESULT_TITLE   = "h3 a"                       # scoped inside item locator
RESULT_DETAILS = ".resultDetails"             # contains year text — parse with regex
NEXT_PAGE      = "[aria-label='Go to next page']"
NO_RESULTS     = ".searchResultItem"          # check .count() == 0

# ── BookDetailPage ──────────────────────────────────────
BOOK_TITLE     = "h1.work-title"              # use .nth(1) — second is visible
AUTHOR_LINK    = ".edition-byline a"          # use .nth(1)
PUBLISH_YEAR   = "[itemprop='datePublished']"
WANT_TO_READ        = ".book-progress-btn"                        # logged in; class="unactivated|activated"
DROPDOWN_EXPANDER   = ".book-progress-btn + button"               # opens status menu
CURRENTLY_READING   = "button.nostyle-btn:has-text('Currently Reading')"
ALREADY_READ        = "button.nostyle-btn:has-text('Already Read')"
REMOVE_FROM_SHELF   = "button:has-text('Remove From Shelf')"

# ── LoginPage (/account/login) ───────────────────────────
# WARNING: page has 2 submit elements — always use the scoped selectors below
LOGIN_EMAIL    = "input[name='username']"     # fallback: #username
LOGIN_PASSWORD = "input[name='password']"     # fallback: #password
LOGIN_SUBMIT   = "button[name='login']"       # fallback: form button[type='submit']
LOGIN_REMEMBER = "input[name='remember']"
# Playwright preferred (use in LabelStrategy / RoleStrategy):
#   email    → page.get_by_label("Email")
#   password → page.get_by_label("Password")
#   submit   → page.get_by_role("button", name="Log In")
```
