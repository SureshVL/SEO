"""White-label branding config for PDF / HTML reports.

Stored as JSON inside `projects.settings.branding`. Keeps everything
optional with safe defaults so the stock Omni-Rank palette is used
when branding isn't configured.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


DEFAULT_PRIMARY = "#c87941"
DEFAULT_SECONDARY = "#8b5a2b"
DEFAULT_ACCENT = "#1D9E75"
DEFAULT_TEXT = "#2c2723"
DEFAULT_BG = "#faf8f5"


@dataclass
class BrandingConfig:
    """Per-project white-label config. All fields optional."""
    agency_name: str = ""
    logo_url: str = ""
    primary_color: str = DEFAULT_PRIMARY
    secondary_color: str = DEFAULT_SECONDARY
    accent_color: str = DEFAULT_ACCENT
    text_color: str = DEFAULT_TEXT
    background_color: str = DEFAULT_BG
    cover_title: str = ""
    cover_subtitle: str = ""
    footer_text: str = ""
    website: str = ""
    email: str = ""
    enabled: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BrandingConfig":
        if not data:
            return cls()
        fields = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in fields and v is not None}
        return cls(**clean)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def resolved_agency_name(self, fallback: str = "OMNI-RANK") -> str:
        return self.agency_name.strip() or fallback

    def resolved_cover_title(self, project_name: str = "") -> str:
        return self.cover_title.strip() or (
            f"SEO Performance Report — {project_name}" if project_name
            else "SEO Performance Report"
        )

    def resolved_footer(self, fallback_agency: str = "OMNI-RANK") -> str:
        if self.footer_text.strip():
            return self.footer_text
        return f"Confidential — prepared by {self.resolved_agency_name(fallback_agency)}"

    def logo_html(self, fallback_text: str = "") -> str:
        """Return <img> tag for logo_url, or a text monogram fallback."""
        if self.logo_url:
            return (
                f'<img src="{self.logo_url}" alt="{self.resolved_agency_name(fallback_text)}" '
                f'style="max-height:48px;max-width:200px;display:block;" />'
            )
        return ""

    def validate(self) -> list[str]:
        """Return a list of validation warnings (invalid colors etc.)."""
        warnings: list[str] = []
        for attr in ("primary_color", "secondary_color", "accent_color", "text_color", "background_color"):
            val = getattr(self, attr)
            if val and not _is_hex_color(val):
                warnings.append(f"{attr} '{val}' is not a valid hex color")
        if self.logo_url and not (self.logo_url.startswith("http://") or self.logo_url.startswith("https://")):
            warnings.append("logo_url must be an absolute http(s) URL")
        return warnings


def _is_hex_color(value: str) -> bool:
    if not value.startswith("#"):
        return False
    rest = value[1:]
    if len(rest) not in (3, 6, 8):
        return False
    try:
        int(rest, 16)
    except ValueError:
        return False
    return True
