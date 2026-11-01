### Verified load-test results

The concurrency tests were executed locally using Waitress with 32 threads and a temporary rate limit of 500 requests per minute.

| Scenario | Requests | Successful result | Time |
|---|---:|---:|---:|
| Different URL creation | 200 | 200 created | 7.58 seconds |
| Competing custom alias | 200 | Exactly 1 created | 7.05 seconds |
| Concurrent redirects | 200 | 200 HTTP 302 responses | 2.39 seconds |

All 200 generated short codes were unique.

For the competing alias test, exactly one request created the alias and the remaining 199 were rejected.

For concurrent redirects, the analytics endpoint reported exactly 200 clicks after 200 successful redirects.

These results demonstrate successful concurrent handling in this local Waitress and SQLite test environment. They do not establish production performance or multi-instance PostgreSQL behavior.