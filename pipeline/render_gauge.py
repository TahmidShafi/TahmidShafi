"""Weekly contributions drawn as a river-level hydrograph.

Bangladesh's Flood Forecasting and Warning Centre reports river levels against
a danger level. Here the 'danger level' is the 90th-percentile week of the
window, so weeks above it mark unusually heavy activity. A staff gauge on the
left fills to the latest week's level.
"""
from __future__ import annotations

from datetime import date, timedelta

from .season import Season
from .svg import base_css, document, esc, palette, panel

W, H = 1200, 300
X0, X1, Y0, Y1 = 150, 1150, 92, 236   # plot box: left, right, top, bottom


def weekly_totals(days: list[dict], run_date: date, weeks: int = 52) -> list[tuple[date, int]]:
    """Sum daily counts into ``weeks`` 7-day bins ending on ``run_date``.

    Returns (bin start date, total) oldest first. Days outside the window are
    ignored; missing days count as zero (validation rejects gaps beforehand).
    """
    by_day = {d["date"]: d["count"] for d in days}
    start = run_date - timedelta(days=weeks * 7 - 1)
    out = []
    for w in range(weeks):
        first = start + timedelta(days=w * 7)
        total = sum(by_day.get((first + timedelta(days=k)).isoformat(), 0) for k in range(7))
        out.append((first, total))
    return out


def percentile(values: list[int], q: float) -> float:
    """Linear-interpolated percentile (same method as numpy's default)."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _smooth(points: list[tuple[float, float]]) -> str:
    """Catmull-Rom spline through ``points`` as cubic Bezier segments."""
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(len(points) - 1):
        p0 = points[max(i - 1, 0)]
        p1, p2 = points[i], points[i + 1]
        p3 = points[min(i + 2, len(points) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        # Clamp control points inside the plot so the curve never dips below zero.
        c1 = (c1[0], min(c1[1], Y1))
        c2 = (c2[0], min(c2[1], Y1))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def render(days: list[dict], run_date: date, season: Season, theme: str,
           fixture: bool) -> str:
    p = palette(season, theme)
    weeks = weekly_totals(days, run_date)
    values = [v for _, v in weeks]
    danger = percentile(values, 0.9)
    top = max(max(values), danger, 1) * 1.15

    def sx(i: int) -> float:
        return X0 + (X1 - X0) * i / (len(weeks) - 1)

    def sy(v: float) -> float:
        return Y1 - (Y1 - Y0) * v / top

    pts = [(sx(i), sy(v)) for i, v in enumerate(values)]
    line = _smooth(pts)
    area = f"{line} L{X1},{Y1} L{X0},{Y1} Z"
    dy = sy(danger)

    months, last_month = [], None
    for i, (start, _) in enumerate(weeks):
        if start.month != last_month:
            last_month = start.month
            if i > 0:
                months.append(f'<text x="{sx(i):.1f}" y="{Y1 + 18}" text-anchor="middle" '
                              f'class="mono muted" font-size="11.5">{start.strftime("%b")}</text>')

    peaks = "".join(
        f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="3.2" fill="{p["accent2"]}" class="rise" '
        f'style="animation-delay:{1.6 + i * 0.01:.2f}s"/>'
        for i, v in enumerate(values) if v > danger)

    # Staff gauge: alternating ticks, water rises to the latest week's level.
    gx, gw = 70, 16
    ticks = "".join(
        f'<rect x="{gx}" y="{Y0 + k * 12}" width="{gw if k % 2 else gw / 2}" height="6" '
        f'fill="{p["muted"]}" fill-opacity=".55"/>'
        for k in range(int((Y1 - Y0) / 12) + 1))
    now = values[-1]
    level_y = sy(now)
    gauge = f"""
    <rect x="{gx - 4}" y="{Y0 - 4}" width="{gw + 8}" height="{Y1 - Y0 + 8}" rx="3" fill="none" stroke="{p['border']}"/>
    {ticks}
    <rect x="{gx - 2}" y="{level_y:.1f}" width="{gw + 4}" height="{Y1 - level_y + 2:.1f}" fill="{p['accent']}"
      fill-opacity=".45">
      <animate attributeName="y" from="{Y1}" to="{level_y:.1f}" dur="2.2s" fill="freeze"
        calcMode="spline" keySplines=".2 .7 .2 1" keyTimes="0;1"/>
      <animate attributeName="height" from="0" to="{Y1 - level_y + 2:.1f}" dur="2.2s" fill="freeze"
        calcMode="spline" keySplines=".2 .7 .2 1" keyTimes="0;1"/>
    </rect>
    <text x="{gx + gw / 2}" y="{Y1 + 18}" text-anchor="middle" class="mono muted" font-size="11.5">now</text>
    <text x="{gx + gw + 12}" y="{level_y + 4:.1f}" class="mono fg" font-size="12.5" font-weight="600">{now}</text>
    """

    badge = ""
    if fixture:
        badge = (f'<rect x="{W - 340}" y="22" width="314" height="24" rx="12" fill="none" '
                 f'stroke="{p["warn"]}"/><text x="{W - 183}" y="38" text-anchor="middle" '
                 f'class="mono" font-size="12" fill="{p["warn"]}">FIXTURE · synthetic preview data</text>')

    source = ("synthetic fixture, replaced on the first live run" if fixture
              else "GitHub GraphQL contributionCalendar (public contributions)")
    css = base_css(p) + """
    .ripple { animation: ripple 3.5s ease-in-out infinite alternate; }
    @keyframes ripple { to { transform: translateY(-2px); } }
    """
    body = f"""
    {panel(W, H, p)}
    <defs>
      <linearGradient id="water" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{p['accent']}" stop-opacity=".42"/>
        <stop offset="1" stop-color="{p['accent']}" stop-opacity="0"/>
      </linearGradient>
      <clipPath id="reveal"><rect x="{X0 - 4}" y="0" width="{X1 - X0 + 8}" height="{H}">
        <animate attributeName="width" from="0" to="{X1 - X0 + 8}" dur="2.4s" fill="freeze"
          calcMode="spline" keySplines=".3 .6 .2 1" keyTimes="0;1"/></rect></clipPath>
    </defs>
    <text x="40" y="40" class="mono accent" font-size="12" letter-spacing="2.4" font-weight="600">SIGNAL</text>
    <text x="40" y="64" class="sans fg" font-size="17" font-weight="600">Weekly contributions, read like a river-level gauge</text>
    {badge}
    <line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="{p['border']}"/>
    {''.join(months)}
    <g clip-path="url(#reveal)">
      <path d="{area}" fill="url(#water)" class="ripple"/>
      <path d="{line}" fill="none" stroke="{p['accent']}" stroke-width="2" stroke-linejoin="round"/>
    </g>
    <line x1="{X0}" y1="{dy:.1f}" x2="{X1}" y2="{dy:.1f}" stroke="{p['accent2']}" stroke-dasharray="6 5"
      stroke-width="1.3"/>
    <line x1="{X1 - 326}" y1="{Y0 - 26}" x2="{X1 - 298}" y2="{Y0 - 26}" stroke="{p['accent2']}" stroke-dasharray="6 5" stroke-width="1.3"/>
    <text x="{X1}" y="{Y0 - 22}" text-anchor="end" class="mono muted" font-size="12">danger level = 90th-percentile week ({danger:.0f})</text>
    {peaks}
    {gauge}
    <text x="40" y="{H - 20}" class="mono muted" font-size="11.5">source: {esc(source)} · 7-day bins ending {run_date.isoformat()}</text>
    """
    desc = (f"Weekly contribution totals for the 52 weeks ending {run_date.isoformat()}, drawn "
            f"as a hydrograph. Latest week: {now}. 90th-percentile week: {danger:.0f}."
            + (" Preview uses synthetic fixture data." if fixture else ""))
    return document(W, H, "Weekly contributions hydrograph", css, body, desc)
