# Django URL Shortener

A Django-based URL shortening application that allows users to create short URLs, redirect visitors to their original destinations, and track link analytics.

The project includes custom aliases, URL expiry, click tracking, caching, rate limiting, destination validation, concurrent request handling, and Docker configuration.

## 1. Features

- Create short URLs from long URLs.
- Generate unique short codes automatically.
- Support custom aliases.
- Prevent duplicate short codes using database uniqueness constraints.
- Redirect users to original URLs.
- Track total clicks and individual click events.
- Display daily click statistics and referrer information.
- Set expiry dates for short URLs.
- Validate destination URLs.
- Reject unsupported URL schemes and known internal destinations.
- Apply configurable rate limiting.
- Cache redirect lookups to improve response times.
- Invalidate cached entries when URLs are created or updated.
- Provide HTML pages for URL creation and analytics.
- Support SQLite for local development and PostgreSQL configuration.
- Support Redis caching.
- Include Docker and Docker Compose configuration.

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Programming language |
| Django | Backend framework |
| SQLite | Local development database |
| PostgreSQL | Production database configuration |
| Django Cache | Redirect caching |
| Redis | Optional shared cache |
| Waitress | Local concurrent request testing |
| Gunicorn | Production WSGI server |
| WhiteNoise | Static file serving |
| HTML and CSS | Frontend |
| Docker | Containerization |
| Docker Compose | Multi-container configuration |

## 3. Project Structure

```text
url-shortener/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── shortener/
│   ├── migrations/
│   ├── templates/
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
│
├── templates/
├── static/
├── staticfiles/
│
├── benchmark_cache.py
├── load_test.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── .gitignore
├── manage.py
├── requirements.txt
├── README.md
└── design_doc.md
```

## 4. Local Installation and Setup

### Prerequisites

- Python 3.13 or later
- pip
- Git

Clone the repository:

```powershell
git clone https://github.com/multiversal-war14/url-shortener.git
```

Navigate into the project:

```powershell
cd url-shortener
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Apply database migrations:

```powershell
python manage.py migrate
```

Collect static files:

```powershell
python manage.py collectstatic --noinput
```

Start the development server:

```powershell
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## 5. Environment Configuration

The application supports environment-based configuration.

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Configure the environment variables before running the application.

Important settings include:

| Variable | Purpose |
|---|---|
| SECRET_KEY | Django secret key |
| DEBUG | Enables or disables debug mode |
| ALLOWED_HOSTS | Permitted hostnames |
| CSRF_TRUSTED_ORIGINS | Trusted CSRF origins |
| DB_ENGINE | Database backend |
| DB_NAME | Database name |
| DB_USER | Database username |
| DB_PASSWORD | Database password |
| DB_HOST | Database hostname |
| DB_PORT | Database port |
| REDIS_URL | Redis connection URL |
| SHORTENER_RATE_LIMIT | Maximum requests in a rate-limit window |
| SHORTENER_RATE_WINDOW | Rate-limit window in seconds |
| REDIRECT_CACHE_TIMEOUT | Redirect cache duration |
| PUBLIC_BASE_URL | Public URL of the deployed application |

Do not commit `.env` or real credentials to GitHub.

The local development configuration uses SQLite. PostgreSQL and Redis can be configured through environment variables.

## 6. Application Usage

### Creating a Short URL

1. Open the homepage.
2. Enter the original destination URL.
3. Optionally provide a custom alias.
4. Optionally configure an expiry date.
5. Submit the form.
6. The application generates a short URL.

### Redirecting

Opening a short URL redirects the visitor to the original destination.

The application checks whether the short URL exists and whether it has expired before redirecting.

### Analytics

The application tracks:

- Total clicks.
- Individual click events.
- Daily click counts.
- Referrer information.

Analytics are available through the application's URL statistics functionality.

## 7. Database and Concurrency Handling

The application uses database constraints and transaction-safe updates to handle concurrent requests.

### Unique Short Codes

The short code field has a database-level uniqueness constraint.

Automatically generated codes use secure random generation.

If multiple requests attempt to create the same custom alias, the database constraint prevents duplicate records.

### Concurrent Click Tracking

Click counts are updated using Django's `F()` expressions.

This allows the database to increment the click count without relying on a potentially outdated value read by the application.

Click events are recorded alongside the counter update using a database transaction.

### Database Considerations

SQLite is used for local development.

SQLite can experience write contention under heavy concurrent workloads. The application includes retry handling for certain SQLite lock errors.

PostgreSQL is configured as an alternative database backend for deployment. Multi-instance PostgreSQL behavior has not yet been verified through a production deployment.

## 8. Caching

Redirect lookups use Django's caching framework.

When a short URL is requested:

1. The application checks the cache.
2. If the entry exists, the cached URL is used.
3. Otherwise, the application retrieves the URL from the database.
4. The result is cached for subsequent requests.
5. Expiry is checked before redirecting.

Cache entries are invalidated when relevant URL records are created or changed.

Redis can be configured as a shared cache backend.

### Cache Benchmark

The following benchmark was measured locally using Django's test client, with 100 requests in each scenario.

| Measurement | Without cache | With cache |
|---|---:|---:|
| Successful redirects | 100 | 100 |
| Average response time | 4.763 ms | 1.876 ms |
| Median response time | 3.718 ms | 1.646 ms |
| Minimum response time | 1.713 ms | 1.405 ms |
| Maximum response time | 78.133 ms | 3.711 ms |

**Average response-time improvement: 60.61%.**

These are local test-client measurements, not real-world internet latency measurements.

Caching reduces repeated database lookup overhead. Click tracking still performs database writes for successful redirects.

Run the benchmark using:

```powershell
python benchmark_cache.py
```

## 9. Rate Limiting and URL Validation

The application includes configurable rate limiting to restrict excessive URL creation requests.

The rate limit and time window can be changed through environment variables.

Destination URL validation includes:

- HTTP and HTTPS scheme validation.
- Hostname validation.
- Malformed URL and port validation.
- Rejection of known internal hostnames.
- Rejection of private or non-public IP addresses when supplied directly.
- Rejection of the configured public shortener hostname.

**Known limitation:** The current validation does not perform DNS resolution to check whether an ordinary hostname resolves to a private IP address. DNS rebinding and DNS-based internal-address protection therefore require additional work before production use.

## 10. Concurrent Load Testing

The application was tested locally using Waitress with 32 threads, SQLite, and a temporary rate limit of 500 requests per minute.

### Test Results

| Scenario | Requests | Successful result | Time |
|---|---:|---:|---:|
| Creating different URLs concurrently | 200 | 200 created | 7.58 seconds |
| Competing for the same custom alias | 200 | Exactly 1 created | 7.05 seconds |
| Concurrent redirects | 200 | 200 HTTP 302 responses | 2.39 seconds |

### Observations

- All 200 URL creation requests succeeded.
- All 200 generated short codes were unique.
- When 200 requests competed for the same custom alias, exactly one succeeded and 199 were rejected by form validation.
- All 200 concurrent redirect requests returned HTTP 302.
- The analytics endpoint recorded exactly 200 clicks after those redirects.

These results demonstrate successful concurrent request handling in the tested local Waitress and SQLite environment. They do not establish production performance or multi-instance PostgreSQL behavior.

### Running the Load Test

Install Waitress if it is not already installed:

```powershell
pip install waitress
```

Start the application in one PowerShell terminal:

```powershell
$env:SHORTENER_RATE_LIMIT="500"
$env:SHORTENER_RATE_WINDOW="60"

waitress-serve --listen=127.0.0.1:8000 --threads=32 config.wsgi:application
```

Open another PowerShell terminal:

```powershell
cd C:\Users\HP\url-shortener

.\.venv\Scripts\Activate.ps1

python load_test.py
```

Keep the server running while the load test executes.

## 11. Automated Testing

The project includes automated tests covering URL shortening functionality and application behavior.

Run the test suite:

```powershell
python manage.py test shortener
```

Latest verified result:

```text
Found 8 test(s).

Ran 8 tests

OK
```

Run Django's system checks:

```powershell
python manage.py check
```

## 12. Docker Configuration

The project includes:

- A Dockerfile for building the Django application image.
- A Docker Compose configuration for the web application, PostgreSQL, and Redis.
- Persistent database and static-file volumes.
- Environment-based application configuration.
- Gunicorn as the application server.

Build and start the containers:

```powershell
docker compose up --build
```

Stop the containers:

```powershell
docker compose down
```

The Docker configuration has been prepared but has not been executed or verified in this development environment.

## 13. Deployment Status

The application includes configuration intended to support deployment using PostgreSQL, Redis, Gunicorn, WhiteNoise, and Docker.

However, a cloud deployment has not yet been completed or verified.

The following items remain to be verified:

- Successful Docker image build.
- Successful Docker Compose startup.
- PostgreSQL persistence and migrations.
- Redis shared caching.
- Production environment variables and secrets.
- Public deployment URL.
- Production security and HTTPS configuration.
- Load testing against the deployed application.

No public production URL is currently claimed.

## 14. Known Limitations and Future Improvements

Potential improvements include:

- DNS resolution-based validation of destination IP addresses.
- Production testing with PostgreSQL.
- Shared Redis cache verification across multiple application instances.
- Docker build and deployment verification.
- Cloud deployment and production monitoring.
- More extensive automated integration and failure tests.
- Improved analytics filtering and visualization.
- Additional performance testing under production-like workloads.

## 15. Design Documentation

Detailed explanations of the application's architecture, database design, concurrency handling, caching strategy, abuse protection, testing, and scalability considerations are available in:

```text
design_doc.md
```

## 16. Author

**Project:** Django URL Shortener
**Repository:** https://github.com/multiversal-war14/url-shortener
