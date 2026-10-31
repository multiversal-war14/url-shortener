
import re

from django import forms
from .models import ShortURL


RESERVED_CODES = {
    "admin",
    "api",
    "static",
    "media",
    "favicon.ico",
}


class ShortURLForm(forms.Form):
    original_url = forms.URLField(
        label="Long URL",
        max_length=2048,
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://example.com/your/long/url",
                "class": "url-input",
            }
        ),
    )

    custom_alias = forms.CharField(
        label="Custom alias (optional)",
        required=False,
        max_length=12,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. django101",
                "class": "url-input",
            }
        ),
    )

    expiry_hours = forms.IntegerField(
        label="Expiry in hours (optional)",
        required=False,
        min_value=1,
        max_value=8760,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "e.g. 24",
                "class": "url-input",
            }
        ),
    )

    def clean_original_url(self):
        url = self.cleaned_data["original_url"]

        from urllib.parse import urlsplit
        parsed = urlsplit(url)

        if parsed.scheme not in ("http", "https"):
            raise forms.ValidationError(
                "Only HTTP and HTTPS URLs are allowed."
            )

        if not parsed.hostname:
            raise forms.ValidationError(
                "Please enter a valid destination URL."
            )

        return url

    def clean_custom_alias(self):
        alias = self.cleaned_data.get("custom_alias", "").strip()

        if not alias:
            return ""

        if not re.fullmatch(r"[A-Za-z0-9_-]{3,12}", alias):
            raise forms.ValidationError(
                "Use 3–12 letters, numbers, hyphens or underscores."
            )

        if alias.lower() in RESERVED_CODES:
            raise forms.ValidationError(
                "That alias is reserved. Please choose another."
            )

        if ShortURL.objects.filter(short_code=alias).exists():
            raise forms.ValidationError(
                "That alias is already taken. Please choose another."
            )

        return alias
