
from django.db import models


class ShortURL(models.Model):
    original_url = models.URLField(max_length=2048)

    short_code = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    click_count = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"



class ClickEvent(models.Model):
    short_url = models.ForeignKey(
        ShortURL,
        on_delete=models.CASCADE,
        related_name="click_events",
    )

    clicked_at = models.DateTimeField(auto_now_add=True)

    referrer = models.URLField(
        max_length=2048,
        blank=True,
        default="",
    )

    def __str__(self):
        return f"Click on {self.short_url.short_code} at {self.clicked_at}"
