
# Django URL Shortener

A Django-based URL shortening application that allows users to create short URLs, redirect visitors to their original destinations, and track link analytics.

The application includes custom aliases, URL expiry, click tracking, caching, rate limiting, destination validation, concurrent request handling, PostgreSQL, Redis, and Docker-based deployment.

**Live Application:** http://13.239.21.206

**GitHub Repository:** https://github.com/multiversal-war14/url-shortener

> Note: The current public deployment uses HTTP. HTTPS has not yet been configured.

## 1. Features

- Create short URLs from long URLs.
- Generate unique short codes automatically.
- Support custom aliases.
- Prevent duplicate short codes using database uniqueness constraints.
- Redirect users to original URLs.
- Track total clicks and individual click events.
- Display daily click statistics and referrer information.
- Set expiry times for short URLs.
- Validate destination URLs.
- Reject unsupported URL schemes and known internal destinations.
- Apply configurable rate limiting.
- Cache redirect lookups to improve response times.
- Invalidate cached entries when URLs are created or updated.
- Provide HTML pages for URL creation and analytics.
- Support SQLite for local development.
- Support PostgreSQL for deployment.
- Support Redis caching.
- Include Docker and Docker Compose configuration.
- Deploy using Gunicorn and WhiteNoise.

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Programming language |
| Django | Backend framework |
| SQLite | Local development database |
| PostgreSQL | Production database |
| Django Cache | Redirect caching |
| Redis | Shared cache backend |
| Waitress | Local concurrent request testing |
| Gunicorn | Production WSGI server |
| WhiteNoise | Static file serving |
| HTML and CSS | Frontend |
| Docker | Containerization |
| Docker Compose | Multi-container configuration |
| AWS EC2 | Cloud deployment |

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

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Configure the required environment variables before running the application.

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

Important environment variables include:

| Variable | Purpose |
|---|---|
| DJANGO_SECRET_KEY | Django secret key |
| DJANGO_DEBUG | Enables or disables debug mode |
| DJANGO_ALLOWED_HOSTS | Permitted hostnames |
| DJANGO_CSRF_TRUSTED_ORIGINS | Trusted CSRF origins |
| DJANGO_CSRF_COOKIE_SECURE | Controls secure CSRF cookies |
| DJANGO_SECURE_SSL_REDIRECT | Controls HTTPS redirection |
| DB_ENGINE | Database backend |
| POSTGRES_DB | PostgreSQL database name |
| POSTGRES_USER | PostgreSQL username |
| POSTGRES_PASSWORD | PostgreSQL password |
| POSTGRES_HOST | PostgreSQL hostname |
| POSTGRES_PORT | PostgreSQL port |
| REDIS_URL | Redis connection URL |
| SHORTENER_RATE_LIMIT | Maximum requests per rate-limit window |
| SHORTENER_RATE_WINDOW | Rate-limit window in seconds |
| SHORTENER_REDIRECT_CACHE_TIMEOUT | Redirect cache duration |
| SHORTENER_PUBLIC_BASE_URL | Public URL of the application |

The local development configuration uses SQLite. PostgreSQL and Redis are configured for deployment through environment variables.

**Security considerations:**

- Never commit `.env` or real credentials to GitHub.
- Keep Django secret keys and database passwords private.
- Use `.env.example` to document required variables without exposing actual secrets.
- Set `DEBUG=0` or its corresponding Django environment setting for deployment.
- Restrict SSH access to trusted IP addresses.

## 6. Application Usage

### Creating a Short URL

1. Open the homepage.
2. Enter the original destination URL.
3. Optionally provide a custom alias.
4. Optionally configure an expiry time in hours.
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

Analytics are available through:

```text
/<short_code>/analytics/
```

Example:

```text
http://13.239.21.206/mytest/analytics/
```

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

PostgreSQL is used for the cloud deployment.

## 8. Caching

Redirect lookups use Django's caching framework.

When a short URL is requested:

1. The application checks the cache.
2. If the entry exists, the cached URL is used.
3. Otherwise, the application retrieves the URL from the database.
4. The result is cached for subsequent requests.
5. Expiry is checked before redirecting.

Cache entries are invalidated when relevant URL records are created or changed.

Redis is configured as the shared cache backend in the Docker deployment.

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

Run Django's system checks:

```powershell
python manage.py check
```

The test suite has been run successfully during development.

## 12. Docker Configuration

The project includes:

- A Dockerfile for building the Django application image.
- A Docker Compose configuration for the web application, PostgreSQL, and Redis.
- Persistent PostgreSQL storage through a Docker volume.
- Environment-based application configuration.
- Gunicorn as the application server.
- WhiteNoise for static file serving.

### Build and Start Containers

Create and configure the `.env` file before starting the containers.

Build and start:

```bash
docker compose up -d --build
```

Check container status:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs web
```

Run migrations manually if needed:

```bash
docker compose exec web python manage.py migrate
```

Stop containers:

```bash
docker compose down
```

The PostgreSQL data volume is retained when containers are stopped and removed with `docker compose down`. Do not use `docker compose down -v` unless you intentionally want to delete the database volume.

## 13. AWS EC2 Deployment

The application has been deployed to an AWS EC2 instance using Docker Compose.

### Deployment Architecture

The deployment consists of three containers:

| Service | Technology | Purpose |
|---|---|---|
| Web | Django + Gunicorn | Application and HTTP requests |
| Database | PostgreSQL 17 | Persistent application data |
| Cache | Redis 7 | Shared caching |

### Deployment Steps

1. Launch an Amazon EC2 instance.
2. Configure SSH access through the EC2 security group.
3. Install Docker and Docker Compose.
4. Clone the GitHub repository.
5. Create and configure the production `.env` file.
6. Build and start the Docker containers.
7. Run database migrations.
8. Verify the web, PostgreSQL, and Redis services.
9. Access the application through the EC2 public IP.

Build and start the deployment:

```bash
docker compose up -d --build
```

Verify services:

```bash
docker compose ps
```

Check Django configuration:

```bash
docker compose exec web python manage.py check
```

### Live Deployment

**Public Application URL:**

http://13.239.21.206

The application has been accessed successfully through the public URL.

The following functionality has been manually verified on the deployed application:

- Homepage loads successfully.
- Short URL creation works.
- Generated short URLs redirect to their destinations.
- Custom aliases work.
- Expiry settings can be submitted.
- Analytics endpoint returns click information.
- PostgreSQL and Redis containers are running and healthy.

### Deployment Security

- Django debug mode is disabled.
- Environment variables are used for sensitive configuration.
- SSH access is restricted to the configured source IP.
- HTTP traffic is allowed through port 80.
- PostgreSQL and Redis are accessed through the Docker network rather than exposed publicly.

**Current limitation:** The public deployment uses HTTP rather than HTTPS. HTTPS, SSL certificate configuration, and production HSTS enforcement remain future improvements.

## 14. Known Limitations and Future Improvements

Potential improvements include:

- DNS resolution-based validation of destination IP addresses.
- HTTPS configuration with an SSL certificate.
- Production security hardening and HSTS configuration.
- Production monitoring and logging.
- More extensive automated integration and failure tests.
- Improved analytics filtering and visualization.
- Additional performance testing under production-like workloads.
- Verification of shared Redis caching across multiple application instances.
- Testing PostgreSQL behavior under larger concurrent workloads.

## 15. Design Documentation

Detailed explanations of the application's architecture, database design, concurrency handling, caching strategy, abuse protection, testing, and scalability considerations are available in:

```text
design_doc.md
```

## 16. Author

**Project:** Django URL Shortener

**Repository:** https://github.com/multiversal-war14/url-shortener

**Live Application:** http://13.239.21.206
