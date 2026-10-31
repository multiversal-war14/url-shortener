
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
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
        secrets.choice(ALPHABET)
        for _ in range(CODE_LENGTH)
    )


def home(request):
    short_url = None
    form = ShortURLForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        original_url = form.cleaned_data["original_url"]
        alias = form.cleaned_data["custom_alias"]
        expiry_hours = form.cleaned_data["expiry_hours"]

        # Reuse an existing active link for plain requests.
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

        # Apply rate limiting only when creating a new link.
        if short_url is None:

            if is_rate_limited(request):
                form.add_error(
                    None,
                    "Too many link creations. Please wait "
                    "before trying again.",
                )

                return render(
                    request,
                    "shortener/home.html",
                    {
                        "form": form,
                        "short_url": None,
                    },
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
                    with transaction.atomic():
                        link = ShortURL.objects.create(
                            original_url=original_url,
                            short_code=code,
                            expires_at=expires_at,
                        )

                    short_url = request.build_absolute_uri(
                        reverse(
                            "redirect_short_url",
                            args=[link.short_code],
                        )
                    )

                    break

                except IntegrityError:

                    if alias:
                        form.add_error(
                            "custom_alias",
                            "That alias was claimed by another "
                            "request. Please choose another.",
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
        {
            "form": form,
            "short_url": short_url,
        },
    )


def redirect_short_url(request, code):

    try:
        link = ShortURL.objects.get(short_code=code)

    except ShortURL.DoesNotExist:
        raise Http404("Short link not found.")

    if link.expires_at and link.expires_at <= timezone.now():
        raise Http404("This short link has expired.")

    ShortURL.objects.filter(pk=link.pk).update(
        click_count=F("click_count") + 1
    )

    referrer = request.META.get("HTTP_REFERER", "")

    ClickEvent.objects.create(
        short_url=link,
        referrer=referrer,
    )

    return redirect(link.original_url)


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

