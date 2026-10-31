
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache

from .models import ShortURL, ClickEvent


class ShortURLTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_create_short_url(self):
        response = self.client.post("/", {
            "original_url": "https://www.example.com",
            "custom_alias": "",
            "expiry_hours": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ShortURL.objects.count(), 1)

    def test_custom_alias_creation(self):
        response = self.client.post("/", {
            "original_url": "https://www.example.com",
            "custom_alias": "testalias",
            "expiry_hours": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ShortURL.objects.filter(
                short_code="testalias"
            ).exists()
        )

    def test_duplicate_alias_rejected(self):
        ShortURL.objects.create(
            original_url="https://www.example.com",
            short_code="testalias",
        )

        response = self.client.post("/", {
            "original_url": "https://www.google.com",
            "custom_alias": "testalias",
            "expiry_hours": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ShortURL.objects.count(), 1)

    def test_expiry_is_saved(self):
        response = self.client.post("/", {
            "original_url": "https://www.example.com",
            "custom_alias": "",
            "expiry_hours": "24",
        })

        self.assertEqual(response.status_code, 200)

        link = ShortURL.objects.get()

        self.assertIsNotNone(link.expires_at)

        self.assertGreater(
            link.expires_at,
            timezone.now(),
        )

    def test_redirect_and_click_count(self):
        link = ShortURL.objects.create(
            original_url="https://www.google.com",
            short_code="redirect1",
        )

        response = self.client.get(
            reverse(
                "redirect_short_url",
                args=["redirect1"],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            "https://www.google.com",
        )

        link.refresh_from_db()

        self.assertEqual(link.click_count, 1)
        self.assertEqual(
            ClickEvent.objects.filter(short_url=link).count(),
            1,
        )

    def test_expired_link_returns_404(self):
        link = ShortURL.objects.create(
            original_url="https://www.google.com",
            short_code="expired1",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        response = self.client.get(
            reverse(
                "redirect_short_url",
                args=["expired1"],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_analytics_endpoint(self):
        link = ShortURL.objects.create(
            original_url="https://www.google.com",
            short_code="analytics1",
        )

        ClickEvent.objects.create(
            short_url=link,
            referrer="https://www.example.com",
        )

        response = self.client.get(
            reverse(
                "analytics",
                args=["analytics1"],
            )
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["short_code"], "analytics1")
        self.assertEqual(len(data["daily_clicks"]), 1)
        self.assertEqual(len(data["referrers"]), 1)
