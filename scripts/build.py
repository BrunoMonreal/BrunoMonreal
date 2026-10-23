#!/usr/bin/env python3
"""Genera el README de perfil de BrunoMonreal: láminas SVG (ES/CA/EN) + estadísticas
anónimas de commits (sin nombres de repos, mensajes ni clientes).

Dirección de arte: «Eixample». El chaflán a 45° de las manzanas de Cerdà es el único
tratamiento de esquina; campos de color planos con bordes duros; tu día real de commits
es la imagen principal. Una sola familia (Archivo, variable en peso y anchura).

Uso:
    GH_TOKEN=<token con acceso a los repos> python scripts/build.py
Sin GH_TOKEN reutiliza data/stats.json y solo vuelve a pintar los SVGs.
"""
import base64
import datetime as dt
import io
import json
import math
import os
import string
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONT = ROOT / "scripts" / "fonts" / "archivo.woff2"
DATA = ROOT / "data" / "stats.json"
REPO_URL = "https://github.com/BrunoMonreal/BrunoMonreal/blob/main"
TZ = ZoneInfo("Europe/Madrid")
WINDOW_DAYS = 90

# ─── Paleta corporativa: campos planos, un solo acento ───────────────────────
WHITE, INK, MUTED = "#FFFFFF", "#171C8F", "#475569"
BLUE, NOVA, TINT, PALE = "#0072CE", "#4AA7B7", "#E7F3F5", "#C9DFF2"
ON_INK, ON_INK_SOFT = "#D9DBF2", "#A9AEDB"  # texto secundario sobre el campo índigo
EASE = "cubic-bezier(.16,1,.3,1)"
M = 40  # margen de lámina
CUT = 28  # chaflán

# ─── Textos ──────────────────────────────────────────────────────────────────
TXT = {
    "es": dict(
        name="Español",
        lead="Partner en Infini · AI & Data Manager en Forvis Mazars.",
        sub="Construyo agentes y pipelines de IA que leen documentos, razonan y llegan a producción.",
        hist="Mis commits por hora del día, últimos {n} días",
        about_title="Enseño a los LLMs a hacer trabajo de verdad.",
        about=(
            "Diseño agentes que leen documentos, razonan sobre ellos y usan herramientas, y los llevo "
            "hasta producción: APIs, modelos servidos en GPU, evaluaciones y todo lo que hay entre medias. "
            "Me gusta que la IA sea útil, medible y aburrida de mantener."
        ),
        facts_title="Datos curiosos",
        facts=[
            "Funciono con café y git push.",
            "Mi modelo favorito es el que pasa las evals.",
            "Convierto PDFs en JSON por deporte.",
            "Frase típica: «en local funciona».",
        ],
        stats_title="Mis commits, en números",
        sentence=("{commits} commits en {days} días, repartidos en {active} días de trabajo y {repos} repos. "
                  "Mi racha más larga: {streak} días seguidos."),
        night="El {pct} % de mis commits llega después de las 20:00. Búho nocturno confirmado.",
        day="Mi hora pico son las {h}:00. Persona de día, lo dice el histograma.",
        days_title="Por día de la semana",
        days=["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
        updated="Se actualiza solo cada día. Último dato: {d}.",
        months=["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
        stack_title="Con lo que trabajo",
        groups={"models": "Modelos", "orch": "Orquestación", "data": "Datos", "ship": "Producción"},
        footer="Hecho con Python, demasiado café y una GitHub Action.",
        alt_hero="Bruno Monreal, Partner en Infini y AI & Data Manager en Forvis Mazars, Barcelona. Histograma de mis commits por hora del día.",
        alt_marquee="Tecnologías: Python, LangGraph, FastAPI, vLLM, RAG, PostgreSQL, Docker…",
        alt_about="Sobre mí y datos curiosos",
        alt_stats="Estadísticas anónimas de mis commits de los últimos 90 días",
        alt_stack="Con lo que trabajo: modelos, orquestación, datos y producción",
        alt_footer="Hecho con Python, demasiado café y una GitHub Action",
    ),
    "ca": dict(
        name="Català",
        lead="Partner a Infini · AI & Data Manager a Forvis Mazars.",
        sub="Construeixo agents i pipelines d'IA que llegeixen documents, raonen i arriben a producció.",
        hist="Els meus commits per hora del dia, últims {n} dies",
        about_title="Ensenyo als LLMs a fer feina de veritat.",
        about=(
            "Dissenyo agents que llegeixen documents, en raonen i fan servir eines, i els porto fins a "
            "producció: APIs, models servits en GPU, avaluacions i tot el que hi ha entremig. "
            "M'agrada que la IA sigui útil, mesurable i avorrida de mantenir."
        ),
        facts_title="Curiositats",
        facts=[
            "Funciono amb cafè i git push.",
            "El meu model preferit és el que passa les evals.",
            "Converteixo PDFs en JSON per esport.",
            "Frase típica: «en local funciona».",
        ],
        stats_title="Els meus commits, en números",
        sentence=("{commits} commits en {days} dies, repartits en {active} dies de feina i {repos} repos. "
                  "La meva ratxa més llarga: {streak} dies seguits."),
        night="El {pct} % dels meus commits arriba després de les 20:00. Mussol nocturn confirmat.",
        day="La meva hora punta són les {h}:00. Persona de dia, ho diu l'histograma.",
        days_title="Per dia de la setmana",
        days=["dl", "dt", "dc", "dj", "dv", "ds", "dg"],
        updated="S'actualitza sol cada dia. Última dada: {d}.",
        months=["gen", "febr", "març", "abr", "maig", "juny", "jul", "ag", "set", "oct", "nov", "des"],
        stack_title="Amb què treballo",
        groups={"models": "Models", "orch": "Orquestració", "data": "Dades", "ship": "Producció"},
        footer="Fet amb Python, massa cafè i una GitHub Action.",
        alt_hero="Bruno Monreal, Partner a Infini i AI & Data Manager a Forvis Mazars, Barcelona. Histograma dels meus commits per hora del dia.",
        alt_marquee="Tecnologies: Python, LangGraph, FastAPI, vLLM, RAG, PostgreSQL, Docker…",
        alt_about="Sobre mi i curiositats",
        alt_stats="Estadístiques anònimes dels meus commits dels últims 90 dies",
        alt_stack="Amb què treballo: models, orquestració, dades i producció",
        alt_footer="Fet amb Python, massa cafè i una GitHub Action",
    ),
    "en": dict(
        name="English",
        lead="Partner at Infini · AI & Data Manager at Forvis Mazars.",
        sub="I build AI agents and pipelines that read documents, reason, and make it to production.",
        hist="My commits by hour of day, last {n} days",
        about_title="I teach LLMs to do real work.",
        about=(
            "I design agents that read documents, reason about them and use tools, and I take them all "
            "the way to production: APIs, GPU-served models, evals and everything in between. "
            "I like my AI useful, measurable and boring to maintain."
        ),
        facts_title="Fun facts",
        facts=[
            "I run on coffee and git push.",
            "My favourite model is whichever passes the evals.",
            "I turn PDFs into JSON for sport.",
            "Catchphrase: “works on my machine”.",
        ],
        stats_title="My commits, by the numbers",
        sentence=("{commits} commits in {days} days, spread over {active} working days and {repos} repos. "
                  "Longest streak: {streak} days in a row."),
        night="{pct}% of my commits land after 8 pm. Certified night owl.",
        day="My peak hour is {h}:00. A day person, says the histogram.",
        days_title="By day of the week",
        days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        updated="Updates itself every day. Last data point: {d}.",
        months=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        stack_title="What I work with",
        groups={"models": "Models", "orch": "Orchestration", "data": "Data", "ship": "Shipping"},
        footer="Made with Python, too much coffee and a GitHub Action.",
        alt_hero="Bruno Monreal, Partner at Infini and AI & Data Manager at Forvis Mazars, Barcelona. Histogram of my commits by hour of day.",
        alt_marquee="Tech: Python, LangGraph, FastAPI, vLLM, RAG, PostgreSQL, Docker…",
        alt_about="About me and fun facts",
        alt_stats="Anonymous stats about my commits over the last 90 days",
        alt_stack="What I work with: models, orchestration, data and shipping",
        alt_footer="Made with Python, too much coffee and a GitHub Action",
    ),
}

MARQUEE = [
    "Python", "LangGraph", "FastAPI", "vLLM", "Transformers", "PyTorch", "RAG", "FAISS", "pgvector",
    "MCP", "OCR", "Pydantic", "SQLAlchemy", "PostgreSQL", "SQL Server", "Docker", "OpenTelemetry", "Langfuse",
]

STACK = [
    ("models", ["vLLM", "Transformers", "PyTorch", "Embeddings", "Evals", "Prompting"]),
    ("orch", ["LangGraph", "MCP", "RAG", "FastAPI", "Pydantic", "Python"]),
    ("data", ["PostgreSQL", "pgvector", "SQL Server", "SQLAlchemy", "FAISS", "ETL", "OCR"]),
    ("ship", ["Docker", "GPU serving", "GitHub Actions", "OpenTelemetry", "Langfuse"]),
]

FOOTER_SIGN = "Bruno Monreal, Barcelona."


# ─── Fuente: Archivo variable, recortada a los caracteres usados ─────────────
def _chars(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return "".join(_chars(x) for x in v.values())
    return "".join(_chars(x) for x in v)


def _font_css():
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt", "tnum"]
    font = TTFont(FONT)
    sub = subset.Subsetter(opts)
    sub.populate(text=_chars([TXT, MARQUEE, STACK, FOOTER_SIGN]) + string.printable + "%·")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return ("@font-face{font-family:'A';src:url(data:font/woff2;base64,%s) format('woff2');"
            "font-weight:100 900;font-stretch:62%% 125%%}" % data)


FONT_CSS = _font_css()
BASE_CSS = (
    "text{font-family:'A',Archivo,'Helvetica Neue',Arial,sans-serif;font-kerning:normal}"
    ".n{font-variant-numeric:tabular-nums}"
    f".gy{{transform-box:fill-box;transform-origin:50% 100%;animation:gy .9s {EASE} backwards}}"
    "@keyframes gy{from{transform:scaleY(0)}}"
    f".gx{{transform-box:fill-box;transform-origin:0 50%;animation:gx .6s {EASE} backwards}}"
    "@keyframes gx{from{transform:scaleX(0)}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)

_metrics = {}


def width(s, size, wght=400, wdth=100, track=0.0):
    key = (wght, wdth)
    if key not in _metrics:
        f = instantiateVariableFont(TTFont(FONT), {"wght": wght, "wdth": wdth})
        _metrics[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[key]
    units = sum(hmtx[cmap.get(ord(c), cmap[32])][0] for c in s)
    return units * size / upm + len(s) * track * size


def wrap(s, size, maxw, wght=400):
    lines, cur = [], ""
    for word in s.split():
        test = f"{cur} {word}".strip()
        if cur and width(test, size, wght) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = test
    return lines + [cur] if cur else lines


def esc(s):
    return escape(str(s), {'"': "&quot;"})


def text(x, y, s, size, fill=INK, wght=400, wdth=100, anchor="start", track=0.0, cls="", extra=""):
    style = f' style="font-stretch:{wdth}%"' if wdth != 100 else ""
    ls = f' letter-spacing="{track * size:.2f}"' if track else ""
    c = f' class="{cls}"' if cls else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{wght}" fill="{fill}" '
            f'text-anchor="{anchor}"{style}{ls}{c}{extra}>{s if s.startswith("<tspan") else esc(s)}</text>')


def chamfer(w, h, c=CUT, x=0, y=0):
    """Lámina con chaflán arriba a la izquierda y abajo a la derecha."""
    return f"M{x + c} {y}H{x + w}V{y + h - c}L{x + w - c} {y + h}H{x}V{y + c}Z"


def octagon(x, y, w, h, c):
    return (f"M{x + c:.1f} {y:.1f}H{x + w - c:.1f}L{x + w:.1f} {y + c:.1f}V{y + h - c:.1f}"
            f"L{x + w - c:.1f} {y + h:.1f}H{x + c:.1f}L{x:.1f} {y + h - c:.1f}V{y + c:.1f}Z")


def svg(w, h, body, title, fill=WHITE, css="", defs="", cut=CUT):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h:.0f}" viewBox="0 0 {w} {h:.0f}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
            f'<defs><style>{FONT_CSS}{BASE_CSS}{css}</style>'
            f'<clipPath id="p"><path d="{chamfer(w, h, cut)}"/></clipPath>{defs}</defs>'
            f'<g clip-path="url(#p)"><path d="{chamfer(w, h, cut)}" fill="{fill}"/>{body}</g></svg>')


def delay(s):
    return f' style="animation-delay:{s:.3f}s"'


def head(y, s, fill=INK, maxw=760):
    out = []
    for ln in wrap(s, 44, maxw, 700):
        out.append(text(M, y, ln, 44, fill, 700, track=-0.02))
        y += 50
    return "".join(out), y - 50


def fmt_num(n, lang):
    return f"{n:,}".replace(",", "," if lang == "en" else ".")


def fmt_date(d, lang):
    m = TXT[lang]["months"][d.month - 1]
    return f"{m} {d.day}, {d.year}" if lang == "en" else f"{d.day} {m} {d.year}"


# ─── Láminas ─────────────────────────────────────────────────────────────────
def hero(lang, s):
    L = TXT[lang]
    W = 1000
    b = [text(M - 6, 150, "Bruno", 140, INK, 700, 125, track=-0.03),
         text(M - 6, 279, f'<tspan>Monreal</tspan><tspan fill="{BLUE}">.</tspan>', 140, INK, 700, 125, track=-0.03),
         text(M, 346, L["lead"], 26, INK, 600)]
    y = 384
    for ln in wrap(L["sub"], 20, 640):
        b.append(text(M, y, ln, 20, MUTED))
        y += 30

    # El día de Bruno: histograma real de commits por hora
    hours = s["hours"]
    peak = max(range(24), key=lambda h: hours[h])
    top_v = max(hours) or 1
    cap_y = y + 40
    bars_top = cap_y + 30
    base = bars_top + 130
    slot = (W - 2 * M) / 24
    bw = slot - 10
    cap = text(M, cap_y, L["hist"].format(n=s["window_days"]), 16, MUTED) if peak >= 12 else \
        text(W - M, cap_y, L["hist"].format(n=s["window_days"]), 16, MUTED, anchor="end")
    b.append(cap)
    for h, v in enumerate(hours):
        bh = max(4, 130 * v / top_v)
        x = M + h * slot + 5
        c = min(9, bh / 2)
        b.append(f'<path class="gy" d="M{x:.1f} {base}V{base - bh + c:.1f}L{x + c:.1f} {base - bh:.1f}H{x + bw - c:.1f}'
                 f'L{x + bw:.1f} {base - bh + c:.1f}V{base}Z" fill="{BLUE if h == peak else PALE}"{delay(.15 + h * .025)}/>')
    px = M + peak * slot + slot / 2
    b.append(text(px, base - 130 * hours[peak] / top_v - 12, f"{peak:02d}:00", 16, INK, 700, anchor="middle", cls="n"))
    for h in (0, 6, 12, 18):
        b.append(text(M + h * slot + slot / 2, base + 28, f"{h:02d}", 16, MUTED, anchor="middle", cls="n"))
    return svg(W, base + 64, "".join(b), L["alt_hero"])


def marquee():
    W, H = 1000, 112
    parts, x = [], 0.0
    for t in MARQUEE:
        parts.append(text(x, 76, t, 56, INK, 500, track=-0.02))
        x += width(t, 56, 500, track=-0.02) + 30
        parts.append(f'<path d="{octagon(x, 49, 14, 14, 4)}" fill="{BLUE}"/>')
        x += 14 + 30
    row = "".join(parts)
    copies = math.ceil(W / x) + 1
    track = "".join(f'<g transform="translate({x * k:.1f} 0)">{row}</g>' for k in range(copies))
    css = ".track{animation:slide %.1fs linear infinite}@keyframes slide{to{transform:translateX(-%.1fpx)}}" % (x / 45, x)
    return svg(W, H, f'<g class="track">{track}</g>', TXT["en"]["alt_marquee"], TINT, css)


def about(lang):
    L = TXT[lang]
    W = 1000
    h, y = head(100, L["about_title"])
    b = [h]
    top = y + 64
    ly = top
    for ln in wrap(L["about"], 24, 560):
        b.append(text(M, ly, ln, 24, INK))
        ly += 36
    rx = 680
    b.append(text(rx, top, L["facts_title"], 20, INK, 700))
    ry = top + 36
    for f in L["facts"]:
        for ln in wrap(f, 20, W - M - rx):
            b.append(text(rx, ry, ln, 20, MUTED))
            ry += 28
        ry += 14
    return svg(W, max(ly, ry) + 30, "".join(b), L["alt_about"])


def rich_lines(template, values, size, maxw):
    lines, cur = [[]], 0.0
    sp = width(" ", size)
    for w in template.split():
        bold = "{" in w
        word = w.format(**values)
        ww = width(word, size, 700 if bold else 400)
        if lines[-1] and cur + sp + ww > maxw:
            lines.append([])
            cur = 0.0
        cur += (sp if lines[-1] else 0) + ww
        lines[-1].append((word, bold))
    return lines


def stats_band(lang, s):
    L = TXT[lang]
    W = 1000
    hours = s["hours"]
    total = sum(hours) or 1
    night = sum(hours[h] for h in list(range(20, 24)) + list(range(0, 6)))
    pct = round(100 * night / total)
    peak = max(range(24), key=lambda h: hours[h])
    finding = L["night"].format(pct=pct) if pct >= 25 else L["day"].format(h=f"{peak:02d}")

    h, y = head(100, L["stats_title"], WHITE)
    b = [h]
    vals = {"commits": fmt_num(s["commits"], lang), "days": s["window_days"], "active": s["active_days"],
            "repos": s["repos"], "streak": s["best_streak"]}
    ly = y + 62
    for ln in rich_lines(L["sentence"], vals, 26, 520):
        spans = "".join(
            f'<tspan fill="{WHITE if bold else ON_INK}" font-weight="{700 if bold else 400}"{" class=\"n\"" if bold else ""}>'
            f'{esc(word)}{" " if i < len(ln) - 1 else ""}</tspan>'
            for i, (word, bold) in enumerate(ln))
        b.append(text(M, ly, spans, 26, WHITE))
        ly += 38
    ly += 26
    b.append(f'<path d="{octagon(M, ly - 15, 14, 14, 4)}" fill="{NOVA}"/>')
    for ln in wrap(finding, 22, 480, 500):
        b.append(text(M + 28, ly, ln, 22, WHITE, 500))
        ly += 32

    # Barras por día de la semana
    days = s["weekdays"]
    best = max(range(7), key=lambda d: days[d])
    md = max(days) or 1
    rx = 620
    b.append(text(rx, y + 62, L["days_title"], 20, WHITE, 600))
    ry = y + 92
    for d, v in enumerate(days):
        bw = max(4, 250 * v / md)
        c = min(6, bw / 2)
        b.append(text(rx, ry + 15, L["days"][d], 16, ON_INK_SOFT)
                 + f'<path class="gx" d="M{rx + 50} {ry}H{rx + 50 + bw - c:.1f}L{rx + 50 + bw:.1f} {ry + c}V{ry + 18}H{rx + 50}Z" '
                   f'fill="{WHITE if d == best else NOVA}"{delay(.2 + d * .06)}/>'
                 + text(rx + 60 + bw, ry + 15, fmt_num(v, lang), 16, ON_INK_SOFT, cls="n"))
        ry += 34

    bottom = max(ly, ry) + 36
    gen = dt.date.fromisoformat(s["generated_at"][:10])
    b.append(text(M, bottom, L["updated"].format(d=fmt_date(gen, lang)), 16, ON_INK_SOFT))
    return svg(W, bottom + 44, "".join(b), L["alt_stats"], INK)


def stack(lang):
    L = TXT[lang]
    W = 1000
    h, y = head(100, L["stack_title"])
    b = [h]
    top = y + 70
    col = (W - 2 * M) / 4
    bottom = top
    for i, (key, items) in enumerate(STACK):
        x = M + i * col
        b.append(f'<path d="{octagon(x, top - 14, 12, 12, 3)}" fill="{BLUE}"/>' + text(x + 22, top, L["groups"][key], 22, INK, 700))
        iy = top + 40
        for t in items:
            b.append(text(x, iy, t, 20, INK))
            iy += 32
        bottom = max(bottom, iy)
    return svg(W, bottom + 20, "".join(b), L["alt_stack"])


def footer(lang):
    L = TXT[lang]
    W, H = 1000, 260
    # Fragmento del Eixample: manzanas achaflanadas, girado como la trama real, y la Diagonal
    blk, street = 116, 26
    step = blk + street
    blocks = "".join(f'<path d="{octagon(x, y, blk, blk, 22)}"/>'
                     for x in range(-260, 1260, step) for y in range(-260, 520, step))
    b = [f'<g fill="#fff" fill-opacity=".12" transform="rotate(-9 500 130)">{blocks}</g>',
         '<path d="M-20 286 L1020 -6" stroke="#fff" stroke-opacity=".3" stroke-width="16"/>']
    y = 104
    for ln in wrap(L["footer"], 30, 640, 600):
        b.append(text(M, y, ln, 30, WHITE, 600, track=-0.01))
        y += 38
    b.append(text(M, y + 6, FOOTER_SIGN, 20, WHITE))
    return svg(W, H, "".join(b), L["alt_footer"], BLUE)


def lang_link(code, on):
    W, H = 136, 48
    name = TXT[code]["name"]
    tw = width(name, 20, 700 if on else 400)
    body = text(W / 2, 28, name, 20, INK if on else MUTED, 700 if on else 400, anchor="middle")
    if on:
        body += f'<rect x="{(W - tw) / 2:.1f}" y="35" width="{tw:.1f}" height="4" fill="{BLUE}"/>'
    return svg(W, H, body, name, cut=10)


# ─── Datos: estadísticas anónimas de commits ─────────────────────────────────
def gh(path, token):
    url = path if path.startswith("http") else "https://api.github.com" + path
    out = []
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "profile-readme"})
        with urllib.request.urlopen(req) as r:
            data, link = json.load(r), r.headers.get("Link", "")
        if not isinstance(data, list):
            return data
        out += data
        url = next((p.split(";")[0].strip()[1:-1] for p in link.split(",") if 'rel="next"' in p), None)
    return out


def collect(token):
    login = gh("/user", token)["login"]
    now = dt.datetime.now(dt.timezone.utc)
    since = (now - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repos = gh("/user/repos?per_page=100&affiliation=owner,collaborator,organization_member", token)
    seen, dates = set(), set()
    hours, weekdays, touched = [0] * 24, [0] * 7, 0
    for repo in repos:
        if not repo.get("pushed_at") or repo["pushed_at"] < since:
            continue
        try:
            commits = gh(f"/repos/{repo['full_name']}/commits?author={login}&since={since}&per_page=100", token)
        except urllib.error.HTTPError:  # repos vacíos o sin acceso
            continue
        new = [c for c in commits if c["sha"] not in seen]
        if not new:
            continue
        touched += 1
        for c in new:
            seen.add(c["sha"])
            t = dt.datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00")).astimezone(TZ)
            hours[t.hour] += 1
            weekdays[t.weekday()] += 1
            dates.add(t.date())
    best = run = 0
    prev = None
    for d in sorted(dates):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best, prev = max(best, run), d
    # Solo agregados: ningún nombre de repo, mensaje ni cliente sale de aquí.
    return {
        "generated_at": now.astimezone(TZ).isoformat(timespec="minutes"),
        "window_days": WINDOW_DAYS,
        "commits": len(seen),
        "active_days": len(dates),
        "best_streak": best,
        "repos": touched,
        "hours": hours,
        "weekdays": weekdays,
    }


# ─── README ──────────────────────────────────────────────────────────────────
FILES = {"es": "README.md", "ca": "README.ca.md", "en": "README.en.md"}


def readme(lang):
    L = TXT[lang]
    links = "\n  ".join(
        f'<a href="{REPO_URL}/{FILES[c]}"><img src="assets/lang-{c}-{"on" if c == lang else "off"}.svg" height="40" alt="{TXT[c]["name"]}" /></a>'
        for c in TXT)
    imgs = [("hero", L["alt_hero"]), ("marquee", L["alt_marquee"]), ("about", L["alt_about"]),
            ("stats", L["alt_stats"]), ("stack", L["alt_stack"]), ("footer", L["alt_footer"])]
    body = [f'<p align="right">\n  {links}\n</p>']
    for name, alt in imgs:
        src = "marquee.svg" if name == "marquee" else f"{name}-{lang}.svg"
        body.append(f'<img src="assets/{src}" width="100%" alt="{esc(alt)}" />')
    (ROOT / FILES[lang]).write_text("\n\n".join(body) + "\n", encoding="utf-8")


def main():
    token = os.environ.get("GH_TOKEN")
    if token:
        stats = collect(token)
        DATA.parent.mkdir(exist_ok=True)
        DATA.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    else:
        stats = json.loads(DATA.read_text(encoding="utf-8"))
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob("*.svg"):
        old.unlink()
    out = {"marquee.svg": marquee()}
    for lang in TXT:
        out[f"hero-{lang}.svg"] = hero(lang, stats)
        out[f"about-{lang}.svg"] = about(lang)
        out[f"stats-{lang}.svg"] = stats_band(lang, stats)
        out[f"stack-{lang}.svg"] = stack(lang)
        out[f"footer-{lang}.svg"] = footer(lang)
        for on in (True, False):
            out[f"lang-{lang}-{'on' if on else 'off'}.svg"] = lang_link(lang, on)
        readme(lang)
    for name, content in out.items():
        (ASSETS / name).write_text(content, encoding="utf-8")
    print(f"{len(out)} SVGs, {stats['commits']} commits, {stats['repos']} repos")


if __name__ == "__main__":
    main()
