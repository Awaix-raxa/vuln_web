# Software Specification Document (Implementation Addendum)

**Application:** Vulnerable Web Application — Security Lab
**Component:** App Foundation (authentication + dashboard)
**Version:** 1.0.0
**Last Updated:** 2026-09-20
**Status:** Implementation reference

---

## 1. Scope

This document captures **implementation-level behavior** required to reproduce the
application exactly as built. It is an addendum to `PRD.md` and `TDD.md` and does
**not** repeat what those documents already cover.

Intentionally omitted here (see PRD.md / TDD.md instead):

- Product goals, target audience, roadmap, success metrics.
- System architecture and layering.
- Technology stack and version pins.
- Descriptions of the 8 intentional vulnerabilities, their exploit vectors, and root-cause locations.
- Database schema definitions (DDL) and column semantics.
- The endpoint inventory (methods, paths, handler names, protection flags).

What this document **does** capture: runtime behavior, exact user flows, functional
requirements, the complete visual design system, form behavior, validation rules,
the session state model, data lifecycle, success/alternate/edge paths, business
rules, rebuild requirements, acceptance criteria, test cases, and known
documentation gaps. Where behavior and the referenced documents disagree, this
addendum records the discrepancy in Section 17 but describes the application **as it
actually behaves**.

---

## 2. Runtime Behavior

**RB-1 — Automatic database initialization on startup.** Schema creation runs during
application startup, before the server begins accepting requests. No manual migration
or seeding step is required.

**RB-2 — Missing DB file recreated automatically.** If the SQLite database file is
absent at startup, it is created and the schema is (re)initialized. Deleting the file
and restarting is the supported reset procedure; the application never depends on the
file pre-existing.

**RB-3 — Data preserved across restarts.** Because persistence is a file on disk,
user records survive process restarts. Startup initialization is non-destructive: it
creates the table only if it does not already exist and never drops or truncates
existing data.

**RB-4 — Static assets available after boot.** CSS and image assets are served from a
mounted static path and are reachable immediately once the server is up. They are not
gated by authentication.

**RB-5 — Templates loaded from disk at request time, no caching.** Each page request
reads its HTML template from the filesystem at the moment of the request. There is no
in-memory template cache and no precompilation step. A consequence is that edits to a
template file are visible on the next request without restarting the process.

**RB-6 — Dashboard content modified via runtime string substitution.** The dashboard
template contains a `{{username}}` placeholder. On each dashboard request the raw
template text is read and the placeholder is replaced with the current session's
username via plain string substitution before the response is returned. Substitution
happens per request against freshly read template text (see RB-5).

**RB-7 — Authentication state based solely on session presence.** A request is treated
as authenticated if and only if the session carries a user identity (`user_id`).
There is no token store, no server-side session revocation list, and no re-validation
against the database on protected requests — the presence of the session value is the
entire authentication decision.

---

## 3. User Flows

### 3.1 Registration
1. User navigates to the signup page; the signup template is served from disk.
2. User fills the form (username, email, password, confirm password).
3. **Client-side validation:** before submission, the page compares password and
   confirm-password. On mismatch it displays an inline error below the confirm field
   and blocks submission — no network request is sent, no page reload occurs.
4. On match, the form submits the registration data to the server.
5. Server creates the user record.
6. On success the server **redirects the user to the login page**. (Registration does
   not establish a session and does not land the user on the dashboard.)

### 3.2 Login
1. User navigates to the login page; the login template is served from disk.
2. User fills the form (username, password).
3. **Client-side fetch:** the page submits credentials via an asynchronous `fetch()`
   request rather than a native form post — the page does not navigate on submit.
4. The client **processes the response dynamically**:
   - On success it triggers a client-side redirect to the dashboard.
   - On failure it renders the returned error message inline in the error area
     without reloading the page.
5. On successful authentication the server establishes the session (user identity
   stored) prior to the success response.
6. The user arrives at the dashboard.

### 3.3 Dashboard
1. User requests the dashboard.
2. **Auth check:** server checks for a session user identity. If absent, the request
   is not served as the dashboard (see AP-03 / EC-04).
3. Server **loads the dashboard template from disk** (RB-5).
4. Server **injects the username** into the template via string substitution (RB-6).
5. Server responds with the composed HTML.

### 3.4 Logout
1. User initiates logout.
2. Server **clears the session** (all stored session values removed).
3. Server **redirects to the login page**.
4. After logout, protected resources are **inaccessible**: a subsequent dashboard
   request has no session identity and is not served as the dashboard.

---

## 4. Functional Requirements

**FR-01 — Session Management.** The application establishes a session on successful
login, carries it across requests via the session cookie, and destroys it on logout.
Session presence is the sole basis for authenticated access (RB-7).

**FR-02 — Dynamic User Context.** The dashboard reflects the currently logged-in
user by injecting the session username into the page at request time via runtime
substitution (RB-6). No user context is baked into the static template.

**FR-03 — Route Protection.** The dashboard route is protected: it is served only
when a session identity is present. All other primary routes (signup, login, logout,
search) are open.

**FR-04 — Error Handling.** Registration surfaces creation errors (e.g. duplicate
username) back to the user. Login returns a failure response that the client renders
inline. Client-side password mismatch is handled on the page before submission.

**FR-05 — Search Processing.** The search endpoint accepts a query parameter, matches
it against user records, and returns an HTML response listing matches. A query
parameter is required for the endpoint to operate.

**FR-06 — Persistence.** User records are stored durably on disk and survive restarts
(RB-3). The database file is auto-created when missing (RB-2).

---

## 5. Complete Visual Design Specification

This is the primary reference for reproducing the interface pixel-faithfully.

### 5.1 Global Design System

**Typography family (all text):**
`"Segoe UI", system-ui, -apple-system, sans-serif`

**Typography scale:**

| Role | Size | Weight |
|------|------|--------|
| Main titles | 2rem | 800 |
| Section titles | 1.4rem | 700 |
| Form titles | 1.7rem | 700 |
| Card titles | 0.95rem | 700 |
| Body text | 0.9rem | 400 |
| Labels | 0.82rem | 600 |
| Buttons | 1rem | 600 |

**Primary colors:**

| Token | Hex | Typical use |
|-------|-----|-------------|
| Indigo (deep) | `#1a237e` | Primary brand, headings, primary button bg |
| Indigo (mid) | `#3949ab` | Accents, focus border, gradient stop |
| Indigo (dark) | `#283593` | Gradient stop |
| Slate (near-black) | `#0f172a` | Deep contrast surfaces/text |
| Panel wash | `#eef1f8` | Dashboard body background |
| White | `#ffffff` | Cards, form panel, header |

**Text colors:**

| Hex | Use |
|-----|-----|
| `#1e293b` | Primary text |
| `#475569` | Secondary text |
| `#64748b` | Muted / subtitle text |
| `#c5cae9` | Light indigo (input borders, on-dark subtle text) |
| `#1a237e` | Emphasis / link text |

**Border radius:** inputs 8px · buttons 8px · cards 10–12px · status tags 6px.

**Shadows:**

| Element | Shadow |
|---------|--------|
| Header | `0 2px 10px rgba(26,35,126,0.08)` |
| Card hover | `0 4px 16px rgba(26,35,126,0.10)` |
| Input focus glow | `0 0 0 3px rgba(57,73,171,0.12)` |

### 5.2 Shared Header

- Fixed position; **70px** height.
- White background; bottom border; subtle header shadow (see table).
- App title on the **left**.
- Three organizational logos on the **right**, each **54×54px**.

### 5.3 Login Page

- **Two-column 50/50 split-screen** layout.
- **Left panel:** deep blue gradient `#0d1b5e → #1a237e → #283593`, containing:
  - a badge label,
  - a welcome heading,
  - a description paragraph,
  - a bullet list,
  - decorative **semi-transparent white circle** overlays (~7% opacity).
- **Right panel:** white background, containing a form constrained to **max 400px**:
  - title,
  - subtitle,
  - username field,
  - password field,
  - error message area,
  - **full-width login button** (`#1a237e` background, white text),
  - signup link.
- **Input styling:** background `#f8f9ff`, border `1.5px solid #c5cae9`; on focus the
  border becomes `#3949ab` with the blue focus glow.
- **Error messages:** light red background, red border, dark red text.

### 5.4 Signup Page

- **Identical structure to the login page** — same split-screen, same left-panel
  gradient, same decorative circles.
- **Form fields:** username, email, password, confirm password.
- **Password mismatch** displays red text below the confirm field **without a page
  reload** (client-side).

### 5.5 Dashboard

- **Body background:** `#eef1f8`.
- **Hero banner** beneath the shared header with gradient `#1a237e → #3949ab`:
  - **Left section:** title and subtitle.
  - **Right section:** logged-in username and a **semi-transparent white logout
    button**.
- **Content area:** max **1100px**, centered.
- **Mission card:** white, with a section title and a description.
- **"Vulnerabilities to Discover" section:** an uppercase, small, bold header.
- **Vulnerability grid:** two-column grid of **8 cards** (white, rounded, light
  border, hover shadow). Each card has a **colored pill tag** and a description.
  - **Tag colors:** SQLi = yellow · XSS = red · Session = purple · Brute = orange ·
    Crypto = green · Exposed = blue · CSRF = pink.
- **Process steps:** three step cards with `#1a237e` background, **circular numbered
  badges**, white text — **Find**, **Exploit**, **Mitigate**.

### 5.6 Responsive Behavior

- Desktop: auth pages render as the 50/50 split-screen.
- Mobile: auth panels **stack vertically**.
- Dashboard vulnerability cards collapse to a **single column**.
- Process steps become **vertical**.
- Header logos **shrink** at small widths.

---

## 6. Form Specifications

### 6.1 Registration Form
- **Inputs (4):** username, email, password, confirm password.
- **Client-side behavior:** password vs. confirm-password comparison runs before
  submit; on mismatch, submission is blocked and an inline error is shown (no reload,
  no request).
- On a valid match the form submits registration data to the server.

### 6.2 Login Form
- **Inputs (2):** username, password.
- **Submission:** via asynchronous `fetch()`.
- **Response handling:** success and failure are processed dynamically on the page —
  success redirects to the dashboard client-side; failure renders an inline error.
  The page does not reload on submit.

---

## 7. Validation Rules

**Registration**
- Username, email, and password are **required** (non-empty).
- Password must equal confirm-password (client-side) before submission.
- **Username uniqueness is enforced at the database level** (unique constraint), not
  by a pre-check in application code.

**Login**
- Username and password are **required** (non-empty).

**Search**
- The query parameter is **required** for the endpoint to process a search.

---

## 8. Session State Model

**Stored values:** `user_id`, `username`, `email`.

**Lifecycle:**
- **Creation:** the session is populated immediately after successful authentication.
- **Usage:** on each protected request the session is read to determine authentication
  (RB-7) and to supply the username for dashboard substitution (RB-6).
- **Destruction:** logout clears all session values; the session then carries no
  identity and protected routes are no longer served.

---

## 9. Data Lifecycle Rules

- **Create:** a user record is created on registration.
- **Update:** there is **no** user-modification workflow (no profile edit, no password
  change). Records are immutable after creation.
- **Delete:** there is **no** user-deletion workflow through the application.
- **Recover:** there is **no** password reset / account recovery workflow.

---

## 10. Success Paths

- **SP-01 — Registration:** valid, matching form data → user record created →
  redirect to login page.
- **SP-02 — Login:** valid credentials → session established → client redirect to
  dashboard.
- **SP-03 — Dashboard:** authenticated request → template loaded → username injected
  → HTML returned.
- **SP-04 — Logout:** logout initiated → session cleared → redirect to login →
  protected routes inaccessible.

---

## 11. Alternate Paths

- **AP-01 — Duplicate username:** registration with an existing username fails at the
  database uniqueness constraint; an error is surfaced to the user rather than a new
  record being created.
- **AP-02 — Invalid credentials:** login fails; the server returns a failure response
  and the client renders the error inline without reload; no session is established.
- **AP-03 — Unauthorized dashboard:** a dashboard request without a session identity
  is not served as the dashboard; the user is directed to authenticate.
- **AP-04 — Empty search:** a search request lacking the required query parameter does
  not perform a search.

---

## 12. Edge Cases

- **EC-01 — Existing username:** second registration with the same username is
  rejected by the unique constraint (see AP-01).
- **EC-02 — Empty registration data:** missing required registration fields do not
  produce a valid user; the required-field rule applies.
- **EC-03 — Empty login data:** missing required login fields cannot authenticate.
- **EC-04 — Missing session:** a protected request with no session identity is treated
  as unauthenticated (see AP-03).
- **EC-05 — Corrupted session:** a session that cannot yield a valid user identity is
  treated as unauthenticated — the same not-served outcome as a missing session.
- **EC-06 — Missing template:** if a page's template file is absent at request time,
  the page cannot be composed (templates are read from disk per request; there is no
  cached fallback copy).
- **EC-07 — Missing database file:** a missing DB file is recreated automatically at
  startup (RB-2); previously stored records are gone unless the file is restored.
- **EC-08 — Application restart:** restarting re-runs non-destructive initialization;
  existing data persists (RB-3) and templates/assets are available again after boot.

---

## 13. Business Rules

- **BR-01** — Authentication depends entirely on session presence; there is no
  secondary check.
- **BR-02** — Dashboard rendering requires runtime placeholder substitution; the
  static template alone is not a complete page.
- **BR-03** — User records are immutable after creation (no update/delete/recover
  workflows).
- **BR-04** — Login and registration use **different response formats**: login is a
  fetch/JSON-style response processed by client JS; registration completes with a
  server redirect.
- **BR-05** — Template edits are visible without a restart because templates are read
  from disk per request (RB-5).
- **BR-06** — The database unique constraint is the **primary uniqueness enforcement
  mechanism** for usernames (not an application-level pre-check).

---

## 14. Rebuild Requirements

A compatible implementation must reproduce all of the following:

1. Startup schema initialization that is non-destructive and idempotent (RB-1, RB-3).
2. Automatic creation of the database file when missing (RB-2).
3. Static assets served and reachable immediately after boot, unauthenticated (RB-4).
4. Per-request template reads from disk with no caching (RB-5), yielding
   edit-without-restart behavior.
5. Dashboard username injection via runtime string substitution of `{{username}}`
   (RB-6).
6. Authentication decided solely by session identity presence (RB-7).
7. Registration flow ending in a redirect to login, with client-side password-match
   validation blocking submission on mismatch.
8. Login flow submitted via async fetch with dynamic success/failure handling and no
   page reload.
9. Logout that clears the session and redirects to login, after which protected routes
   are inaccessible.
10. Session carrying `user_id`, `username`, `email` with the described lifecycle.
11. Search endpoint requiring a query parameter and returning an HTML list of matches.
12. The complete visual design system in Section 5 — typography scale, color tokens,
    radii, shadows, the fixed 70px header with three 54×54px logos, the 50/50
    split-screen auth pages with the specified gradient and ~7% circle overlays, and
    the dashboard hero + 8-card two-column grid with the specified tag colors and the
    three Find/Exploit/Mitigate process cards.
13. The responsive behavior in Section 5.6.
14. Username uniqueness enforced at the database level (BR-06).

---

## 15. Acceptance Criteria

- **AC-01 — Registration:** submitting valid, matching data creates a user and lands
  on the login page; mismatched passwords are blocked client-side with an inline
  error and no request.
- **AC-02 — Login:** valid credentials establish a session and redirect to the
  dashboard via client-side handling; invalid credentials show an inline error with no
  reload.
- **AC-03 — Dashboard:** an authenticated request renders the dashboard with the
  current username injected; the layout matches Section 5.5.
- **AC-04 — Logout:** logout clears the session, redirects to login, and makes the
  dashboard inaccessible on the next request.
- **AC-05 — Search:** a request with a query parameter returns an HTML list of
  matching users; a request without the parameter performs no search.
- **AC-06 — Persistence:** a user created before a restart can log in after the
  restart; deleting the DB file and restarting yields a fresh, empty, working
  database.

---

## 16. Test Cases

| ID | Scenario | Steps | Expected result |
|----|----------|-------|-----------------|
| TC-01 | Valid registration | Submit unique username, email, matching passwords | User created; redirect to login |
| TC-02 | Password mismatch | Enter differing password / confirm | Inline red error under confirm; no submit, no reload |
| TC-03 | Duplicate username | Register a username that already exists | Rejected by unique constraint; error surfaced; no new record |
| TC-04 | Missing registration fields | Submit with a required field empty | No valid user created |
| TC-05 | Valid login | Submit correct credentials | Session set; client redirect to dashboard |
| TC-06 | Invalid login | Submit wrong credentials | Inline error rendered; no reload; no session |
| TC-07 | Missing login fields | Submit with username or password empty | Authentication fails |
| TC-08 | Dashboard while authenticated | Visit dashboard after login | Dashboard renders with correct username |
| TC-09 | Dashboard while unauthenticated | Visit dashboard with no session | Not served as dashboard; directed to authenticate |
| TC-10 | Logout | Trigger logout | Session cleared; redirect to login |
| TC-11 | Post-logout protection | Visit dashboard after logout | Inaccessible (no session) |
| TC-12 | Search with query | Call search with a query parameter | HTML list of matching users returned |
| TC-13 | Search without query | Call search with no query parameter | No search performed |
| TC-14 | Persistence across restart | Create user, restart app, log in | Login succeeds; data intact |
| TC-15 | DB file recreation | Delete DB file, restart app | File recreated; app works with empty user set |

---

## 17. Documentation Gaps

Discrepancies between the referenced documents and implementation reality:

1. **Registration destination.** Flow-level behavior is that successful registration
   **redirects to login** (no session, no dashboard). Any reading of the requirements
   that implies auto-login after signup is not what the implementation does.

2. **Uniqueness enforcement point.** The documents describe unique usernames as a
   requirement but the implementation enforces this **only at the database
   constraint** — there is no application-level duplicate pre-check, so the behavior on
   collision is a constraint failure surfaced as an error, not a graceful pre-validation.

3. **Login vs. registration response formats.** The docs describe both as form
   submissions uniformly, but in practice login uses an **async fetch with a
   JSON-style response handled by client JS**, while registration completes with a
   **server-side redirect**. Rebuilds must not assume a single shared submission model.

4. **Template caching / responsiveness.** The docs mention static assets being
   "cached appropriately," but templates are **read from disk per request with no
   caching**, which is what enables edit-without-restart. The caching expectation in
   the non-functional requirements does not match the template-loading implementation.
