
import re
import time
import urllib.request
import urllib.parse
import http.cookiejar

from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://127.0.0.1:8000/"


def send_request(original_url, alias=""):
    start = time.time()

    try:
        # Each worker gets its own cookies and CSRF token.
        cookies = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookies)
        )

        # Load homepage and obtain CSRF token.
        response = opener.open(BASE_URL)
        page = response.read().decode("utf-8")

        match = re.search(
            r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
            page
        )

        if not match:
            return False, "CSRF token not found", 0

        csrf_token = match.group(1)

        # Submit the form.
        data = urllib.parse.urlencode({
            "csrfmiddlewaretoken": csrf_token,
            "original_url": original_url,
            "custom_alias": alias,
            "expiry_hours": "",
        }).encode()

        request = urllib.request.Request(
            BASE_URL,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": BASE_URL,
            },
            method="POST",
        )

        response = opener.open(request)
        result = response.read().decode("utf-8")
        status = response.status

        success = "Your short link" in result

        return success, status, round(time.time() - start, 3)

    except urllib.error.HTTPError as error:
        return False, error.code, round(time.time() - start, 3)

    except Exception as error:
        return False, str(error), round(time.time() - start, 3)


def run_test(name, requests):
    print(f"\n{'=' * 50}")
    print(name)
    print("=" * 50)

    results = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(send_request, url, alias)
            for url, alias in requests
        ]

        for future in as_completed(futures):
            results.append(future.result())

    successes = sum(1 for result in results if result[0])
    failures = len(results) - successes

    times = [
        result[2]
        for result in results
        if isinstance(result[2], float)
    ]

    print("Total requests:", len(results))
    print("Successful:", successes)
    print("Failed:", failures)

    if times:
        print("Average response time:", round(sum(times) / len(times), 3), "seconds")
        print("Maximum response time:", max(times), "seconds")

    print("\nResponse details:")
    for result in results:
        print(result)


if __name__ == "__main__":

    # Test 1: 50 different URLs.
    different_urls = [
        (f"https://example.com/page/{i}", "")
        for i in range(50)
    ]

    run_test("TEST 1: 50 CONCURRENT DIFFERENT URLS", different_urls)

    # Test 2: 20 requests competing for the same alias.
    same_alias = [
        (f"https://example.com/alias-test/{i}", "sharedtest")
        for i in range(20)
    ]

    run_test("TEST 2: 20 REQUESTS FOR THE SAME ALIAS", same_alias)
