"""Hero banner: identity on the left, a data 'river delta' on the right.

Bangladesh's rivers run north to south and merge before reaching the Bay of
Bengal. The banner draws Tahmid's real data sources as headwaters that join at
confluences, which double as pipeline stages, and drain into a bay of outputs.
Overlapping channel segments get wider downstream, as a river does.
"""
from __future__ import annotations

from .season import Season
from .svg import base_css, document, esc, palette, panel

W, H = 1200, 500

# Headwaters: (x, name, kind). Every source here is used by a real project.
SOURCES = [
    (660, "DGHS portal", "dengue tables"),
    (775, "Open-Meteo", "weather archive"),
    (890, "FCTB 2013", "food composition"),
    (1005, "BBS HIES 2022", "calibration"),
    (1120, "simulators", "synthetic data"),
]
SOURCE_Y = 76

# Shared downstream segments (cubic Bezier continuations).
T1 = "C820,225 850,250 880,280 "   # confluence 1 -> 2
T2 = "C905,305 930,325 960,340 "   # confluence 2 -> 3
T3 = "C990,362 966,390 935,404 "   # confluence 3 -> river mouth
# Distributaries: the delta fans back out to the bay, one per kind of output.
MOUTH = (935, 404)
DELTA = [
    ("C910,418 882,430 860,446", (860, 446), "tables"),
    ("C941,420 946,434 946,450", (946, 450), "dashboards"),
    ("C966,418 1004,430 1032,446", (1032, 446), "write-ups"),
]
_UPPER = [
    f"M660,{SOURCE_Y} C660,140 720,170 780,200 " + T1 + T2 + T3,
    f"M775,{SOURCE_Y} C775,130 785,170 780,200 " + T1 + T2 + T3,
    f"M890,{SOURCE_Y} C895,160 870,220 880,280 " + T2 + T3,
    f"M1005,{SOURCE_Y} C1010,170 990,280 960,340 " + T3,
    f"M1120,{SOURCE_Y} C1120,200 1040,300 960,340 " + T3,
]
# Each headwater drains through a distributary so particles fan out at the coast.
HEADS = [d + DELTA[i % 3][0] for i, d in enumerate(_UPPER)]
# Stage bands drawn across the river, one per confluence.
STAGES = [(SOURCE_Y, "sources"), (200, "extract"), (280, "validate"),
          (340, "transform"), (404, "publish")]
CONFLUENCES = [(780, 200), (880, 280), (960, 340)]


def _river(p: dict[str, str]) -> str:
    parts = []
    # Stage bands first, so the river draws over them.
    for y, label in STAGES:
        parts.append(f'<line x1="664" y1="{y}" x2="1170" y2="{y}" stroke="{p["faint"]}" '
                     f'stroke-dasharray="2 6"/>')
        parts.append(f'<text x="584" y="{y + 4}" class="mono muted" font-size="12.5">{label}</text>')

    # Thin headwater channels.
    for d in HEADS:
        parts.append(f'<path d="{d}" fill="none" stroke="{p["accent"]}" stroke-opacity=".35" '
                     f'stroke-width="1.6" stroke-linecap="round"/>')
    # Main stem widens after each confluence; distributaries thin out again.
    stems = [("M780,200 " + T1, 3.5), ("M880,280 " + T2, 5.5), ("M960,340 " + T3, 8)]
    stems += [(f"M{MOUTH[0]},{MOUTH[1]} " + d, 3) for d, _, _ in DELTA]
    for d, width in stems:
        parts.append(f'<path d="{d}" fill="none" stroke="{p["accent"]}" stroke-opacity=".28" '
                     f'stroke-width="{width}" stroke-linecap="round"/>')
    # Flowing texture over every channel.
    for d in HEADS:
        parts.append(f'<path d="{d}" class="flow" fill="none" stroke="{p["accent"]}" '
                     f'stroke-width="1.2" stroke-linecap="round"/>')

    # Headwater nodes with labels and a slow pulse.
    for i, (x, name, kind) in enumerate(SOURCES):
        parts.append(
            f'<g class="rise" style="animation-delay:{0.5 + i * 0.12:.2f}s">'
            f'<circle cx="{x}" cy="{SOURCE_Y}" r="4" fill="{p["accent"]}"/>'
            f'<circle cx="{x}" cy="{SOURCE_Y}" r="4" fill="none" stroke="{p["accent"]}" '
            f'class="pulse" style="animation-delay:{i * 0.6:.1f}s"/>'
            f'<text x="{x}" y="{SOURCE_Y - 32}" text-anchor="middle" class="mono fg" '
            f'font-size="13" font-weight="600">{esc(name)}</text>'
            f'<text x="{x}" y="{SOURCE_Y - 14}" text-anchor="middle" class="mono muted" '
            f'font-size="11.5">{esc(kind)}</text></g>')

    for d, (x, y), label in DELTA:
        parts.append(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{p["accent2"]}"/>'
                     f'<text x="{x}" y="{y + 18}" text-anchor="middle" class="mono muted" '
                     f'font-size="12">{label}</text>')

    for x, y in CONFLUENCES:
        parts.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{p["panel"]}" '
                     f'stroke="{p["accent"]}" stroke-width="1.5"/>')

    # Particles: negative begin offsets put them mid-flight on first paint.
    for i, d in enumerate(HEADS):
        dur = 7.5 - i * 0.7
        for k in range(3):
            begin = -(k * dur / 3 + i * 0.4)
            colour = p["accent2"] if k == 1 else p["accent"]
            parts.append(
                f'<circle r="2.6" fill="{colour}" class="motion" filter="url(#glow)">'
                f'<animateMotion dur="{dur:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite" '
                f'path="{d}"/>'
                f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.08;.9;1" '
                f'dur="{dur:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite"/></circle>')

    # The bay: drifting wave lines below the mouth.
    waves = []
    for row, y in enumerate((478, 486, 494)):
        d = " ".join(f"q 15 {-4 if j % 2 == 0 else 4} 30 0" for j in range(30))
        waves.append(f'<path d="M560,{y} {d}" fill="none" stroke="{p["accent"]}" '
                     f'stroke-opacity="{0.45 - row * 0.12:.2f}" stroke-width="1.2" '
                     f'class="wave" style="animation-duration:{6 + row * 2}s"/>')
    parts.append(f'<g clip-path="url(#bay)">{"".join(waves)}</g>')
    return "".join(parts)


def _identity(p: dict[str, str], season: Season) -> str:
    return f"""
    <text x="56" y="76" class="mono accent rise" font-size="12" letter-spacing="2.4"
      font-weight="600" style="animation-delay:.05s">DATA ENGINEERING · ANALYTICS</text>
    <text x="54" y="150" class="sans fg rise" font-size="60" font-weight="700"
      letter-spacing="-1.5" style="animation-delay:.15s">Tahmid Jawad</text>
    <text x="54" y="216" class="sans accent rise" font-size="60" font-weight="700"
      letter-spacing="-1.5" style="animation-delay:.3s">Shafi</text>
    <text x="56" y="268" class="sans fg rise" font-size="21" style="animation-delay:.5s">I build data pipelines that</text>
    <text x="56" y="296" class="sans fg rise" font-size="21" font-weight="600"
      style="animation-delay:.6s">show their work.</text>
    <path d="M56,306 C100,302 150,309 214,303" fill="none" stroke="{p['accent2']}"
      stroke-width="2.4" stroke-linecap="round" class="draw"/>
    <text x="56" y="346" class="mono muted rise" font-size="14" style="animation-delay:.8s">CSE @ AIUB · Dhaka, Bangladesh</text>
    <text x="56" y="369" class="mono muted rise" font-size="14" style="animation-delay:.9s">graduating Jun 2027 · open to roles from Jan 2027</text>
    <g class="rise" style="animation-delay:1.1s">
      <rect x="56" y="398" width="476" height="30" rx="15" fill="none" stroke="{p['border']}"/>
      <circle cx="74" cy="413" r="5" fill="{p['accent']}"/>
      <text x="88" y="418" class="fg" font-size="14"><tspan class="bn">{esc(season.bangla)}</tspan><tspan
        class="mono" dx="6" font-size="12.5">{esc(season.latin)} palette · set by today's Bangla season</tspan></text>
    </g>
    """


def render(season: Season, theme: str) -> str:
    p = palette(season, theme)
    css = base_css(p) + f"""
    .flow {{ stroke-dasharray: 2 10; animation: flow 1.4s linear infinite; opacity: .9; }}
    @keyframes flow {{ to {{ stroke-dashoffset: -12; }} }}
    .pulse {{ transform-box: fill-box; transform-origin: center;
      animation: pulse 3s ease-out infinite; }}
    @keyframes pulse {{ from {{ transform: scale(1); opacity: .9; }}
      to {{ transform: scale(3.2); opacity: 0; }} }}
    .wave {{ animation: drift linear infinite; }}
    @keyframes drift {{ to {{ transform: translateX(60px); }} }}
    .draw {{ stroke-dasharray: 170; animation: draw 1.1s 1s ease-out both; }}
    @keyframes draw {{ from {{ stroke-dashoffset: 170; }} }}
    """
    defs = f"""<defs>
      <filter id="glow" x="-200%" y="-200%" width="500%" height="500%">
        <feGaussianBlur stdDeviation="1.6" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <clipPath id="bay"><rect x="600" y="470" width="570" height="28"/></clipPath>
    </defs>"""
    divider = (f'<line x1="566" y1="40" x2="566" y2="{H - 40}" stroke="{p["faint"]}"/>')
    body = (panel(W, H, p) + defs + divider
            + f'<g transform="translate(0,16)">{_identity(p, season)}</g>' + _river(p))
    desc = ("Tahmid Jawad Shafi, data engineering and analytics. An animated river delta "
            "shows his data sources (DGHS portal, Open-Meteo, FCTB 2013, BBS HIES 2022, "
            "simulators) merging through extract, validate and transform stages into "
            "published outputs.")
    return document(W, H, "Tahmid Jawad Shafi — data engineering", css, body, desc)

