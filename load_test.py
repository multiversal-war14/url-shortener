import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar

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
        html = response.read().decode("utf-8", errors="replace")

    match = re.search(
        r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
        html
    )
    if not match:
        raise RuntimeError("Could not find CSRF token on homepage.")

    return match.group(1)


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

        # The app displays the generated absolute short URL in the page.
        match = re.search(
            re.escape(BASE_URL) + r"/([A-Za-z0-9_-]{3,12})/",
            body
        )

        return {
            "status": status,
            "success": bool(match),
            "code": match.group(1) if match else None,
            "time": elapsed,
        }

    except Exception as error:
        return {
            "status": "ERROR",
            "success": False,
            "code": None,
            "time": 0,
            "error": str(error),
        }


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

    print("\nTEST 1: 200 CONCURRENT DIFFERENT URLS")
    print("Total requests:", len(results))
    print("Successful:", sum(r["success"] for r in results))
    print("Failed:", sum(not r["success"] for r in results))
    print("Unique generated codes:", len({
        r["code"] for r in results if r["code"]
    }))
    print("Total elapsed time:", round(time.perf_counter() - start, 2), "seconds")

    successful_codes = [r["code"] for r in results if r["success"]]
    return successful_codes


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


def run_concurrent_clicks(code):
    # Do not follow redirects: we only need to verify the shortener's 302 response.
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
            return str(error)

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [executor.submit(click) for _ in range(CONCURRENT_REQUESTS)]
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
    print("Analytics total_clicks:", total_clicks)
    print("Expected click count: 200")
    print("Total elapsed time:", round(time.perf_counter() - start, 2), "seconds")


if __name__ == "__main__":
    print("Starting 200-request concurrency tests...")
    codes = run_concurrent_creations()
    run_alias_race()

    if codes:
        run_concurrent_clicks(codes[0])
    else:
        print("\nSkipping click test: no short link was created.")