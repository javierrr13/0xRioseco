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
GH_URL = "https://github.com/javierrr13/htb-operations-center"

# --------------------------------------------------------------------------- #
#  Áreas del sitio
# --------------------------------------------------------------------------- #
COLLECTIONS = [
    dict(id="offensive", name="Ofensiva · HTB & CTFs", icon="🎯",
         accent="var(--green)", kind="machine", dirs=["01 - Machines"],
         blurb="Máquinas y retos resueltos paso a paso, de la enumeración al "
               "root — y las lecciones que deja cada uno."),
    dict(id="research", name="Investigación de vulnerabilidades", icon="🔬",
         accent="var(--orange)", kind="post", dirs=["07 - Research"],
         blurb="Análisis de CVEs, estudio de parches, pruebas de concepto y "
               "hallazgos propios."),
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


def extract_blocks(body, tokens):
    def mermaid_sub(m):
        tok = f"XBLOCKX{len(tokens)}XBLOCKX"
        tokens.append((tok, f'<pre class="mermaid">{html.escape(m.group(1))}</pre>'))
        return f"\n\n{tok}\n\n"

    body = re.sub(r"```mermaid\n(.*?)```", mermaid_sub, body, flags=re.DOTALL)

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


def render_body(body, bucket, slug):
    tokens = []
    body = extract_blocks(strip_first_h1(body), tokens)
    out = md_to_html(body)
    for tok, blk in tokens:
        out = out.replace(f"<p>{tok}</p>", blk).replace(tok, blk)
    return rewrite_images(out, bucket, slug)


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
def render_index(by_area, recent):
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

    body = f"""
<header class="hero"><div class="wrap">
  <span class="tag">// personal lab — security · research · data</span>
  <h1><span class="grad">0x</span>Rioseco</h1>
  <p>Laboratorio personal de <b>Javier Rioseco</b>: seguridad ofensiva, investigación
     de vulnerabilidades y data science. Donde documento lo que aprendo, rompo e
     investigo — y lo que vaya saliendo.</p>
  <div class="cta">
    <a class="btn primary" href="#areas">Explorar áreas →</a>
    <a class="btn" href="{GH_URL}">Ver en GitHub ↗</a>
  </div>
  <div class="stats">
    <div class="stat"><div class="n">{total}</div><div class="l">Entradas publicadas</div></div>
    <div class="stat"><div class="n">{len(COLLECTIONS)}</div><div class="l">Áreas</div></div>
    <div class="stat"><div class="n">{len(by_area["offensive"])}</div><div class="l">Máquinas / retos</div></div>
    <div class="stat"><div class="n">{len(recent)}</div><div class="l">Con fecha</div></div>
  </div>
</div></header>

<section id="areas"><div class="wrap">
  <div class="sec-head"><h2>Áreas</h2><p>elige por dónde empezar</p></div>
  <div class="areas">{area_cards}</div>
</div></section>
{recent_html}
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
    prose = render_body(p["_body"], "posts", p["slug"])
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
                      p["summary"] or p["title"], body, prefix="../")


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
    for f in (SITE_SRC / "assets").iterdir():
        if f.is_file():
            shutil.copy2(f, OUT / "assets" / f.name)
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
    (OUT / "index.html").write_text(render_index(by_area, recent), encoding="utf-8")

    total = sum(len(v) for v in by_area.values())
    print(f"✅ Sitio 0xRioseco generado en {OUT} — {total} entrada(s):")
    for col in COLLECTIONS:
        print(f"   · {col['name']:<34} {len(by_area[col['id']])} item(s) → {col['id']}.html")


if __name__ == "__main__":
    main()
