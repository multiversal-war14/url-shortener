
# Design Document: Django URL Shortener

## 1. Overview

The application is a URL shortening service built using Django and SQLite. It allows users to convert long URLs into short, shareable links.

The system supports custom aliases, expiration, click tracking, analytics, rate limiting, destination validation, and redirect caching.

The main design goals are:

- Generate unique short codes.
- Prevent duplicate aliases.
- Track clicks reliably.
- Reduce redirect lookup latency.
- Validate destination URLs.
- Handle invalid requests without crashing.
- Keep the system extensible for future scaling.

## 2. System Architecture

The application follows Django's Model-View-Template architecture.

### Models

Two primary database models are used.

**ShortURL**

Stores:

- Original destination URL.
- Unique short code.
- Creation timestamp.
- Optional expiration timestamp.
- Total click count.

The `short_code` field has a database-level unique constraint. This ensures that two records cannot use the same short code, even if simultaneous requests attempt to create it.

**ClickEvent**

Stores:

- Related short URL.
- Click timestamp.
- Referrer information.

Every successful redirect creates a click event.

### Views

The application provides three main operations:

- Homepage: accepts URL creation requests.
- Redirect: looks up a short code and redirects to its destination.
- Analytics: returns click statistics and referrer information.

### Forms

The form validates:

- URL format.
- HTTP and HTTPS schemes.
- Custom alias format.
- Reserved aliases.
- Duplicate aliases.
- Expiration limits.
- Common internal and private destinations.

## 3. Unique Code Generation and Concurrent Writes

Random short codes are generated using Python's secure random token generation facilities.

The database enforces uniqueness through a unique constraint on `short_code`.

This is important because checking whether an alias exists before inserting it is not sufficient.

For example, two requests may simultaneously check whether an alias is available. Both may find that it is available.

The database constraint ensures that only one insertion succeeds.

The application catches duplicate-key errors and rejects the conflicting request.

### SQLite Concurrency Limitation

SQLite supports concurrent readers but serializes writes.

When many requests attempt to write simultaneously, some operations may encounter database lock errors.

The application uses:

- A 60-second SQLite database timeout.
- Write-ahead logging (WAL).
- Database operation retries for lock errors.
- Atomic transactions.
- Database uniqueness constraints.

These measures improve reliability but do not remove SQLite's single-writer limitation.

A production deployment with substantial write concurrency should use PostgreSQL or another database designed for concurrent workloads.

## 4. Click Tracking and Data Consistency

When a short URL is accessed, the application performs two operations:

1. Increments the URL's click counter.
2. Creates a corresponding ClickEvent record.

The click counter uses Django's database-side `F()` expression.

This avoids the unsafe pattern of reading a counter into Python, incrementing it, and writing the result back.

The operations are performed within a database transaction so that the counter update and event creation succeed or fail together.

However, SQLite can still experience lock contention under heavy concurrent writes.

## 5. Redirect Caching

Redirect lookups are cached using Django's cache framework.

The cache stores the destination URL, database record identifier, and expiration information.

When a short code is requested:

1. The application checks the cache.
2. If the entry exists, it retrieves the cached redirect information.
3. Otherwise, it looks up the record in the database.
4. The result is cached for subsequent requests.
5. Expired links are rejected.

Cache duration is configurable through `SHORTENER_REDIRECT_CACHE_TIMEOUT`.

The cache timeout is also limited by the link's remaining lifetime.

When a new link is created, its corresponding cache key is invalidated.

### Benchmark Results

The local benchmark used 100 requests in each measurement.

| Measurement | Without cache | With cache |
|---|---:|---:|
| Average | 4.763 ms | 1.876 ms |
| Median | 3.718 ms | 1.646 ms |
| Minimum | 1.713 ms | 1.405 ms |
| Maximum | 78.133 ms | 3.711 ms |

Average response-time improvement:

**60.61%**

The benchmark uses Django's test client. It measures application processing time rather than real network latency.

The cache reduces database lookup overhead, but click tracking still requires database writes.

### Cache Limitations

The current local-memory cache is suitable for development and a single application process.

It is not shared between multiple application instances.

For a multi-instance deployment, Redis or another shared cache should be used.

## 6. Rate Limiting

URL creation requests are rate-limited using Django's cache framework.

The rate limit and time window are configurable through:

- `SHORTENER_RATE_LIMIT`
- `SHORTENER_RATE_WINDOW`

Requests exceeding the configured limit are rejected.

The current local-memory implementation does not provide a distributed rate limit across multiple application instances.

A shared cache such as Redis would be required for distributed rate limiting.

## 7. Abuse Protection

The application validates destination URLs before saving them.

It rejects:

- Non-HTTP and non-HTTPS schemes.
- Localhost destinations.
- Common internal hostnames.
- Private IP addresses.
- Loopback IP addresses.
- Link-local IP addresses.
- Reserved IP addresses.
- URLs pointing to the configured shortener hostname.

The public base URL is configured through `SHORTENER_PUBLIC_BASE_URL`.

### Security Limitation

The current validation checks IP literals and common internal hostname patterns. It does not resolve DNS names to verify their resulting IP addresses.

Therefore, a hostname that appears public but resolves to a private address may bypass this validation.

A production implementation should include DNS resolution checks and protections against DNS rebinding, including validation at the appropriate point before accepting a destination.

## 8. Load Testing and Observations

The load-testing script uses concurrent workers to test three scenarios:

1. Creation of different short URLs.
2. Simultaneous creation requests using the same custom alias.
3. Concurrent clicks on an existing short URL.

### Observed Results

One recorded test run produced:

| Test | Requests | Successful | Failed |
|---|---:|---:|---:|
| Different URL creation | 200 | 70 | 130 |
| Same custom alias | 200 | 1 | 199 |
| Concurrent redirects | 200 | 85 | 115 |

For the custom alias test, exactly one request successfully created the alias. The remaining requests were rejected, demonstrating that the database uniqueness constraint prevents duplicate aliases.

The different-URL creation and concurrent redirect tests experienced failures caused by SQLite write contention.

These results demonstrate that the current SQLite configuration is not sufficient to satisfy the full 200-request concurrency requirement.

The failures have not been hidden or treated as successful requests.

### Future Improvement

For a production workload, PostgreSQL would be a better choice because it supports more effective concurrent write handling.

The load test should be repeated against the production database before claiming that the 200-request requirement has been satisfied.

## 9. Database Bottlenecks

The main bottleneck is concurrent database writing.

URL creation requires database inserts.

Redirect tracking requires a counter update and a click-event insert.

Caching reduces repeated URL lookup queries, but it cannot eliminate click-tracking writes.

Possible improvements include:

- Moving from SQLite to PostgreSQL.
- Using a shared Redis cache.
- Separating click-event collection from analytics aggregation.
- Adding suitable indexes.
- Monitoring database query performance.
- Using a connection pool where appropriate.

## 10. Reliability and Scaling

The current implementation is designed for local development and testing.

For production, the following improvements are recommended:

- PostgreSQL for persistent and concurrent database operations.
- Redis for shared caching and distributed rate limiting.
- Multiple Django application workers.
- A reverse proxy or load balancer.
- Centralized logging and monitoring.
- Environment-based secret management.
- Persistent database backups.
- Automated deployment and health checks.

If multiple application instances are used, they must share the same database and cache infrastructure.

Using separate SQLite databases or separate local-memory caches would result in inconsistent application state.

## 11. Conclusion

The application implements the core functionality of a URL shortener, including custom aliases, expiration, analytics, click tracking, rate limiting, destination validation, and redirect caching.

The automated test suite currently discovers and passes 24 tests.

The local caching benchmark demonstrates a 60.61% improvement in average application response time.

Concurrent alias creation is protected by a database uniqueness constraint. However, SQLite write contention remains a limitation under high concurrency.

A production deployment should use PostgreSQL and shared infrastructure before claiming full high-concurrency readiness.
