import json
import re
import secrets
import time
import html
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

BASE_URL = "http://127.0.0.1:8000"
CONCURRENT_REQUESTS = 200
TIMEOUT = 90


def make_opener():
    cookies = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookies)
    )


def get_csrf(opener):
    request = urllib.request.Request(BASE_URL + "/")

    with opener.open(request, timeout=TIMEOUT) as response:
        page = response.read().decode("utf-8", errors="replace")

    match = re.search(
        r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
        page
    )

    if not match:
        raise RuntimeError("Could not find CSRF token on homepage.")

    return match.group(1)


def clean_message(body):
    message = re.sub(r"<[^>]+>", " ", body)
    message = html.unescape(message)
    message = re.sub(r"\s+", " ", message)
    return message.strip()[:250]


def submit_link(original_url, alias=None, barrier=None):
    opener = make_opener()

    try:
        csrf = get_csrf(opener)

        if barrier:
            barrier.wait(timeout=TIMEOUT)

        data = {
            "original_url": original_url,
            "custom_alias": alias or "",
            "expiry_hours": "",
            "csrfmiddlewaretoken": csrf,
        }

        request = urllib.request.Request(
            BASE_URL + "/",
            data=urllib.parse.urlencode(data).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": BASE_URL + "/",
            },
        )

        start = time.perf_counter()

        try:
            with opener.open(request, timeout=TIMEOUT) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = response.status

        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            status = error.code

        elapsed = time.perf_counter() - start

        match = re.search(
            re.escape(BASE_URL) + r"/([A-Za-z0-9_-]{3,12})/",
            body
        )

        return {
            "status": status,
            "success": bool(match),
            "code": match.group(1) if match else None,
            "time": elapsed,
            "detail": clean_message(body),
        }

    except Exception as error:
        return {
            "status": "ERROR",
            "success": False,
            "code": None,
            "time": 0,
            "detail": str(error),
        }


def print_failure_details(results):
    failures = [r for r in results if not r["success"]]

    print("Failure status breakdown:")

    counts = Counter(str(r["status"]) for r in failures)

    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    print("\nSample failure messages:")

    for result in failures[:5]:
        print(
            f"  Status {result['status']}: "
            f"{result.get('detail', 'No details')}"
        )


def run_concurrent_creations():
    barrier = Barrier(CONCURRENT_REQUESTS)

    urls = [
        f"https://example.com/load-test/{secrets.token_hex(8)}"
        for _ in range(CONCURRENT_REQUESTS)
    ]

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [
            executor.submit(submit_link, url, None, barrier)
            for url in urls
        ]

        results = [future.result() for future in futures]

    successful = [r for r in results if r["success"]]
    codes = [r["code"] for r in successful]

    print("\nTEST 1: 200 CONCURRENT DIFFERENT URLS")
    print("Total requests:", len(results))
    print("Successful:", len(successful))
    print("Failed:", len(results) - len(successful))
    print("Unique generated codes:", len(set(codes)))
    print("Total elapsed time:", round(time.perf_counter() - start, 2), "seconds")

    print_failure_details(results)

    return codes


def run_alias_race():
    alias = "race" + secrets.token_hex(4)
    barrier = Barrier(CONCURRENT_REQUESTS)

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [
            executor.submit(
                submit_link,
                f"https://example.com/alias-race/{i}",
                alias,
                barrier,
            )
            for i in range(CONCURRENT_REQUESTS)
        ]

        results = [future.result() for future in futures]

    successes = sum(r["success"] for r in results)

    print("\nTEST 2: 200 REQUESTS COMPETING FOR ONE ALIAS")
    print("Alias:", alias)
    print("Total requests:", len(results))
    print("Successful creations:", successes)
    print("Rejected requests:", len(results) - successes)
    print("Total elapsed time:", round(time.perf_counter() - start, 2), "seconds")
    print("Expected successful creations: 1")

    print_failure_details(results)


def run_concurrent_clicks(code):
    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirectHandler())
    barrier = Barrier(CONCURRENT_REQUESTS)

    def click():
        try:
            barrier.wait(timeout=TIMEOUT)

            request = urllib.request.Request(BASE_URL + f"/{code}/")

            try:
                with opener.open(request, timeout=TIMEOUT) as response:
                    return response.status

            except urllib.error.HTTPError as error:
                return error.code

        except Exception as error:
            return f"ERROR: {error}"

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [
            executor.submit(click)
            for _ in range(CONCURRENT_REQUESTS)
        ]

        statuses = [future.result() for future in futures]

    try:
        with urllib.request.urlopen(
            BASE_URL + f"/{code}/analytics/",
            timeout=TIMEOUT
        ) as response:
            analytics = json.loads(response.read().decode())
            total_clicks = analytics["total_clicks"]

    except Exception as error:
        total_clicks = f"Could not read analytics: {error}"

    print("\nTEST 3: 200 CONCURRENT CLICKS")
    print("Total requests:", len(statuses))
    print("Successful redirects (HTTP 302):", statuses.count(302))
    print("Other responses:", len(statuses) - statuses.count(302))
    print("Response status breakdown:")

    for status, count in Counter(str(s) for s in statuses).items():
        print(f"  {status}: {count}")

    print("Analytics total_clicks:", total_clicks)
    print("Expected click count:", 200)
    print("Total elapsed time:", round(time.perf_counter() - start, 2), "seconds")


if __name__ == "__main__":
    print("Starting 200-request concurrency tests...")

    codes = run_concurrent_creations()
    run_alias_race()

    if codes:
        run_concurrent_clicks(codes[0])
    else:
        print("\nSkipping click test: no short links were created.")