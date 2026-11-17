"""Project cards in the style of a model card.

Each card shows one headline result, a small animated chart of it, and a
"doesn't show" line taken from the project's own stated limitations. The footer
reports whether every number on the card was found in the source README at a
pinned commit.
"""
from __future__ import annotations

from .season import Season
from .svg import base_css, document, esc, palette, panel

# 480 wide so that at 49% of GitHub's ~800px README column the text still renders
# near its designed size (about 0.8x).
W, H = 480, 350
HEAD_Y = 228            # headline baseline
BOX_Y = 266             # top edge of the "doesn't show" box
VIZ_TOP = 106
PAD = 22


def _pill(text: str, right: float, y: float, p: dict[str, str]) -> str:
    width = len(text) * 6.7 + 22
    x = right - width
    return (f'<rect x="{x:.1f}" y="{y - 15}" width="{width:.1f}" height="22" rx="11" '
            f'fill="none" stroke="{p["border"]}"/>'
            f'<text x="{x + width / 2:.1f}" y="{y}" text-anchor="middle" class="mono muted" '
            f'font-size="11">{esc(text)}</text>')


def _viz_ci(v: dict, p: dict[str, str]) -> str:
    """Point estimate with a 95% CI whisker on a zero-anchored axis."""
    x0, x1, y = PAD + 14, W - PAD - 14, 176
    span = v["axis_max"]

    def sx(value: float) -> float:
        return x0 + (x1 - x0) * value / span

    ticks = []
    for i in range(5):
        value = span * i / 4
        x = sx(value)
        ticks.append(f'<line x1="{x:.1f}" y1="{y}" x2="{x:.1f}" y2="{y + 5}" stroke="{p["muted"]}"/>'
                     f'<text x="{x:.1f}" y="{y + 18}" text-anchor="middle" class="mono muted" '
                     f'font-size="11">{value:.2f}</text>')
    lo, hi, est = sx(v["low"]), sx(v["high"]), sx(v["estimate"])
    return f"""
    <text x="{PAD}" y="{VIZ_TOP + 10}" class="mono muted" font-size="11.5">{esc(v['label'])}</text>
    <line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{p['border']}"/>
    {''.join(ticks)}
    <line x1="{x0}" y1="{y - 34}" x2="{x0}" y2="{y}" stroke="{p['muted']}" stroke-dasharray="3 3"/>
    <text x="{x0 + 6}" y="{y - 26}" class="mono muted" font-size="11">rule counts</text>
    <g class="grow" style="transform-origin:{est:.1f}px {y - 14}px">
      <line x1="{lo:.1f}" y1="{y - 14}" x2="{hi:.1f}" y2="{y - 14}" stroke="{p['accent']}" stroke-width="2.5"/>
      <line x1="{lo:.1f}" y1="{y - 20}" x2="{lo:.1f}" y2="{y - 8}" stroke="{p['accent']}" stroke-width="2"/>
      <line x1="{hi:.1f}" y1="{y - 20}" x2="{hi:.1f}" y2="{y - 8}" stroke="{p['accent']}" stroke-width="2"/>
    </g>
    <circle cx="{est:.1f}" cy="{y - 14}" r="5.5" fill="{p['accent2']}" class="rise" style="animation-delay:.9s"/>
    <text x="{est:.1f}" y="{y - 28}" text-anchor="middle" class="mono fg rise" font-size="13"
      font-weight="700" style="animation-delay:1s">+{v['estimate']:.3f}</text>
    """


def _viz_seeds(v: dict, p: dict[str, str]) -> str:
    """One dot per holdout seed, then the cost comparison as two bars."""
    parts = [f'<text x="{PAD}" y="{VIZ_TOP + 10}" class="mono muted" font-size="11.5">'
             f'holdout seeds won</text>']
    for i in range(v["total"]):
        cx = PAD + 140 + i * 30
        won = i < v["won"]
        fill = p["accent"] if won else "none"
        parts.append(f'<circle cx="{cx}" cy="{VIZ_TOP + 6}" r="8" fill="{fill}" stroke="{p["accent"]}" '
                     f'stroke-width="1.5" class="pop" style="animation-delay:{0.3 + i * 0.18:.2f}s"/>')
    top = max(b["value"] for b in v["bars"])
    for i, bar in enumerate(v["bars"]):
        y = VIZ_TOP + 34 + i * 26
        width = (W - 2 * PAD - 210) * bar["value"] / top
        colour = p["accent2"] if i == len(v["bars"]) - 1 else p["muted"]
        parts.append(
            f'<text x="{PAD}" y="{y + 12}" class="mono muted" font-size="12">{esc(bar["label"])}</text>'
            f'<rect x="{PAD + 140}" y="{y}" width="{width:.1f}" height="16" rx="3" fill="{colour}" '
            f'fill-opacity=".85" class="bar" style="animation-delay:{1.2 + i * 0.25:.2f}s"/>'
            f'<text x="{PAD + 148 + width:.1f}" y="{y + 12}" class="mono fg rise" font-size="12" '
            f'style="animation-delay:{1.9 + i * 0.25:.2f}s">'
            f'{bar["value"]}</text>')
    parts.append(f'<text x="{PAD + 140}" y="{VIZ_TOP + 98}" class="mono muted" font-size="11">'
                 f'{esc(v["unit"])}</text>')
    return "".join(parts)


def _viz_gate(v: dict, p: dict[str, str]) -> str:
    """Rows stream through a validation gate; anomalies divert to an audit table."""
    y = VIZ_TOP + 30
    gate_x = int(W * 0.46)
    straight = f"M{PAD},{y} L{W - PAD - 70},{y}"
    divert = f"M{PAD},{y} L{gate_x - 6},{y} C{gate_x + 30},{y} {gate_x + 40},{y + 50} {gate_x + 90},{y + 54}"
    rows = []
    # (path, colour, begin offset): a fixed loop pattern, not a count of anything.
    pattern = [(straight, p["muted"]), (straight, p["muted"]), (divert, p["alert"]),
               (straight, p["muted"]), (straight, p["muted"]), (straight, p["muted"]),
               (divert, p["alert"]), (straight, p["muted"])]
    dur = 8.0
    for i, (path, colour) in enumerate(pattern):
        begin = -i * dur / len(pattern)
        rows.append(
            f'<rect x="-9" y="-4" width="18" height="8" rx="2" fill="{colour}" class="motion">'
            f'<animateMotion dur="{dur}s" begin="{begin:.2f}s" repeatCount="indefinite" path="{path}"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.06;.88;1" dur="{dur}s" '
            f'begin="{begin:.2f}s" repeatCount="indefinite"/></rect>')
    return f"""
    <text x="{PAD}" y="{VIZ_TOP + 10}" class="mono muted" font-size="11.5">bronze</text>
    <line x1="{PAD}" y1="{y}" x2="{W - PAD - 70}" y2="{y}" stroke="{p['faint']}" stroke-width="12" stroke-linecap="round"/>
    <path d="M{gate_x - 6},{y} C{gate_x + 30},{y} {gate_x + 40},{y + 50} {gate_x + 90},{y + 54}"
      fill="none" stroke="{p['faint']}" stroke-width="12" stroke-linecap="round"/>
    <rect x="{gate_x - 3}" y="{y - 20}" width="6" height="40" rx="3" fill="{p['accent']}"/>
    <text x="{gate_x}" y="{y - 26}" text-anchor="middle" class="mono accent" font-size="11.5">{esc(v['gate_label'])}</text>
    <text x="{W - PAD - 60}" y="{y + 4}" class="mono muted" font-size="11.5">{esc(v['pass_label'])}</text>
    <rect x="{gate_x + 92}" y="{y + 42}" width="120" height="24" rx="4" fill="none"
      stroke="{p['alert']}" stroke-dasharray="3 3"/>
    <text x="{gate_x + 152}" y="{y + 58}" text-anchor="middle" class="mono" font-size="11.5"
      fill="{p['alert']}">{esc(v['fail_label'])}</text>
    {''.join(rows)}
    """


def _viz_stack(v: dict, p: dict[str, str]) -> str:
    """Catalogue composition as one stacked bar, segments growing in order."""
    total = sum(s["value"] for s in v["segments"])
    x, y, full = PAD, VIZ_TOP + 26, W - 2 * PAD
    colours = [p["accent"], p["accent2"], p["muted"]]
    parts = [f'<text x="{PAD}" y="{VIZ_TOP + 10}" class="mono muted" font-size="11.5">'
             f'catalogue by source</text>']
    for i, seg in enumerate(v["segments"]):
        width = full * seg["value"] / total
        parts.append(
            f'<rect x="{x:.1f}" y="{y}" width="{max(width - 3, 1):.1f}" height="24" rx="3" '
            f'fill="{colours[i % 3]}" class="bar" style="animation-delay:{0.4 + i * 0.35:.2f}s"/>'
            f'<text x="{x:.1f}" y="{y + 44}" class="mono fg rise" font-size="12.5" font-weight="600" '
            f'style="animation-delay:{0.6 + i * 0.35:.2f}s">{seg["value"]}</text>'
            f'<text x="{x:.1f}" y="{y + 60}" class="mono muted rise" font-size="11" '
            f'style="animation-delay:{0.6 + i * 0.35:.2f}s">{esc(seg["label"])}</text>')
        x += width
    return "".join(parts)


VIZ = {"ci": _viz_ci, "seeds": _viz_seeds, "gate": _viz_gate, "stack": _viz_stack}


def _footer(card: dict, verdict: dict, p: dict[str, str]) -> str:
    state = verdict["state"]
    if state == "verified":
        colour, text = p["ok"], f"claims verified · README @ {verdict['sha'][:7]}"
    elif state == "stale":
        colour, text = p["alert"], f"stale claim · README @ {verdict['sha'][:7]}"
    else:
        colour, text = p["warn"], "unverified · offline preview"
    return (f'<circle cx="{PAD + 4}" cy="{H - 22}" r="4" fill="{colour}"/>'
            f'<text x="{PAD + 14}" y="{H - 18}" class="mono muted" font-size="11">{esc(text)}</text>'
            f'<text x="{W - PAD}" y="{H - 18}" text-anchor="end" class="mono muted" '
            f'font-size="11">{esc(card["stack"])}</text>')


def render(card: dict, verdict: dict, season: Season, theme: str) -> str:
    p = palette(season, theme)
    css = base_css(p) + """
    .grow { animation: grow 1s .5s cubic-bezier(.2,.7,.2,1) both; }
    @keyframes grow { from { transform: scaleX(0); } }
    .bar { transform-box: fill-box; transform-origin: left center;
      animation: bar 1s cubic-bezier(.2,.7,.2,1) both; }
    @keyframes bar { from { transform: scaleX(0); } }
    .pop { transform-box: fill-box; transform-origin: center;
      animation: pop .5s cubic-bezier(.3,1.6,.5,1) both; }
    @keyframes pop { from { transform: scale(0); } }
    """
    summary = "".join(
        f'<text x="{PAD}" y="{66 + i * 19}" class="sans muted" font-size="14">{esc(line)}</text>'
        for i, line in enumerate(card["summary"]))
    limitation = "".join(
        f'<text x="{PAD + 14}" y="{BOX_Y + 22 + i * 17}" class="sans muted" font-size="12.5">{esc(line)}</text>'
        for i, line in enumerate(card["limitation"]))
    body = f"""
    {panel(W, H, p)}
    <text x="{PAD}" y="38" class="mono fg" font-size="19" font-weight="700">{esc(card['title'])}</text>
    {_pill(card['status'], W - PAD, 37, p)}
    {summary}
    {VIZ[card['viz']['type']](card['viz'], p)}
    <text x="{PAD}" y="{HEAD_Y}" class="sans fg" font-size="16" font-weight="650">{esc(card['headline'])}</text>
    <text x="{PAD}" y="{HEAD_Y + 20}" class="sans muted" font-size="13">{esc(card['subline'])}</text>
    <rect x="{PAD}" y="{BOX_Y}" width="{W - 2 * PAD}" height="{14 + 17 * len(card['limitation'])}" rx="6"
      fill="none" stroke="{p['border']}" stroke-dasharray="4 4"/>
    <rect x="{PAD + 9}" y="{BOX_Y - 6}" width="100" height="12" fill="{p['panel']}"/>
    <text x="{PAD + 14}" y="{BOX_Y + 3.5}" class="mono" font-size="10" fill="{p['warn']}"
      letter-spacing="1.2">DOESN'T SHOW</text>
    {limitation}
    {_footer(card, verdict, p)}
    """
    desc = (f"{card['title']}: {' '.join(card['summary'])} Result: {card['headline']} "
            f"({card['subline']}). Limitation: {' '.join(card['limitation'])}")
    return document(W, H, f"{card['title']} project card", css, body, desc)
