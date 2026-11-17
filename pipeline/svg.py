"""Shared SVG helpers: escaping, theme palettes, font stacks, base CSS.

GitHub serves README images as <img>, so an SVG here cannot run scripts or load
external resources. Motion comes from CSS keyframes and SMIL, which both work in
SVG-as-image in current Chrome, Firefox and Safari.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from .season import Season

SANS = "Inter,'Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif"
MONO = ("ui-monospace,SFMono-Regular,'JetBrains Mono','Cascadia Code',Consolas,"
        "'Liberation Mono',monospace")
BANGLA = "'Noto Sans Bengali','Nirmala UI','Bangla Sangam MN',Vrinda,sans-serif"

_NEUTRAL = {
    "dark": {
        "panel": "#0d1117", "border": "#30363d", "fg": "#e6edf3",
        "muted": "#8b949e", "faint": "#21262d", "ok": "#3fb950",
        "warn": "#d29922", "alert": "#f85149",
    },
    "light": {
        "panel": "#ffffff", "border": "#d0d7de", "fg": "#1f2328",
        "muted": "#59636e", "faint": "#eaeef2", "ok": "#1a7f37",
        "warn": "#9a6700", "alert": "#cf222e",
    },
}

# (accent, accent2) per theme. Light values are darkened for contrast on white.
_ACCENTS = {
    "grishmo": {"dark": ("#f4a259", "#e76f51"), "light": ("#b8621b", "#b23a1e")},
    "borsha": {"dark": ("#4cc9f0", "#4895ef"), "light": ("#0b7fa6", "#2a5fc1")},
    "shorot": {"dark": ("#9ad1f5", "#d8dee4"), "light": ("#2f78a8", "#6c757d")},
    "hemonto": {"dark": ("#e3b448", "#8fbf5a"), "light": ("#9a6b00", "#4f7d23")},
    "sheet": {"dark": ("#a9bcd9", "#e0995e"), "light": ("#4a6487", "#a65a1c")},
    "boshonto": {"dark": ("#ff7a59", "#ffc15e"), "light": ("#c2410c", "#a16207")},
}

THEMES = ("dark", "light")


def esc(value: object) -> str:
    """Escape text for use in SVG element content or attribute values."""
    return escape(str(value), {'"': "&quot;"})


def palette(season: Season, theme: str) -> dict[str, str]:
    """Merge neutral colours for ``theme`` with the season's accents."""
    if theme not in _NEUTRAL:
        raise ValueError(f"unknown theme: {theme}")
    accent, accent2 = _ACCENTS[season.key][theme]
    return {**_NEUTRAL[theme], "accent": accent, "accent2": accent2}


def base_css(p: dict[str, str]) -> str:
    """CSS shared by every asset: fonts, the entrance animation, reduced motion.

    Entrance keyframes only define the *from* state, so a renderer that ignores
    CSS animation still shows every element at full opacity.
    """
    return f"""
    .sans {{ font-family: {SANS}; }}
    .mono {{ font-family: {MONO}; }}
    .bn {{ font-family: {BANGLA}; }}
    .fg {{ fill: {p['fg']}; }}
    .muted {{ fill: {p['muted']}; }}
    .accent {{ fill: {p['accent']}; }}
    .accent2 {{ fill: {p['accent2']}; }}
    .rise {{ animation: rise .9s cubic-bezier(.2,.7,.2,1) both; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(10px); }} }}
    .fade {{ animation: fade 1.2s ease-out both; }}
    @keyframes fade {{ from {{ opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{ animation: none !important; }}
      .motion {{ display: none; }}
    }}
    """


def document(width: int, height: int, title: str, css: str, body: str,
             desc: str = "") -> str:
    """Wrap ``body`` in a standalone, accessible SVG document."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">'
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc or title)}</desc>'
        f"<style>{css}</style>{body}</svg>\n"
    )


def panel(width: int, height: int, p: dict[str, str]) -> str:
    """Rounded background panel with a hairline border."""
    return (f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" '
            f'fill="{p["panel"]}" stroke="{p["border"]}"/>')
