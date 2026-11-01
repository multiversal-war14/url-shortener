
# Django URL Shortener

A Django-based URL shortening service with custom aliases, expiration, click analytics, rate limiting, redirect caching, and destination URL validation.

## Features

- Generate unique short URLs for long URLs.
- Create custom aliases.
- Set optional link expiration (1–8760 hours).
- Redirect users to the original destination.
- Track total clicks and individual click events.
- View daily click statistics and referrer analytics.
- Rate-limit URL creation.
- Cache frequently accessed redirects.
- Reject localhost, private IP addresses, and common internal hostnames.
- Prevent redirects to the configured shortener hostname.
- Handle duplicate aliases using database uniqueness constraints.

## Technology Stack

- Python
- Django
- SQLite
- Django Cache Framework
- HTML and CSS

## Project Structure

```text
url-shortener/
├── config/
├── shortener/
│   ├── migrations/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   └── tests.py
├── templates/
│   └── shortener/
│       └── home.html
├── benchmark_cache.py
├── load_test.py
├── manage.py
├── requirements.txt
├── README.md
└── design_doc.md
```

## Installation

Clone the repository:

```bash
git clone https://github.com/multiversal-war14/url-shortener.git
cd url-shortener
```

Create and activate a virtual environment:

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply migrations:

```bash
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Configuration

The following settings can be configured in `config/settings.py`:

- `SHORTENER_RATE_LIMIT`: Maximum URL creations allowed during a rate-limit window.
- `SHORTENER_RATE_WINDOW`: Rate-limit window in seconds.
- `SHORTENER_REDIRECT_CACHE_TIMEOUT`: Default redirect cache duration in seconds.
- `SHORTENER_PUBLIC_BASE_URL`: Public base URL of the deployed shortener.

Do not commit secrets or production credentials.

## Usage

1. Open the homepage.
2. Enter the destination URL.
3. Optionally enter a custom alias.
4. Optionally select an expiration period.
5. Submit the form.
6. Use the generated short URL to redirect to the destination.

## Analytics

Each redirect records a click event.

The analytics endpoint is:

```text
/<short_code>/analytics/
```

It provides:

- Short code
- Total clicks
- Daily clicks
- Referrer statistics

## Running Tests

Run the application test suite:

```bash
python manage.py test shortener
```

The current test suite discovers 24 tests, which have passed locally.

## Cache Benchmark

Run:

```bash
python benchmark_cache.py YOUR_SHORT_CODE
```

Latest local benchmark:

| Measurement | Without cache | With cache |
|---|---:|---:|
| Average response | 4.763 ms | 1.876 ms |
| Median response | 3.718 ms | 1.646 ms |
| Maximum response | 78.133 ms | 3.711 ms |

Average response-time improvement: **60.61%**.

These measurements represent Django application response time using its test client, not real network latency.

## Load Testing

Run:

```bash
python load_test.py
```

The script tests:

- Concurrent creation of different URLs.
- Simultaneous requests for the same custom alias.
- Concurrent clicks and analytics tracking.

The local SQLite implementation has demonstrated successful duplicate-alias protection, but high-concurrency URL creation and click tracking still experience database lock failures. See `design_doc.md` for measured results and limitations.

## Deployment

The application has not yet been deployed to a public cloud environment. Production deployment requires a production-grade database, persistent storage, environment-based configuration, and appropriate hosting configuration.

## Repository

https://github.com/multiversal-war14/url-shortener
