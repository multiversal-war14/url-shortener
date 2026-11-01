
import ipaddress
import re
from urllib.parse import urlsplit

from django import forms
from django.conf import settings

from .models import ShortURL


RESERVED_CODES = {
    "admin",
    "api",
    "static",
    "media",
    "favicon.ico",
}

INTERNAL_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}

INTERNAL_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home",
    ".test",
)


def validate_destination_url(url):
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname

        # Only HTTP and HTTPS are allowed.
        if parsed.scheme.lower() not in ("http", "https"):
            raise forms.ValidationError(
                "Only HTTP and HTTPS URLs are allowed."
            )

        if not hostname:
            raise forms.ValidationError(
                "Please enter a valid destination URL."
            )

        # Reject malformed ports.
        try:
            parsed.port
        except ValueError:
            raise forms.ValidationError(
                "Please enter a valid destination URL."
            )

        hostname = hostname.rstrip(".").lower()

        # Reject localhost and common internal hostnames.
        if hostname in INTERNAL_HOSTNAMES or any(
            hostname.endswith(suffix)
            for suffix in INTERNAL_SUFFIXES
        ):
            raise forms.ValidationError(
                "Internal or localhost destinations are not allowed."
            )

        # If the hostname is an IP address, allow only globally
        # routable public IP addresses.
        try:
            ip = ipaddress.ip_address(hostname)

            if not ip.is_global:
                raise forms.ValidationError(
                    "Private, reserved and internal IP addresses "
                    "are not allowed."
                )

        except ValueError:
            # It is a hostname rather than an IP address.
            pass

        # Prevent links pointing back to this shortener service.
        public_base_url = getattr(
            settings,
            "SHORTENER_PUBLIC_BASE_URL",
            ""
        )

        if public_base_url:
            service_hostname = urlsplit(
                public_base_url
            ).hostname

            if service_hostname and (
                hostname == service_hostname.rstrip(".").lower()
            ):
                raise forms.ValidationError(
                    "Redirects to this URL shortener are not allowed."
                )

    except ValueError:
        raise forms.ValidationError(
            "Please enter a valid destination URL."
        )


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
        validate_destination_url(url)
        return url

    def clean_custom_alias(self):
        alias = self.cleaned_data.get("custom_alias", "").strip()

        if not alias:
            return ""

        if not re.fullmatch(r"[A-Za-z0-9_-]{3,12}", alias):
            raise forms.ValidationError(
                "Use 3-12 letters, numbers, hyphens or underscores."
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
