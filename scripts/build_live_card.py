"""Builds assets/live.svg from real GitHub data. Standard library only.

Run in GitHub Actions (see .github/workflows/update-profile.yml).
Run `python scripts/build_live_card.py demo` to render a preview with sample data.
"""
import calendar
import datetime as dt
import json
import math
import os
import random
import sys
import urllib.request
from collections import Counter
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "YugamdeepGoyal")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "live.svg")

MONO = "SF Mono, Menlo, Consolas, monospace"
SANS = "Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
LEVELS = ["#1b2048", "#3a3a9e", "#6b4fe0", "#9b7bff", "#d2c4ff"]

QUERY = (
    "query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{"
    "totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"
)


def call(url, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-live-card"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def get_repos():
    repos, page = [], 1
    while True:
        url = f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}"
        batch = call(url)
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    return [r for r in repos if not r.get("fork") and not r.get("private")]


def get_calendar():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    data = call("https://api.github.com/graphql", body)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [(d["date"], d["contributionCount"], d["weekday"]) for d in w["contributionDays"]]
        for w in cal["weeks"]
    ]
    return cal["totalContributions"], weeks


def demo_data():
    random.seed(5)
    today = dt.date.today()
    start = today - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    weeks, day = [], start
    while day <= today:
        week = []
        for _ in range(7):
            if day > today:
                break
            busy = random.random() < 0.38
            count = random.choice([1, 1, 2, 3, 4, 6, 9]) if busy else 0
            week.append((day.isoformat(), count, (day.weekday() + 1) % 7))
            day += dt.timedelta(days=1)
        weeks.append(week)
    total = sum(c for w in weeks for _, c, _ in w)
    now = dt.datetime.now(dt.timezone.utc)

    def iso(days):
        return (now - dt.timedelta(days=days)).isoformat()

    repos = [
        {"name": "predictive_maintenance", "pushed_at": iso(3), "topics": ["machine-learning", "lstm", "xgboost", "deeplearning", "prediction", "neural-network"], "language": "Jupyter Notebook"},
        {"name": "ecg_data", "pushed_at": iso(8), "topics": ["machine-learning", "lstm", "tensorflow", "keras", "neural-network", "research"], "language": "Jupyter Notebook"},
        {"name": "image_processing_elc", "pushed_at": iso(9), "topics": [], "language": "Jupyter Notebook"},
        {"name": "elc_house_price_prediction", "pushed_at": iso(54), "topics": [], "language": "Jupyter Notebook"},
        {"name": "exp_learning_telco_churn", "pushed_at": iso(80), "topics": ["python", "data-science", "machine-learning", "deep-learning", "random-forest", "scikit-learn"], "language": "Jupyter Notebook"},
        {"name": "mnist_dataset_model", "pushed_at": iso(101), "topics": ["python", "machine-learning", "deep-learning", "neural-network", "tensorflow", "keras", "mnist"], "language": "Jupyter Notebook"},
    ]
    return total, weeks, repos


def streaks(weeks):
    days = [c for w in weeks for _, c, _ in w]
    best = run = 0
    for c in days:
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    rev = days[::-1]
    if rev and rev[0] == 0:
        rev = rev[1:]
    cur = 0
    for c in rev:
        if c > 0:
            cur += 1
        else:
            break
    return best, cur


def ago(iso):
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = int((dt.datetime.now(dt.timezone.utc) - t).total_seconds() // 86400)
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        n = days // 30
        return f"{n} month ago" if n == 1 else f"{n} months ago"
    n = days // 365
    return f"{n} year ago" if n == 1 else f"{n} years ago"


def level(count, top):
    if count <= 0:
        return 0
    return min(4, max(1, math.ceil(4 * count / top)))


def tile(x, y, number, label, delay):
    return (
        f'<g class="rise" style="animation-delay:{delay}s">'
        f'<rect x="{x}" y="{y}" width="250" height="84" rx="14" fill="#151a3a" stroke="#262d63" stroke-width="1.5"/>'
        f'<text x="{x + 22}" y="{y + 44}" font-family="{SANS}" font-size="38" font-weight="800" fill="#f4f6ff">{escape(str(number))}</text>'
        f'<text x="{x + 22}" y="{y + 68}" font-family="{MONO}" font-size="13" fill="#8f9acb">{escape(label)}</text>'
        f'</g>'
    )


def build(total, weeks, repos, demo=False):
    nonzero = sorted(c for w in weeks for _, c, _ in w if c > 0)
    top = nonzero[max(0, int(len(nonzero) * 0.9) - 1)] if nonzero else 1
    top = max(top, 1)
    active = len(nonzero)
    best, cur = streaks(weeks)

    X0, Y0, PITCH, CELL = 70, 214, 20, 16
    cells, months = [], []
    for ci, week in enumerate(weeks):
        for date, _, _ in week:
            if date[8:10] == "01":
                months.append(
                    f'<text x="{X0 + ci * PITCH}" y="{Y0 - 12}" font-family="{MONO}" font-size="12" fill="#7782bd">{calendar.month_abbr[int(date[5:7])]}</text>'
                )
        for date, count, wd in week:
            cells.append(
                f'<rect class="cell" style="animation-delay:{ci * 0.022:.2f}s" x="{X0 + ci * PITCH}" y="{Y0 + wd * PITCH}" '
                f'width="{CELL}" height="{CELL}" rx="4" fill="{LEVELS[level(count, top)]}"/>'
            )

    recent = [r for r in repos if r["name"].lower() not in (USER.lower(), USER.lower() + ".github.io")]
    recent.sort(key=lambda r: r["pushed_at"], reverse=True)
    rows = []
    for i, r in enumerate(recent[:4]):
        y = 442 + i * 30
        rows.append(
            f'<g class="rise" style="animation-delay:{1.2 + i * 0.12:.2f}s">'
            f'<circle cx="96" cy="{y - 5}" r="4" fill="{["#8b6cff", "#2dd4bf", "#8b6cff", "#2dd4bf"][i]}"/>'
            f'<text x="114" y="{y}" font-family="{SANS}" font-size="16" font-weight="700" fill="#e6e9ff">{escape(r["name"])}</text>'
            f'<text x="662" y="{y}" text-anchor="end" font-family="{MONO}" font-size="13" fill="#8f9acb">{ago(r["pushed_at"])}</text>'
            f'</g>'
        )

    topics = Counter(t for r in repos for t in r.get("topics", []))
    ranked = sorted(topics.items(), key=lambda kv: (-kv[1], kv[0]))[:12]
    chips, cx, cy = [], 734, 448
    for name, _ in ranked:
        w = len(name) * 8 + 26
        if cx + w > 1106:
            cx, cy = 734, cy + 36
        if cy > 524:
            break
        chips.append(
            f'<g class="rise" style="animation-delay:{1.4 + len(chips) * 0.05:.2f}s">'
            f'<rect x="{cx}" y="{cy - 19}" width="{w}" height="28" rx="14" fill="#1d2350" stroke="#2f3880" stroke-width="1"/>'
            f'<text x="{cx + w / 2}" y="{cy}" text-anchor="middle" font-family="{MONO}" font-size="13" fill="#dfe4ff">{escape(name)}</text>'
            f'</g>'
        )
        cx += w + 10

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    note = "preview data, replaced on the first workflow run" if demo else f"rebuilt automatically, last run {stamp} UTC"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 580" width="1200" height="580" role="img" aria-label="Live GitHub activity for {escape(USER)}: contributions in the last year, active days, longest streak, public repositories, a contribution heatmap, recently pushed repositories and common topics.">
<style>
@keyframes pop {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.cell {{ opacity: 0; animation: pop 0.4s ease forwards; }}
.rise {{ opacity: 0; animation: rise 0.6s ease forwards; }}
</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0c0f26"/><stop offset="1" stop-color="#181b47"/></linearGradient>
</defs>
<rect width="1200" height="580" rx="18" fill="url(#bg)"/>
<text x="70" y="54" font-family="{SANS}" font-size="24" font-weight="800" fill="#f4f6ff">Live from GitHub</text>
<text x="1130" y="53" text-anchor="end" font-family="{MONO}" font-size="13" fill="#7782bd">{escape(note)}</text>
{tile(70, 78, total, "contributions, last year", 0.1)}
{tile(340, 78, active, "active days", 0.2)}
{tile(610, 78, f"{best} days", "longest streak", 0.3)}
{tile(880, 78, len(repos), "public repositories", 0.4)}
{"".join(months)}
{"".join(cells)}
<rect x="70" y="378" width="620" height="170" rx="16" fill="#11152e" stroke="#232a5c" stroke-width="1.5"/>
<text x="96" y="410" font-family="{MONO}" font-size="13" fill="#8f9acb">recently pushed</text>
{"".join(rows)}
<rect x="710" y="378" width="420" height="170" rx="16" fill="#11152e" stroke="#232a5c" stroke-width="1.5"/>
<text x="734" y="410" font-family="{MONO}" font-size="13" fill="#8f9acb">what my repos are tagged with</text>
{"".join(chips)}
</svg>
'''


def main():
    demo = len(sys.argv) > 1 and sys.argv[1] == "demo"
    if demo:
        total, weeks, repos = demo_data()
    else:
        repos = get_repos()
        total, weeks = get_calendar()
    svg = build(total, weeks, repos, demo)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT, len(svg), "bytes")


if __name__ == "__main__":
    main()
