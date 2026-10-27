#!/usr/bin/env python3
"""
Generador de la web 0xRioseco.

Laboratorio personal de Javier Rioseco: seguridad ofensiva (HTB/CTFs),
investigación de vulnerabilidades, data science y notas. Lee el contenido del
vault de Obsidian y produce un sitio estático en `_site/` para GitHub Pages.

El sitio se organiza en ÁREAS (ver COLLECTIONS). Cada área apunta a una o más
carpetas del vault:
  · Ofensiva  → `01 - Machines/`            (tarjetas de máquina + roadmap)
  · Research  → `07 - Research/`            (posts)
  · Data      → `08 - Data Science/`        (posts)
  · Notas     → `04 - Notes/`, `05 - Cheatsheets/` (posts)

Salida:
  _site/
    index.html                       hub: hero + áreas + últimas entradas
    <area>.html                      una página por área con sus tarjetas
    machines/<slug>.html             writeup de máquina
    posts/<slug>.html                post (research/data/notas)
    assets/…                         css, js, imágenes copiadas

Para añadir contenido basta con crear un `.md` con su frontmatter en la carpeta
del área y reconstruir: aparece solo.
"""

import html
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = ROOT / "site"
OUT = ROOT / "_site"

MD_EXTS = ["fenced_code", "tables", "sane_lists", "attr_list", "md_in_html"]

SITE_NAME = "0xRioseco"
SITE_DESC = ("Laboratorio personal de Javier Rioseco: seguridad ofensiva, "
             "investigación de vulnerabilidades y data science.")
GH_URL = "https://github.com/javierrr13/0xRioseco"

# --------------------------------------------------------------------------- #
#  Áreas del sitio
# --------------------------------------------------------------------------- #
COLLECTIONS = [
    dict(id="offensive", name="Ofensiva · HTB & CTFs", icon="🎯",
         accent="var(--green)", kind="machine", dirs=["01 - Machines"],
         blurb="Máquinas y retos resueltos paso a paso, de la enumeración al "
               "root — y las lecciones que deja cada uno."),
    dict(id="research", name="Investigación", icon="🔬",
         accent="var(--orange)", kind="post", dirs=["07 - Research"],
         blurb="Análisis de vulnerabilidades y tendencias en defensa: SOC, "
               "respuesta a incidentes e impacto de la IA."),
    dict(id="data", name="Data Science / ML", icon="📊",
         accent="var(--teal)", kind="post", dirs=["08 - Data Science"],
         blurb="Proyectos de datos, análisis exploratorio, visualización y "
               "modelos — incluido su cruce con la seguridad."),
    dict(id="notes", name="Notas & Cheatsheets", icon="📚",
         accent="var(--purple)", kind="post", dirs=["04 - Notes", "05 - Cheatsheets"],
         blurb="Teoría transversal y referencias rápidas de comandos y técnicas."),
]

CALLOUT_META = {
    "note": ("ℹ️", "c-note"), "info": ("ℹ️", "c-info"),
    "tip": ("💡", "c-tip"), "hint": ("💡", "c-tip"), "success": ("✅", "c-tip"),
    "warning": ("⚠️", "c-warning"), "caution": ("⚠️", "c-warning"),
    "danger": ("🔥", "c-danger"), "error": ("⛔", "c-danger"), "bug": ("🐞", "c-danger"),
    "abstract": ("📋", "c-abstract"), "summary": ("📋", "c-abstract"),
    "example": ("🧪", "c-info"), "quote": ("❝", "c-note"),
}

ROADMAP_PHASES = [
    ("recon",   "🔎", "Reconnaissance", "Escaneo de puertos, DNS y OSINT para mapear la superficie.", "var(--green)"),
    ("enum",    "🧩", "Enumeration",    "Enumeración por servicio: web, SMB, LDAP, shares…", "var(--green)"),
    ("web",     "🌐", "Web",            "HTTP, autenticación, JWT, IDOR, inyecciones.", "var(--teal)"),
    ("network", "🖧", "Network",        "Servicios de red, FTP/SMB, captura de tráfico.", "var(--teal)"),
    ("access",  "🚪", "Initial Access", "Explotación del vector de entrada → primera shell.", "var(--yellow)"),
    ("privesc", "📈", "Privilege Esc.", "SUID, sudo, capabilities, kernel, RBAC.", "var(--yellow)"),
    ("post",    "🔀", "Post Exploit.",  "Pivoting, movimiento lateral, abuso de permisos.", "var(--orange)"),
    ("root",    "👑", "Root / Admin",   "Control total del sistema y lectura de la flag.", "var(--orange)"),
    ("lessons", "📝", "Lessons Learned","Por qué funcionó, qué falló y qué repetir.", "var(--purple)"),
]


# --------------------------------------------------------------------------- #
#  Markdown → HTML
# --------------------------------------------------------------------------- #
def parse_frontmatter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return (yaml.safe_load(parts[1]) or {}), parts[2].lstrip("\n")
    return {}, text


def strip_first_h1(body):
    lines = body.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "":
            continue
        if ln.startswith("# "):
            del lines[i]
            if i < len(lines) and lines[i].strip() == "":
                del lines[i]
        break
    return "\n".join(lines)


def md_to_html(md_text):
    return markdown.markdown(md_text, extensions=MD_EXTS, output_format="html5")


def extract_blocks(body, tokens, charts):
    def mermaid_sub(m):
        tok = f"XBLOCKX{len(tokens)}XBLOCKX"
        tokens.append((tok, f'<pre class="mermaid">{html.escape(m.group(1))}</pre>'))
        return f"\n\n{tok}\n\n"

    body = re.sub(r"```mermaid\n(.*?)```", mermaid_sub, body, flags=re.DOTALL)

    # Bloques de gráfico: ```chart\n{ ...spec Chart.js + "title"/"caption"... }```
    def chart_sub(m):
        try:
            spec = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            tok = f"XBLOCKX{len(tokens)}XBLOCKX"
            tokens.append((tok, f'<pre class="callout c-danger">chart JSON inválido: {html.escape(str(e))}</pre>'))
            return f"\n\n{tok}\n\n"
        cid = f"chart{len(charts)}"
        caption = spec.pop("caption", "") or spec.pop("title", "")
        charts.append((cid, spec))
        tok = f"XBLOCKX{len(tokens)}XBLOCKX"
        fig = (f'<figure class="chart-card"><div class="chart-wrap">'
               f'<canvas id="{cid}"></canvas></div>'
               + (f'<figcaption>{html.escape(caption)}</figcaption>' if caption else "")
               + '</figure>')
        tokens.append((tok, fig))
        return f"\n\n{tok}\n\n"

    body = re.sub(r"```chart\n(.*?)```", chart_sub, body, flags=re.DOTALL)

    out, lines, i = [], body.splitlines(), 0
    while i < len(lines):
        m = re.match(r"^>\s*\[!(\w+)\]([+-]?)\s*(.*)$", lines[i])
        if m:
            ctype, title, inner = m.group(1).lower(), m.group(3).strip(), []
            i += 1
            while i < len(lines) and (lines[i].startswith(">") or lines[i].strip() == ""):
                if lines[i].strip() == "" and not (
                    i + 1 < len(lines) and lines[i + 1].startswith(">")
                ):
                    break
                # una línea en blanco seguida de otro "> [!tipo]" empieza un callout nuevo
                if lines[i].strip() == "" and re.match(r"^>\s*\[!\w+\]", lines[i + 1]):
                    break
                inner.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            icon, cls = CALLOUT_META.get(ctype, ("🔸", "c-note"))
            title = title or ctype.capitalize()
            tok = f"XBLOCKX{len(tokens)}XBLOCKX"
            tokens.append((tok,
                f'<div class="callout {cls}"><div class="ttl">{icon} '
                f'{html.escape(title)}</div><div class="body">'
                f'{md_to_html(chr(10).join(inner))}</div></div>'))
            out += ["", tok, ""]
        else:
            out.append(lines[i]); i += 1
    return "\n".join(out)


def rewrite_images(html_text, bucket, slug):
    def sub(m):
        return f'{m.group(1)}="../assets/{bucket}/{slug}/{m.group(2).split("/")[-1]}"'
    return re.sub(r'(src)="(?:\./)?attachments/([^"]+)"', sub, html_text)


def render_body(body, bucket, slug, charts=None):
    tokens = []
    if charts is None:
        charts = []
    body = extract_blocks(strip_first_h1(body), tokens, charts)
    out = md_to_html(body)
    for tok, blk in tokens:
        out = out.replace(f"<p>{tok}</p>", blk).replace(tok, blk)
    return rewrite_images(out, bucket, slug)


def charts_script(charts, prefix=""):
    """Devuelve el <script> que instancia los Chart.js del post (o '').

    Chart.js se sirve auto-alojado desde assets/vendor (sin CDN en runtime)."""
    if not charts:
        return ""
    chartjs = f'<script src="{prefix}assets/vendor/chart.umd.min.js"></script>'
    inits = "\n".join(
        f"new Chart(document.getElementById({json.dumps(cid)}),"
        f"{json.dumps(spec, ensure_ascii=False)});"
        for cid, spec in charts
    )
    defaults = (
        "if(window.Chart){"
        "Chart.defaults.color='#aab0ba';"
        "Chart.defaults.borderColor='rgba(255,255,255,0.08)';"
        "Chart.defaults.font.family=\"'Fira Code', ui-monospace, monospace\";"
        "Chart.defaults.font.size=12;"
        "Chart.defaults.plugins.legend.labels.boxWidth=14;"
        "}"
    )
    return f"{chartjs}\n<script>{defaults}\n{inits}</script>"


# --------------------------------------------------------------------------- #
#  Modelo
# --------------------------------------------------------------------------- #
def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def as_str(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    return "" if v is None else str(v)


def as_list(v):
    if v is None:
        return []
    return [as_str(x) for x in (v if isinstance(v, list) else [v])]


def os_from_path(parts):
    for part in parts:
        if part in ("Linux", "Windows", "Active Directory"):
            return part
    return ""


def collect(col):
    """Devuelve la lista de items de una colección (área)."""
    items = []
    for d in col["dirs"]:
        base = ROOT / d
        if not base.exists():
            continue
        for md in sorted(base.rglob("*.md")):
            meta, body = parse_frontmatter(md.read_text(encoding="utf-8"))
            if col["kind"] == "machine":
                slug = slugify(meta.get("machine") or md.stem)
                items.append({
                    "kind": "machine", "slug": slug, "area": col["id"],
                    "accent": col["accent"],
                    "machine": as_str(meta.get("machine") or md.stem),
                    "title": as_str(meta.get("title") or meta.get("machine") or md.stem),
                    "os": as_str(meta.get("os") or os_from_path(md.relative_to(ROOT).parts)),
                    "platform": as_str(meta.get("platform") or "HackTheBox"),
                    "difficulty": as_str(meta.get("difficulty")),
                    "status": as_str(meta.get("status")),
                    "date": as_str(meta.get("date")),
                    "entry_vector": as_str(meta.get("entry_vector")),
                    "privesc_vector": as_str(meta.get("privesc_vector")),
                    "tags": as_list(meta.get("tags")),
                    "url": f"machines/{slug}.html",
                    "_src": md, "_body": body,
                })
            else:
                cat = as_str(meta.get("category") or col["id"])
                slug = slugify(f'{cat}-{meta.get("title") or md.stem}')
                items.append({
                    "kind": "post", "slug": slug, "area": col["id"],
                    "accent": col["accent"],
                    "title": as_str(meta.get("title") or md.stem),
                    "category": cat,
                    "summary": as_str(meta.get("summary")),
                    "status": as_str(meta.get("status") or "published"),
                    "date": as_str(meta.get("date")),
                    "tags": as_list(meta.get("tags")),
                    "url": f"posts/{slug}.html",
                    "_src": md, "_body": body,
                })
    items.sort(key=lambda m: (m.get("date") or "", m.get("title")), reverse=True)
    return items


# --------------------------------------------------------------------------- #
#  Plantillas HTML
# --------------------------------------------------------------------------- #
FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600'
    '&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
)
HLJS = (
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/'
    'highlight.js/11.9.0/styles/github-dark.min.css">'
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/'
    'highlight.min.js"></script>'
)


def nav_links(prefix):
    links = "".join(
        f'<a href="{prefix}{c["id"]}.html">{c["name"].split(" ")[0].split("·")[0].strip()}</a>'
        for c in COLLECTIONS
    )
    links += f'<a href="{prefix}attack.html">ATT&amp;CK</a>'
    links += f'<a href="{prefix}about.html">Sobre mí</a>'
    return links


def page_shell(title, desc, body, prefix, scripts="", head=""):
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{FONTS}
{HLJS}
<link rel="stylesheet" href="{prefix}assets/style.css">
{head}
</head>
<body>
<nav class="nav"><div class="nav-inner">
  <a class="brand" href="{prefix}index.html"><span class="dot"></span><span class="zero">0x</span>Rioseco</a>
  <div class="nav-links">
    {nav_links(prefix)}
    <a href="{GH_URL}">GitHub ↗</a>
  </div>
</div></nav>
{body}
<footer class="foot"><div class="wrap">
  <div>Uso educativo · entornos autorizados (HTB, CTFs, labs). <a href="{GH_URL}/blob/main/LICENSE">CC BY 4.0</a></div>
  <div><code>Javier Rioseco Rodríguez</code></div>
</div></footer>
<script>hljs.highlightAll();</script>
{scripts}
</body>
</html>
"""


def render_roadmap():
    return "\n".join(
        f'<div class="phase" data-phase="{pid}" style="--accent:{color}">'
        f'<span class="ph-count">0</span><div class="ph-ico">{icon}</div>'
        f'<div class="ph-name">{name}</div>'
        f'<div class="ph-desc">{html.escape(desc)}</div></div>'
        for pid, icon, name, desc, color in ROADMAP_PHASES
    )


# ---- hub ------------------------------------------------------------------ #
def projects_html(projects):
    out = ""
    for p in projects:
        url = as_str(p.get("url"))
        name = html.escape(as_str(p.get("name")))
        title = f'<a href="{html.escape(url)}">{name}</a>' if url else name
        tech = "".join(f"<span>{html.escape(as_str(t))}</span>" for t in (p.get("tech") or []))
        go = f'<a class="go" href="{html.escape(url)}">Ver en GitHub ↗</a>' if url else ""
        out += (f'<article class="project-card"><h3>{title}</h3>'
                f'<p>{html.escape(as_str(p.get("summary")))}</p>'
                f'<div class="skill-chips">{tech}</div>{go}</article>')
    return out


def timeline_html(profile, home=False):
    """Formación + experiencia como dos columnas de línea de tiempo.

    Con home=True se omiten las entradas marcadas con `home: false`."""
    def entries(items, kind):
        out = ""
        for e in items or []:
            if home and e.get("home") is False:
                continue
            sub = " · ".join(x for x in (as_str(e.get("org")), as_str(e.get("place"))) if x)
            lis = "".join(f"<li>{html.escape(as_str(i))}</li>" for i in (e.get("items") or []))
            period = as_str(e.get("period"))
            out += (f'<div class="tl-item"><div class="tl-period">{html.escape(period) or "&nbsp;"}</div>'
                    f'<div class="tl-title">{html.escape(as_str(e.get("title")))}</div>'
                    f'<div class="tl-org">{html.escape(sub)}</div>'
                    + (f"<ul>{lis}</ul>" if lis else "") + "</div>")
        return (f'<div class="tl-col"><h4>{kind}</h4>{out}</div>') if out else ""
    cols = entries(profile.get("education"), "🎓 Formación") + \
        entries(profile.get("experience"), "💼 Experiencia")
    return f'<div class="timeline">{cols}</div>' if cols else ""


def render_index(by_area, recent, profile=None):
    profile = profile or {}
    total = sum(len(v) for v in by_area.values())
    area_cards = ""
    for c in COLLECTIONS:
        n = len(by_area[c["id"]])
        area_cards += (
            f'<a class="area-card" href="{c["id"]}.html" style="--accent:{c["accent"]}">'
            f'<span class="arrow">→</span>'
            f'<div class="ico">{c["icon"]}</div>'
            f'<h3>{html.escape(c["name"])}</h3>'
            f'<p>{html.escape(c["blurb"])}</p>'
            f'<div class="count"><b>{n}</b> '
            f'{"entrada" if n == 1 else "entradas"}</div></a>'
        )
    recent_html = ""
    if recent:
        cards = ""
        for it in recent[:6]:
            area = next(c for c in COLLECTIONS if c["id"] == it["area"])
            cards += (
                f'<a href="{it["url"]}" style="--accent:{it["accent"]}">'
                f'<span class="r-area">{area["icon"]} {html.escape(area["name"].split("·")[0].strip())}</span>'
                f'<span class="r-title">{html.escape(it.get("machine") or it["title"])}</span>'
                f'<span class="r-date">{html.escape(it.get("date") or "")}</span></a>'
            )
        recent_html = f"""
<section><div class="wrap">
  <div class="sec-head"><h2>Últimas entradas</h2><p>lo más reciente de todas las áreas</p></div>
  <div class="recent">{cards}</div>
</div></section>"""

    name = as_str(profile.get("name") or "Javier Rioseco Rodríguez")
    role = as_str(profile.get("role"))
    loc = as_str(profile.get("location"))
    tagline = as_str(profile.get("tagline"))
    stats = "".join(
        f'<div class="stat"><div class="n">{html.escape(as_str(h.get("value")))}</div>'
        f'<div class="l">{html.escape(as_str(h.get("label")))}</div></div>'
        for h in (profile.get("highlights") or [])
    )
    stats += (f'<div class="stat"><div class="n">{total}</div>'
              f'<div class="l">Entradas publicadas en este sitio</div></div>')

    projects = profile.get("projects") or []
    projects_sec = ""
    if projects:
        projects_sec = f"""
<section id="projects"><div class="wrap">
  <div class="sec-head"><h2>Proyectos</h2><p>código propio en GitHub</p></div>
  <div class="projects">{projects_html(projects)}</div>
</div></section>"""

    timeline = timeline_html(profile, home=True)
    timeline_sec = ""
    if timeline:
        timeline_sec = f"""
<section id="trayectoria"><div class="wrap">
  <div class="sec-head"><h2>Trayectoria</h2><p>formación y experiencia</p></div>
  {timeline}
  <p class="roadmap-hint">Perfil completo, skills e idiomas en <a href="about.html">Sobre mí</a>.</p>
</div></section>"""

    body = f"""
<header class="hero"><div class="wrap">
  <span class="tag">// <span class="zero">0x</span>Rioseco — security · research · data</span>
  <h1>{html.escape(name)}</h1>
  {f'<p class="role">{html.escape(role)}{" · " + html.escape(loc) if loc else ""}</p>' if role else ""}
  <p>{html.escape(tagline)}</p>
  <div class="cta">
    <a class="btn primary" href="#areas">Explorar el laboratorio →</a>
    <a class="btn" href="#projects">Proyectos</a>
    <a class="btn" href="about.html">Sobre mí</a>
    <a class="btn" href="https://github.com/javierrr13">GitHub ↗</a>
  </div>
  <div class="stats">{stats}</div>
</div></header>
{projects_sec}
<section id="areas"><div class="wrap">
  <div class="sec-head"><h2>Áreas</h2><p>lo que investigo y documento</p></div>
  <div class="areas">{area_cards}</div>
</div></section>
{recent_html}
{timeline_sec}
"""
    return page_shell(f"{SITE_NAME} — {SITE_DESC}", SITE_DESC, body, prefix="")


# ---- página de área ------------------------------------------------------- #
def machine_card(m):
    import json as _json
    tags = "".join(f"<span>{html.escape(t)}</span>" for t in m["tags"][:6])
    vec = ""
    if m["entry_vector"]:
        vec += f'<div class="vec"><b>Entrada</b>{html.escape(m["entry_vector"])}</div>'
    if m["privesc_vector"]:
        vec += f'<div class="vec"><b>Escalada</b>{html.escape(m["privesc_vector"])}</div>'
    return (
        f'<article class="card" style="--os-color:{os_color(m["os"])}">'
        f'<div class="top"><h3><a href="{m["url"]}">{html.escape(m["machine"])}</a></h3>'
        f'<span class="os">{os_icon(m["os"])} {html.escape(m["os"])}</span></div>'
        f'<div class="meta-row">'
        f'<span class="badge diff-{slugify(m["difficulty"])}">{html.escape(m["difficulty"] or "?")}</span>'
        f'<span class="badge">{html.escape(m["platform"])}</span>'
        f'<span class="badge st-{slugify(m["status"])}">{html.escape(m["status"])}</span></div>'
        f'{vec}<div class="tags">{tags}</div>'
        f'<a class="go" href="{m["url"]}">Leer writeup →</a></article>'
    )


def post_card(p):
    tags = "".join(f"<span>{html.escape(t)}</span>" for t in p["tags"][:6])
    search = html.escape(
        (p["title"] + " " + p["summary"] + " " + " ".join(p["tags"]) + " " + p["category"]).lower(),
        quote=True)
    return (
        f'<article class="post-card" data-search="{search}" style="--accent:{p["accent"]}">'
        f'<div class="pmeta"><span class="cat">{html.escape(p["category"])}</span>'
        f'<span>{html.escape(p["date"] or "")}</span></div>'
        f'<h3><a href="{p["url"]}">{html.escape(p["title"])}</a></h3>'
        f'<div class="summary">{html.escape(p["summary"])}</div>'
        f'<div class="tags">{tags}</div>'
        f'<a class="go" href="{p["url"]}">Leer →</a></article>'
    )


def os_color(os):
    os = (os or "").lower()
    return ("var(--yellow)" if "linux" in os else "var(--blue)" if "windows" in os
            else "var(--purple)" if "active" in os else "var(--green)")


def os_icon(os):
    os = (os or "").lower()
    return ("🐧" if "linux" in os else "🪟" if "windows" in os
            else "🏢" if "active" in os else "🖥️")


def render_area(col, items):
    head = f"""
<header class="area-head"><div class="wrap">
  <div class="eyebrow" style="--accent:{col['accent']}">{col['icon']} área</div>
  <h1>{html.escape(col['name'])}</h1>
  <p>{html.escape(col['blurb'])}</p>
</div></header>"""

    if col["kind"] == "machine":
        cards = "".join(machine_card(m) for m in items) or \
            '<div class="empty">Aún no hay máquinas publicadas.</div>'
        data = [{k: m[k] for k in ("slug", "machine", "title", "os", "platform",
                "difficulty", "status", "date", "entry_vector", "privesc_vector",
                "tags", "url")} for m in items]
        body = head + f"""
<section id="roadmap"><div class="wrap">
  <div class="sec-head"><h2>Roadmap</h2><p>el ciclo que sigue cada writeup</p></div>
  <div class="roadmap">{render_roadmap()}</div>
  <p class="roadmap-hint" id="phase-label"></p>
</div></section>
<section id="machines"><div class="wrap">
  <div class="sec-head"><h2>Máquinas</h2><p>{len(items)} writeups · filtra por fase, OS o búsqueda</p></div>
  <div class="filters">
    <label class="search">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
      <input id="search-input" type="search" placeholder="buscar máquina, técnica, CVE…"
        autocomplete="off" spellcheck="false">
    </label>
    <div class="chips">
      <span class="chip on" data-os="all">Todas</span>
      <span class="chip" data-os="linux">🐧 Linux</span>
      <span class="chip" data-os="windows">🪟 Windows</span>
      <span class="chip" data-os="active">🏢 AD</span>
    </div>
  </div>
  <div class="grid" id="machine-grid"></div>
</div></section>"""
        scripts = ("<script>window.MACHINES = "
                   + json.dumps(data, ensure_ascii=False)
                   + ';</script>\n<script src="assets/app.js"></script>')
        return page_shell(f'{col["name"]} — {SITE_NAME}', col["blurb"], body,
                          prefix="", scripts=scripts)

    # kind == post
    if items:
        cards = "".join(post_card(p) for p in items)
        empty = '<div class="empty" id="post-empty" style="display:none">Sin resultados.</div>'
    else:
        cards = ""
        empty = ('<div class="empty" id="post-empty">Aún no hay entradas en esta área. '
                 'Añade un <code>.md</code> con su frontmatter en la carpeta correspondiente '
                 'del vault y aparecerá aquí.</div>')
    body = head + f"""
<section><div class="wrap">
  <div class="filters">
    <label class="search">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
      <input id="post-search" type="search" placeholder="buscar en esta área…"
        autocomplete="off" spellcheck="false">
    </label>
  </div>
  <div class="grid" id="post-grid">{cards}{empty}</div>
</div></section>"""
    return page_shell(f'{col["name"]} — {SITE_NAME}', col["blurb"], body,
                      prefix="", scripts='<script src="assets/app.js"></script>')


# ---- detalle -------------------------------------------------------------- #
def render_machine(m):
    prose = render_body(m["_body"], "machines", m["slug"])
    info = "".join(
        f'<div><div class="k">{k}</div><div class="v">{html.escape(v)}</div></div>'
        for k, v in (("Plataforma", m["platform"]), ("Dificultad", m["difficulty"]),
                     ("OS", m["os"]), ("Estado", m["status"]), ("Fecha", m["date"]))
        if v)
    for label, key in (("Vector de entrada", "entry_vector"), ("Escalada", "privesc_vector")):
        if m[key]:
            info += f'<div><div class="k">{label}</div><div class="v">{html.escape(m[key])}</div></div>'
    body = f"""
<main class="article"><div class="wrap">
  <div class="crumbs"><a href="../index.html">Inicio</a> / <a href="../offensive.html">Ofensiva</a> / {html.escape(m["machine"])}</div>
  <div class="art-head"><h1>{html.escape(m["title"] or m["machine"])}</h1>
    <div class="infobox">{info}</div></div>
  <article class="prose">{prose}</article>
  <div class="article-nav">
    <a class="btn" href="../offensive.html">← Todas las máquinas</a>
    <a class="btn" href="{GH_URL}">Ver en GitHub ↗</a>
  </div>
</div></main>"""
    mermaid = ('<script type="module">import mermaid from '
               '"https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";'
               'mermaid.initialize({startOnLoad:true,theme:"dark"});</script>')
    return page_shell(f'{m["machine"]} — {SITE_NAME}',
                      f'Writeup de {m["machine"]} ({m["os"]}, {m["difficulty"]}).',
                      body, prefix="../", scripts=mermaid)


def render_post(p):
    charts = []
    prose = render_body(p["_body"], "posts", p["slug"], charts)
    col = next(c for c in COLLECTIONS if c["id"] == p["area"])
    info = "".join(
        f'<div><div class="k">{k}</div><div class="v">{html.escape(v)}</div></div>'
        for k, v in (("Categoría", p["category"]), ("Fecha", p["date"]),
                     ("Estado", p["status"]))
        if v)
    body = f"""
<main class="article"><div class="wrap">
  <div class="crumbs"><a href="../index.html">Inicio</a> / <a href="../{col['id']}.html">{html.escape(col['name'].split('·')[0].strip())}</a> / {html.escape(p["title"])}</div>
  <div class="art-head"><h1>{html.escape(p["title"])}</h1>
    <div class="infobox">{info}</div></div>
  <article class="prose">{prose}</article>
  <div class="article-nav">
    <a class="btn" href="../{col['id']}.html">← Volver a {html.escape(col['name'].split('·')[0].strip())}</a>
    <a class="btn" href="{GH_URL}">Ver en GitHub ↗</a>
  </div>
</div></main>"""
    return page_shell(f'{p["title"]} — {SITE_NAME}',
                      p["summary"] or p["title"], body, prefix="../",
                      scripts=charts_script(charts, "../"))


# ---- MITRE ATT&CK coverage ------------------------------------------------ #
TACTIC_ORDER = [
    "Reconnaissance", "Resource Development", "Initial Access", "Execution",
    "Persistence", "Privilege Escalation", "Defense Evasion", "Credential Access",
    "Discovery", "Lateral Movement", "Collection", "Command and Control",
    "Exfiltration", "Impact",
]
TACTIC_ACCENT = {
    "Initial Access": "var(--yellow)", "Execution": "var(--teal)",
    "Persistence": "var(--teal)", "Privilege Escalation": "var(--orange)",
    "Defense Evasion": "var(--purple)", "Credential Access": "var(--green)",
    "Discovery": "var(--teal)", "Lateral Movement": "var(--blue)",
    "Collection": "var(--green)", "Command and Control": "var(--purple)",
    "Exfiltration": "var(--orange)", "Impact": "var(--orange)",
}


def collect_attack(machines):
    """Agrega el mapeo ATT&CK de todas las máquinas: tactic -> {tech_id: {...}}."""
    by_tactic = {}
    for m in machines:
        meta, _ = parse_frontmatter(m["_src"].read_text(encoding="utf-8"))
        for t in (meta.get("attack") or []):
            tactic = as_str(t.get("tactic")) or "Otros"
            tid = as_str(t.get("id"))
            name = as_str(t.get("name"))
            d = by_tactic.setdefault(tactic, {})
            e = d.setdefault(tid, {"id": tid, "name": name, "machines": []})
            e["machines"].append({"name": m["machine"], "url": m["url"]})
    return by_tactic


def render_attack(by_tactic):
    tactics = [t for t in TACTIC_ORDER if t in by_tactic] + \
              [t for t in by_tactic if t not in TACTIC_ORDER]
    n_tech = sum(len(v) for v in by_tactic.values())

    cols = ""
    for tac in tactics:
        accent = TACTIC_ACCENT.get(tac, "var(--green)")
        techs = ""
        for e in sorted(by_tactic[tac].values(), key=lambda x: x["id"]):
            machs = " · ".join(
                f'<a href="{mm["url"]}">{html.escape(mm["name"])}</a>' for mm in e["machines"])
            techs += (
                f'<div class="tech"><div class="tech-id">{html.escape(e["id"])}</div>'
                f'<div class="tech-name">{html.escape(e["name"])}</div>'
                f'<div class="tech-src">{machs}</div></div>'
            )
        cols += (
            f'<div class="tac-col" style="--accent:{accent}">'
            f'<div class="tac-head">{html.escape(tac)}'
            f'<span class="tac-n">{len(by_tactic[tac])}</span></div>{techs}</div>'
        )

    # gráfico: nº de técnicas por táctica
    chart = {
        "type": "bar",
        "caption": "Técnicas distintas demostradas por táctica (mapeo propio a MITRE ATT&CK Enterprise).",
        "data": {"labels": tactics,
                 "datasets": [{"label": "Técnicas", "data": [len(by_tactic[t]) for t in tactics],
                               "backgroundColor": "#9fef00"}]},
        "options": {"responsive": True, "maintainAspectRatio": False,
                    "scales": {"y": {"beginAtZero": True, "ticks": {"precision": 0}}},
                    "plugins": {"legend": {"display": False},
                                "title": {"display": True, "text": "Cobertura por táctica"}}},
    }
    charts = [("attackchart", chart)]

    body = f"""
<header class="area-head"><div class="wrap">
  <div class="eyebrow" style="--accent:var(--green)">🎯 cobertura</div>
  <h1>Mapa MITRE ATT&amp;CK</h1>
  <p>Técnicas de ATT&amp;CK Enterprise demostradas en los writeups, agrupadas por táctica.
     <b>{n_tech}</b> técnicas en <b>{len(tactics)}</b> tácticas.</p>
</div></header>
<section><div class="wrap">
  <figure class="chart-card"><div class="chart-wrap"><canvas id="attackchart"></canvas></div>
  <figcaption>Técnicas distintas por táctica. Mapeo orientativo propio a MITRE ATT&amp;CK Enterprise.</figcaption></figure>
  <div class="attack-board">{cols}</div>
  <p class="roadmap-hint">Cada técnica enlaza con el writeup donde se demuestra. El mapeo es
     <b>orientativo</b> (interpretación propia), no una clasificación oficial de MITRE.</p>
</div></section>"""
    return page_shell(f"MITRE ATT&CK — {SITE_NAME}",
                      "Cobertura de técnicas MITRE ATT&CK demostradas en los writeups.",
                      body, prefix="", scripts=charts_script(charts, ""))


# ---- página "Sobre mí" ---------------------------------------------------- #
ABOUT_SRC = ROOT / "Sobre mí.md"


def render_about():
    if not ABOUT_SRC.exists():
        return None
    meta, body_md = parse_frontmatter(ABOUT_SRC.read_text(encoding="utf-8"))
    name = as_str(meta.get("name") or "Javier Rioseco Rodríguez")
    role = as_str(meta.get("role"))
    loc = as_str(meta.get("location"))
    tagline = as_str(meta.get("tagline"))
    bio = render_body(body_md, "posts", "about")

    # enlaces de contacto
    btns = ""
    for label, url in (meta.get("links") or {}).items():
        if as_str(url):
            btns += f'<a class="btn" href="{html.escape(as_str(url))}">{html.escape(label)} ↗</a>'
    if as_str(meta.get("email")):
        btns += f'<a class="btn" href="mailto:{html.escape(as_str(meta["email"]))}">Email</a>'
    if as_str(meta.get("cv")):
        btns = f'<a class="btn primary" href="{html.escape(as_str(meta["cv"]))}">Descargar CV ↓</a>' + btns

    # skills
    skills_html = ""
    for group, items in (meta.get("skills") or {}).items():
        chips = "".join(f"<span>{html.escape(as_str(s))}</span>" for s in (items or []))
        skills_html += (f'<div class="skill-group"><h4>{html.escape(group)}</h4>'
                        f'<div class="skill-chips">{chips}</div></div>')

    langs = meta.get("languages") or []
    langs_html = ""
    if langs:
        chips = "".join(
            f'<span><b>{html.escape(as_str(l.get("name")))}</b> · {html.escape(as_str(l.get("level")))}</span>'
            for l in langs)
        langs_html = (f'<div class="sec-head" style="margin-top:34px"><h2>Idiomas</h2></div>'
                      f'<div class="skill-chips langs">{chips}</div>')

    certs = [as_str(c) for c in (meta.get("certs") or []) if as_str(c)]
    certs_html = ""
    if certs:
        lis = "".join(f"<li>{html.escape(c)}</li>" for c in certs)
        certs_html = (f'<div class="sec-head"><h2>Certificaciones</h2></div>'
                      f'<ul class="certs">{lis}</ul>')

    body = f"""
<header class="area-head"><div class="wrap">
  <div class="eyebrow" style="--accent:var(--green)">👤 sobre mí</div>
  <h1>{html.escape(name)}</h1>
  {f'<p class="role">{html.escape(role)}{" · " + html.escape(loc) if loc else ""}</p>' if role else ""}
  {f'<p>{html.escape(tagline)}</p>' if tagline else ""}
  <div class="cta">{btns}</div>
</div></header>
<section><div class="wrap">
  <article class="prose">{bio}</article>
  {f'<div class="sec-head" style="margin-top:34px"><h2>Trayectoria</h2></div>{timeline_html(meta)}' if timeline_html(meta) else ""}
  {f'<div class="sec-head" style="margin-top:34px"><h2>Proyectos</h2></div><div class="projects">{projects_html(meta.get("projects"))}</div>' if meta.get("projects") else ""}
  <div class="sec-head" style="margin-top:34px"><h2>Skills</h2></div>
  <div class="skills">{skills_html}</div>
  {langs_html}
  {certs_html}
</div></section>"""
    return page_shell(f"Sobre mí — {SITE_NAME}",
                      tagline or f"Perfil de {name}", body, prefix="")


# --------------------------------------------------------------------------- #
#  Build
# --------------------------------------------------------------------------- #
def copy_attachments(item, bucket):
    src = item["_src"].parent / "attachments"
    if src.is_dir():
        dst = OUT / "assets" / bucket / item["slug"]
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    for sub in ("machines", "posts", "assets"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE_SRC / "assets", OUT / "assets", dirs_exist_ok=True)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    by_area, recent = {}, []
    for col in COLLECTIONS:
        items = collect(col)
        by_area[col["id"]] = items
        (OUT / f'{col["id"]}.html').write_text(render_area(col, items), encoding="utf-8")
        for it in items:
            if it["kind"] == "machine":
                (OUT / "machines" / f'{it["slug"]}.html').write_text(render_machine(it), encoding="utf-8")
                copy_attachments(it, "machines")
            else:
                (OUT / "posts" / f'{it["slug"]}.html').write_text(render_post(it), encoding="utf-8")
                copy_attachments(it, "posts")
            if it.get("date"):
                recent.append(it)

    recent.sort(key=lambda m: m["date"], reverse=True)
    profile = {}
    if ABOUT_SRC.exists():
        profile, _ = parse_frontmatter(ABOUT_SRC.read_text(encoding="utf-8"))
    (OUT / "index.html").write_text(render_index(by_area, recent, profile), encoding="utf-8")

    # Página de cobertura MITRE ATT&CK (agregada de las máquinas)
    by_tactic = collect_attack(by_area.get("offensive", []))
    n_tech = sum(len(v) for v in by_tactic.values())
    (OUT / "attack.html").write_text(render_attack(by_tactic), encoding="utf-8")

    # Página "Sobre mí"
    about = render_about()
    if about:
        (OUT / "about.html").write_text(about, encoding="utf-8")

    total = sum(len(v) for v in by_area.values())
    print(f"✅ Sitio 0xRioseco generado en {OUT} — {total} entrada(s):")
    for col in COLLECTIONS:
        print(f"   · {col['name']:<34} {len(by_area[col['id']])} item(s) → {col['id']}.html")
    print(f"   · MITRE ATT&CK: {n_tech} técnicas en {len(by_tactic)} tácticas → attack.html")
    print(f"   · Sobre mí → about.html" if about else "   · (sin Sobre mí.md)")


if __name__ == "__main__":
    main()
