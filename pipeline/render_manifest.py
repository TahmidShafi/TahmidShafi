"""Run manifest footer: what the last pipeline run read, checked and published."""
from __future__ import annotations

from .season import Season
from .svg import base_css, document, esc, palette, panel

W, H = 1200, 210


def render(manifest: dict, season: Season, theme: str) -> str:
    p = palette(season, theme)
    checks = manifest["checks"]
    hard = [c for c in checks if c["severity"] == "hard"]
    claims = manifest["claims"]
    fixture = manifest["mode"] == "fixture"

    verified = sum(1 for c in claims.values() if c["state"] == "verified")
    claim_text = ("claims not checked (offline preview)" if fixture
                  else f"{verified}/{len(claims)} cards verified against source READMEs")
    repos = manifest["extract"].get("public_repos")
    lines = [
        ("$", f"python -m pipeline.run --mode {manifest['mode']}", "accent"),
        ("extract", f"{manifest['extract']['days']} days of contributions"
                    + (f" · {repos} public repos" if repos is not None else "")
                    + f" · {len(claims)} source READMEs", "fg"),
        ("validate", f"{sum(c['ok'] for c in hard)}/{len(hard)} hard checks passed · {claim_text}", "fg"),
        ("publish", f"write-audit-publish → assets/ · {manifest['generated_at']}"
                    + (f" · run #{manifest['run_number']}" if manifest.get("run_number") else ""), "fg"),
    ]
    rows = []
    for i, (key, text, cls) in enumerate(lines):
        y = 72 + i * 25
        rows.append(
            f'<g class="rise" style="animation-delay:{0.2 + i * 0.35:.2f}s">'
            f'<text x="40" y="{y}" class="mono muted" font-size="14">{esc(key)}</text>'
            f'<text x="136" y="{y}" class="mono {cls}" font-size="14">{esc(text)}</text></g>')
    y_season = 72 + len(lines) * 25
    rows.append(
        f'<g class="rise" style="animation-delay:{0.2 + len(lines) * 0.35:.2f}s">'
        f'<text x="40" y="{y_season}" class="mono muted" font-size="14">palette</text>'
        f'<text x="136" y="{y_season}" class="fg" font-size="14"><tspan class="bn">{esc(season.bangla)}</tspan>'
        f'<tspan class="mono" dx="8">{esc(season.latin)} ({esc(season.english)}) · {esc(season.motif)}</tspan>'
        f'</text></g>')
    status, colour = (("FIXTURE", p["warn"]) if fixture else
                      ("PASS", p["ok"]) if all(c["ok"] for c in hard) else ("FAIL", p["alert"]))
    css = base_css(p) + """
    .cursor { animation: blink 1.1s steps(1) infinite; }
    @keyframes blink { 50% { opacity: 0; } }
    """
    body = f"""
    {panel(W, H, p)}
    <rect x="16" y="22" width="3" height="{H - 44}" rx="1.5" fill="{p['accent']}"/>
    <text x="40" y="36" class="mono accent" font-size="12" letter-spacing="2.4" font-weight="600">RUN MANIFEST</text>
    <text x="{W - 40}" y="36" text-anchor="end" class="mono" font-size="12" font-weight="700"
      fill="{colour}">● {status}</text>
    {''.join(rows)}
    <rect x="136" y="{y_season + 12}" width="9" height="15" fill="{p['accent']}" class="cursor"/>
    """
    desc = (f"Pipeline run manifest. Mode {manifest['mode']}, generated {manifest['generated_at']}, "
            f"{sum(c['ok'] for c in hard)} of {len(hard)} hard checks passed. {claim_text}.")
    return document(W, H, "Profile pipeline run manifest", css, body, desc)
