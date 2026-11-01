
import secrets
import string
import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F, Q, Count
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from .forms import ShortURLForm
from .models import ShortURL, ClickEvent


ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7
DB_RETRIES = 8


def retry_database_operation(operation):
    for attempt in range(DB_RETRIES):
        try:
            return operation()
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            if attempt == DB_RETRIES - 1:
                raise
            time.sleep(0.1 * (attempt + 1))


def is_rate_limited(request):
    limit = getattr(settings, "SHORTENER_RATE_LIMIT", 3)
    window = getattr(settings, "SHORTENER_RATE_WINDOW", 60)

    client_ip = request.META.get("REMOTE_ADDR") or "unknown"
    cache_key = f"shortener:rate:{client_ip}"

    if cache.add(cache_key, 1, timeout=window):
        return False

    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.add(cache_key, 1, timeout=window)
        count = 1

    return count > limit


def generate_code():
    return "".join(
        secrets.choice(ALPHABET) for _ in range(CODE_LENGTH)
    )


def create_short_url(original_url, code, expires_at):
    def operation():
        with transaction.atomic():
            return ShortURL.objects.create(
                original_url=original_url,
                short_code=code,
                expires_at=expires_at,
            )

    return retry_database_operation(operation)


def home(request):
    short_url = None
    form = ShortURLForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        original_url = form.cleaned_data["original_url"]
        alias = form.cleaned_data["custom_alias"]
        expiry_hours = form.cleaned_data["expiry_hours"]

        if not alias and expiry_hours is None:
            existing = ShortURL.objects.filter(
                original_url=original_url
            ).filter(
                Q(expires_at__isnull=True)
                | Q(expires_at__gt=timezone.now())
            ).first()

            if existing:
                short_url = request.build_absolute_uri(
                    reverse(
                        "redirect_short_url",
                        args=[existing.short_code],
                    )
                )

        if short_url is None:
            if is_rate_limited(request):
                form.add_error(
                    None,
                    "Too many link creations. Please wait before trying again.",
                )
                return render(
                    request,
                    "shortener/home.html",
                    {"form": form, "short_url": None},
                    status=429,
                )

            expires_at = None
            if expiry_hours is not None:
                expires_at = timezone.now() + timedelta(
                    hours=expiry_hours
                )

            attempts = 1 if alias else 10

            for _ in range(attempts):
                code = alias or generate_code()

                try:
                    link = create_short_url(
                        original_url,
                        code,
                        expires_at,
                    )

                    short_url = request.build_absolute_uri(
                        reverse(
                            "redirect_short_url",
                            args=[link.short_code],
                        )
                    )

                    # Remove any stale cached entry.
                    cache.delete(f"shortener:redirect:{link.short_code}")
                    break

                except IntegrityError:
                    if alias:
                        form.add_error(
                            "custom_alias",
                            "That alias was claimed by another request. Please choose another.",
                        )
                        break

                except OperationalError:
                    if alias:
                        form.add_error(
                            None,
                            "The database is busy. Please try again.",
                        )
                        break

            if short_url is None and not form.errors:
                return HttpResponse(
                    "Could not generate a unique code. Please try again.",
                    status=503,
                )

    return render(
        request,
        "shortener/home.html",
        {"form": form, "short_url": short_url},
    )


def redirect_short_url(request, code):
    cache_key = f"shortener:redirect:{code}"
    cached_link = cache.get(cache_key)

    if cached_link is not None:
        link_id = cached_link["id"]
        original_url = cached_link["original_url"]
        expires_at = cached_link["expires_at"]

    else:
        try:
            link = ShortURL.objects.get(short_code=code)
        except ShortURL.DoesNotExist:
            raise Http404("Short link not found.")

        link_id = link.id
        original_url = link.original_url
        expires_at = link.expires_at

        timeout = getattr(
            settings,
            "SHORTENER_REDIRECT_CACHE_TIMEOUT",
            300,
        )

        if expires_at is not None:
            remaining = (expires_at - timezone.now()).total_seconds()

            if remaining <= 0:
                raise Http404("This short link has expired.")

            timeout = min(timeout, max(1, int(remaining)))

        cache.set(
            cache_key,
            {
                "id": link_id,
                "original_url": original_url,
                "expires_at": expires_at,
            },
            timeout=timeout,
        )

    if expires_at is not None and expires_at <= timezone.now():
        cache.delete(cache_key)
        raise Http404("This short link has expired.")

    referrer = request.META.get("HTTP_REFERER", "")

    def record_click():
        with transaction.atomic():
            ShortURL.objects.filter(pk=link_id).update(
                click_count=F("click_count") + 1
            )

            ClickEvent.objects.create(
                short_url_id=link_id,
                referrer=referrer,
            )

    try:
        retry_database_operation(record_click)
    except OperationalError:
        return HttpResponse(
            "The service is temporarily busy. Please try again.",
            status=503,
        )

    return redirect(original_url)


def analytics(request, code):
    try:
        link = ShortURL.objects.get(short_code=code)
    except ShortURL.DoesNotExist:
        raise Http404("Short link not found.")

    daily_clicks = (
        ClickEvent.objects
        .filter(short_url=link)
        .annotate(day=TruncDate("clicked_at"))
        .values("day")
        .annotate(clicks=Count("id"))
        .order_by("day")
    )

    referrer_stats = (
        ClickEvent.objects
        .filter(short_url=link)
        .values("referrer")
        .annotate(clicks=Count("id"))
        .order_by("-clicks")
    )

    referrers = [
        {
            "referrer": item["referrer"] or "Direct",
            "clicks": item["clicks"],
        }
        for item in referrer_stats
    ]

    return JsonResponse({
        "short_code": link.short_code,
        "total_clicks": link.click_count,
        "daily_clicks": [
            {
                "date": item["day"].isoformat(),
                "clicks": item["clicks"],
            }
            for item in daily_clicks
        ],
        "referrers": referrers,
    })
