
import os
import sys
import time
import statistics

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.core.cache import cache
from django.test import Client, override_settings
from shortener.models import ShortURL

REQUESTS = 100


def benchmark(code, use_cache):
    client = Client()
    cache_key = f"shortener:redirect:{code}"
    times = []
    successes = 0

    cache.delete(cache_key)

    if use_cache:
        # Warm the cache. This request is not included in measurements.
        response = client.get(f"/{code}/", follow=False)

        if response.status_code != 302:
            print("Could not warm cache. HTTP status:", response.status_code)
            return None

    for _ in range(REQUESTS):
        if not use_cache:
            cache.delete(cache_key)

        start = time.perf_counter()
        response = client.get(f"/{code}/", follow=False)
        elapsed = time.perf_counter() - start

        times.append(elapsed * 1000)

        if response.status_code == 302:
            successes += 1

    return {
        "successes": successes,
        "average": statistics.mean(times),
        "median": statistics.median(times),
        "minimum": min(times),
        "maximum": max(times),
    }


if len(sys.argv) != 2:
    print("Usage: python benchmark_cache.py SHORT_CODE")
    sys.exit(1)

code = sys.argv[1]

if not ShortURL.objects.filter(short_code=code).exists():
    print("Short code does not exist.")
    sys.exit(1)

# Allow Django's test client hostname for this benchmark only.
with override_settings(ALLOWED_HOSTS=["*"]):

    print("\nBENCHMARK: WITHOUT REDIRECT CACHE")
    uncached = benchmark(code, False)

    print("\nBENCHMARK: WITH REDIRECT CACHE")
    cached = benchmark(code, True)

if uncached and cached:
    print("\n========== RESULTS ==========")

    print("\nWithout cache:")
    print("Successful redirects:", uncached["successes"])
    print("Average:", round(uncached["average"], 3), "ms")
    print("Median:", round(uncached["median"], 3), "ms")
    print("Minimum:", round(uncached["minimum"], 3), "ms")
    print("Maximum:", round(uncached["maximum"], 3), "ms")

    print("\nWith cache:")
    print("Successful redirects:", cached["successes"])
    print("Average:", round(cached["average"], 3), "ms")
    print("Median:", round(cached["median"], 3), "ms")
    print("Minimum:", round(cached["minimum"], 3), "ms")
    print("Maximum:", round(cached["maximum"], 3), "ms")

    improvement = (
        (uncached["average"] - cached["average"])
        / uncached["average"]
    ) * 100

    print("\nAverage response-time improvement:",
          round(improvement, 2), "%")

    print("\nNote: This measures Django application response time,")
    print("not real network latency.")
