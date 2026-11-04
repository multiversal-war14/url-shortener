# Design Document – Production-Minded URL Shortener

## 1. System Overview

The application is a URL shortener built using Django. It allows users to create short URLs, redirect visitors to their original destinations, and view basic analytics such as total clicks and click history.

The application uses PostgreSQL for persistent storage and Redis for caching and rate limiting. Docker Compose manages the application and its supporting services. The application is deployed on a single AWS EC2 instance.

### Technology Stack

- **Backend:** Python, Django
- **Database:** PostgreSQL
- **Caching and rate limiting:** Redis
- **Application server:** Gunicorn
- **Containerization:** Docker and Docker Compose
- **Deployment:** AWS EC2

## 2. Short-Code Generation and Uniqueness

Each shortened URL receives a unique short code. Generated codes use uppercase letters, lowercase letters, and digits, providing a large number of possible combinations.

Custom aliases are also supported. However, aliases must be unique and cannot use reserved application paths.

The database enforces uniqueness through a unique constraint on the short-code field. This is important because checking whether a code exists before inserting it is not sufficient under concurrent requests: two requests could check at the same time and both find the code available.

The database constraint acts as the final authority and prevents duplicate codes from being stored.

If the application is scaled to multiple instances, each instance can generate codes independently because uniqueness is enforced centrally by the shared database. A collision can be handled by generating another code and retrying the insertion.

**Implemented:** Unique short codes, custom aliases, reserved-code validation, and database-level uniqueness.

**Possible improvement:** Use a carefully designed retry strategy for generated-code collisions and monitor collision frequency as the number of stored URLs grows.

## 3. Concurrent Requests and Database Consistency

The application must handle multiple users creating URLs and accessing existing shortened URLs at the same time.

For URL creation, database uniqueness constraints protect against duplicate short codes and competing custom aliases. When multiple requests attempt to create the same custom alias, only one can successfully claim it.

For redirects, click tracking must remain consistent when multiple visitors access the same short URL concurrently. Database-side atomic updates are preferable to reading a click count into application memory, incrementing it, and writing it back, because that approach can cause lost updates.

Click events provide additional information for analytics, while the total click count provides a convenient summary.

Concurrency was tested locally using Waitress with 32 threads and a temporary rate limit of 500 requests per minute.

The tests covered:

- 200 simultaneous requests creating different URLs.
- 200 simultaneous requests competing for the same custom alias.
- 200 simultaneous redirects to a shortened URL.

All 200 generated short codes were unique. Exactly one competing alias request succeeded, and the analytics endpoint reported 200 clicks after 200 successful redirects.

These results demonstrate successful handling in the tested local Waitress and SQLite environment. They do not prove identical performance under PostgreSQL or across multiple application instances.

**Implemented:** Database uniqueness protection and concurrent request testing.

**Further improvement:** Use database transactions and atomic counter updates wherever appropriate, and repeat the concurrency tests against the production PostgreSQL configuration.

## 4. Database Bottlenecks and Persistence

The database is responsible for storing shortened URLs, expiration information, click counts, and click-event records.

As traffic increases, database operations can become a bottleneck. Frequent redirects may generate many writes because click tracking updates analytics information. Large analytics queries can also become expensive as the number of click events grows.

Indexes on frequently queried fields, such as short codes and timestamps, help reduce lookup costs.

PostgreSQL is used in the deployed environment because it provides stronger support for concurrent application workloads than a simple local SQLite setup.

Persistent database storage is important because application containers may be rebuilt or restarted. Database data should therefore be stored in a persistent Docker volume rather than only inside a temporary application container.

**Implemented:** PostgreSQL deployment, database-backed URL persistence, and indexed short-code lookup.

**Possible improvements:**
- Add database connection pooling.
- Review slow queries and query plans.
- Introduce archival or retention policies for old click-event records.
- Consider read replicas if analytics queries become a significant workload.

## 5. Caching Strategy

Redis is used to reduce repeated work and improve response times.

Frequently accessed shortened URLs can be cached so that the application does not need to query the database for every redirect. Rate-limiting information is also maintained using Redis.

Caching improves performance for frequently accessed links, but cached information must remain consistent with the database.

When a URL expires or is modified, its cached entry must not continue serving an outdated destination. Cache entries should therefore have a suitable expiration time, and relevant entries should be invalidated when the underlying URL changes.

The application also has an expiration mechanism for shortened URLs, so expiry must be respected even when cached data is involved.

Cache failure should not cause permanent loss of URL data because PostgreSQL remains the persistent source of truth.

**Implemented:** Redis integration, redirect caching, configurable cache timeout, and Redis-based rate limiting.

**Design consideration:** Cache invalidation and expiry handling are essential to prevent stale redirects. PostgreSQL remains the authoritative data store.

## 6. Deployment Reliability and Security

The application is containerized using Docker and deployed on AWS EC2 using Docker Compose.

The deployment consists of three main services:

1. Django application served through Gunicorn.
2. PostgreSQL database.
3. Redis cache and rate-limiting service.

Environment variables are used for configuration, including Django settings, database credentials, Redis connection details, and application limits. Sensitive values are kept in a server-side `.env` file rather than committed to the Git repository.

The EC2 security group restricts SSH access to the permitted source IP and exposes the application through HTTP.

Database and Redis services are intended for internal Docker-network communication rather than direct public access.

Docker Compose makes it easier to rebuild and restart services. Persistent database volumes protect stored data across container restarts.

**Implemented:** Docker-based deployment, PostgreSQL and Redis services, environment-based configuration, and AWS EC2 hosting.

**Current limitation:** The deployed application is accessible over HTTP. HTTPS, TLS certificate management, and stronger production security configuration remain future improvements.

For greater reliability, the deployment could use automated backups, health monitoring, centralized logs, and a recovery procedure for database or instance failures.

## 7. Scaling Beyond a Single EC2 Instance

The current deployment uses one EC2 instance running the application, database, and Redis services through Docker Compose.

This is suitable for the current demonstration but introduces a single point of failure. If the EC2 instance becomes unavailable, the entire application becomes unavailable.

To support higher traffic, the architecture could be extended as follows:

- Run multiple Django/Gunicorn application instances.
- Place a load balancer in front of the application instances.
- Use a shared PostgreSQL database instead of separate databases per instance.
- Use a shared Redis service for caching and rate limiting.
- Move persistent database storage to a managed database service.
- Add monitoring, automated backups, and health checks.

All application instances must use the same database and shared cache infrastructure. Otherwise, different instances could maintain inconsistent URL data or rate-limit counters.

Database constraints remain essential because application-level checks alone cannot guarantee uniqueness across multiple instances.

**Current implementation:** Single EC2 instance with Docker Compose.

**Proposed future architecture:** Multiple stateless Django instances behind a load balancer, with shared PostgreSQL and Redis services.

## 8. Trade-offs and Conclusion

The project prioritizes correctness, simplicity, and reproducibility over premature infrastructure complexity.

PostgreSQL provides persistent relational storage, Redis reduces repeated database work, and Docker Compose makes the deployment easier to reproduce.

A single EC2 instance keeps the architecture straightforward, but it does not provide high availability or horizontal scaling. The local concurrency tests provide useful evidence of correct behavior under the tested conditions, but additional testing against the deployed PostgreSQL environment would be required before making production-scale performance claims.

The architecture can be extended with multiple application instances, managed database services, HTTPS, monitoring, and automated recovery as traffic and reliability requirements increase.