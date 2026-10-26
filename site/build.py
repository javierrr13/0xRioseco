#!/usr/bin/env python3
"""
Generador de la web de HTB Operations Center.

Lee los writeups del vault de Obsidian (`01 - Machines/**/*.md`), convierte el
Markdown a HTML (incluyendo callouts de Obsidian, bloques mermaid e imágenes) y
emite un sitio estático en `_site/` listo para GitHub Pages:

    _site/
      index.html                      portada: hero + roadmap + grid de máquinas
      machines/<slug>.html            un writeup por página
      assets/style.css, app.js        copiados de site/assets/
      assets/machines/<slug>/*.png    attachments de cada máquina

El vault sigue siendo la fuente de verdad: añade una nota nueva bajo
`01 - Machines/` con su frontmatter y, al reconstruir, aparece sola.
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
MACHINES_DIR = ROOT / "01 - Machines"

MD_EXTS = ["fenced_code", "tables", "sane_lists", "attr_list", "md_in_html"]

CALLOUT_META = {
    "note": ("ℹ️", "c-note"), "info": ("ℹ️", "c-info"),
    "tip": ("💡", "c-tip"), "hint": ("💡", "c-tip"), "success": ("✅", "c-tip"),
    "warning": ("⚠️", "c-warning"), "caution": ("⚠️", "c-warning"),
    "danger": ("🔥", "c-danger"), "error": ("⛔", "c-danger"), "bug": ("🐞", "c-danger"),
    "abstract": ("📋", "c-abstract"), "summary": ("📋", "c-abstract"),
    "example": ("🧪", "c-info"), "quote": ("❝", "c-note"),
}


# --------------------------------------------------------------------------- #
#  Parsing helpers
# --------------------------------------------------------------------------- #
def parse_frontmatter(text):
    """Devuelve (meta_dict, body) separando el bloque YAML inicial."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            return meta, parts[2].lstrip("\n")
    return {}, text


def strip_first_h1(body):
    """Quita el primer encabezado H1 del cuerpo (lo mostramos en la cabecera)."""
    lines = body.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "":
            continue
        if ln.startswith("# "):
            del lines[i]
            # quita una línea en blanco sobrante inmediatamente después
            if i < len(lines) and lines[i].strip() == "":
                del lines[i]
        break
    return "\n".join(lines)


def extract_blocks(body, tokens):
    """
    Extrae bloques mermaid y callouts de Obsidian, sustituyéndolos por tokens
    de una sola línea para que no interfieran con el conversor Markdown.
    Rellena `tokens` (lista de (token, html)).
    """
    # --- mermaid ```mermaid ... ``` ---
    def mermaid_sub(m):
        idx = len(tokens)
        tok = f"XBLOCKX{idx}XBLOCKX"
        raw = m.group(1)
        tokens.append((tok, f'<pre class="mermaid">{html.escape(raw)}</pre>'))
        return f"\n\n{tok}\n\n"

    body = re.sub(r"```mermaid\n(.*?)```", mermaid_sub, body, flags=re.DOTALL)

    # --- callouts: un blockquote cuyo primer renglón es [!tipo] título ---
    out_lines = []
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^>\s*\[!(\w+)\]([+-]?)\s*(.*)$", lines[i])
        if m:
            ctype = m.group(1).lower()
            title = m.group(3).strip()
            inner = []
            i += 1
            while i < len(lines) and (lines[i].startswith(">") or lines[i].strip() == ""):
                if lines[i].strip() == "" and not (
                    i + 1 < len(lines) and lines[i + 1].startswith(">")
                ):
                    break
                inner.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            icon, cls = CALLOUT_META.get(ctype, ("🔸", "c-note"))
            if not title:
                title = ctype.capitalize()
            inner_html = md_to_html("\n".join(inner))
            idx = len(tokens)
            tok = f"XBLOCKX{idx}XBLOCKX"
            block = (
                f'<div class="callout {cls}">'
                f'<div class="ttl">{icon} {html.escape(title)}</div>'
                f'<div class="body">{inner_html}</div></div>'
            )
            tokens.append((tok, block))
            out_lines.append("")
            out_lines.append(tok)
            out_lines.append("")
        else:
            out_lines.append(lines[i])
            i += 1
    return "\n".join(out_lines)


def md_to_html(md_text):
    return markdown.markdown(md_text, extensions=MD_EXTS, output_format="html5")


def rewrite_images(html_text, slug):
    """Reescribe rutas relativas de imágenes a la carpeta de assets copiada."""
    def sub(m):
        attr, path = m.group(1), m.group(2)
        fname = path.split("/")[-1]
        return f'{attr}="../assets/machines/{slug}/{fname}"'

    return re.sub(r'(src)="(?:\./)?attachments/([^"]+)"', sub, html_text)


def render_body(body, slug):
    tokens = []
    body = strip_first_h1(body)
    body = extract_blocks(body, tokens)
    out = md_to_html(body)
    # reinserta los bloques extraídos (envueltos por markdown en <p>…</p>)
    for tok, blk in tokens:
        out = out.replace(f"<p>{tok}</p>", blk).replace(tok, blk)
    out = rewrite_images(out, slug)
    return out


# --------------------------------------------------------------------------- #
#  Model
# --------------------------------------------------------------------------- #
def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def as_str(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    return "" if v is None else str(v)


def os_from_path(p):
    for part in p.parts:
        if part in ("Linux", "Windows", "Active Directory"):
            return part
    return ""


def collect_machines():
    machines = []
    if not MACHINES_DIR.exists():
        return machines
    for md in sorted(MACHINES_DIR.rglob("*.md")):
        raw = md.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        name = meta.get("machine") or meta.get("title") or md.stem
        slug = slugify(meta.get("machine") or md.stem)
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        machines.append({
            "slug": slug,
            "machine": as_str(meta.get("machine") or md.stem),
            "title": as_str(meta.get("title") or name),
            "os": as_str(meta.get("os") or os_from_path(md.relative_to(ROOT))),
            "platform": as_str(meta.get("platform") or "HackTheBox"),
            "difficulty": as_str(meta.get("difficulty")),
            "status": as_str(meta.get("status")),
            "date": as_str(meta.get("date")),
            "entry_vector": as_str(meta.get("entry_vector")),
            "privesc_vector": as_str(meta.get("privesc_vector")),
            "tags": [as_str(t) for t in tags],
            "url": f"machines/{slug}.html",
            "_src": md,
            "_body": body,
        })
    return machines


# --------------------------------------------------------------------------- #
#  Templates
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


def page_shell(title, desc, body, prefix, head="", scripts=""):
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
  <a class="brand" href="{prefix}index.html"><span class="dot"></span>HTB&nbsp;<b>Operations Center</b></a>
  <div class="nav-links">
    <a href="{prefix}index.html#roadmap">Roadmap</a>
    <a href="{prefix}index.html#machines">Máquinas</a>
    <a href="https://github.com/javierrr13/htb-operations-center">GitHub ↗</a>
  </div>
</div></nav>
{body}
<footer class="foot"><div class="wrap">
  <div>Uso educativo · entornos autorizados (HTB, CTFs, labs). <a href="https://github.com/javierrr13/htb-operations-center/blob/main/LICENSE">CC BY 4.0</a></div>
  <div><code>Javier Rioseco Rodríguez</code></div>
</div></footer>
<script>hljs.highlightAll();</script>
{scripts}
</body>
</html>
"""


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


def render_roadmap():
    nodes = []
    for pid, icon, name, desc, color in ROADMAP_PHASES:
        nodes.append(
            f'<div class="phase" data-phase="{pid}" style="--accent:{color}">'
            f'<span class="ph-count">0</span>'
            f'<div class="ph-ico">{icon}</div>'
            f'<div class="ph-name">{name}</div>'
            f'<div class="ph-desc">{html.escape(desc)}</div></div>'
        )
    return "\n".join(nodes)


def render_index(machines):
    n = len(machines)
    n_linux = sum(1 for m in machines if "linux" in m["os"].lower())
    n_win = sum(1 for m in machines if "windows" in m["os"].lower())
    tagset = set()
    for m in machines:
        tagset.update(m["tags"])
    body = f"""
<header class="hero"><div class="wrap">
  <span class="tag">// cybersecurity knowledge base</span>
  <h1>HTB <span class="grad">Operations Center</span></h1>
  <p>Base de conocimiento de pentesting y Hack The Box: writeups documentados paso
     a paso siguiendo un mismo ciclo, de la enumeración al root — y las lecciones
     que deja cada máquina.</p>
  <div class="cta">
    <a class="btn primary" href="#machines">Ver máquinas →</a>
    <a class="btn" href="#roadmap">Explorar el roadmap</a>
  </div>
  <div class="stats">
    <div class="stat"><div class="n">{n}</div><div class="l">Máquinas documentadas</div></div>
    <div class="stat"><div class="n">{n_linux}</div><div class="l">Linux</div></div>
    <div class="stat"><div class="n">{n_win}</div><div class="l">Windows</div></div>
    <div class="stat"><div class="n">{len(tagset)}</div><div class="l">Técnicas / tags</div></div>
  </div>
</div></header>

<section id="roadmap"><div class="wrap">
  <div class="sec-head"><h2>Roadmap</h2><p>el ciclo que sigue cada writeup</p></div>
  <div class="roadmap">{render_roadmap()}</div>
  <p class="roadmap-hint" id="phase-label"></p>
</div></section>

<section id="machines"><div class="wrap">
  <div class="sec-head"><h2>Máquinas</h2><p>{n} writeups · filtra por fase, OS o búsqueda</p></div>
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
</div></section>
"""
    data = [{k: m[k] for k in (
        "slug", "machine", "title", "os", "platform", "difficulty",
        "status", "date", "entry_vector", "privesc_vector", "tags", "url")}
        for m in machines]
    scripts = (
        "<script>window.MACHINES = "
        + json.dumps(data, ensure_ascii=False)
        + ";</script>\n<script src=\"assets/app.js\"></script>"
    )
    return page_shell(
        "HTB Operations Center — Knowledge Base",
        "Writeups de Hack The Box y base de conocimiento de ciberseguridad ofensiva.",
        body, prefix="", scripts=scripts,
    )


def render_machine(m):
    prose = render_body(m["_body"], m["slug"])
    info = []
    for k, v in (("Plataforma", m["platform"]), ("Dificultad", m["difficulty"]),
                 ("OS", m["os"]), ("Estado", m["status"]), ("Fecha", m["date"])):
        if v:
            info.append(f'<div><div class="k">{k}</div><div class="v">{html.escape(v)}</div></div>')
    vecs = ""
    if m["entry_vector"]:
        vecs += f'<div><div class="k">Vector de entrada</div><div class="v">{html.escape(m["entry_vector"])}</div></div>'
    if m["privesc_vector"]:
        vecs += f'<div><div class="k">Escalada</div><div class="v">{html.escape(m["privesc_vector"])}</div></div>'
    body = f"""
<main class="article"><div class="wrap">
  <div class="crumbs"><a href="../index.html">Inicio</a> / <a href="../index.html#machines">Máquinas</a> / {html.escape(m["machine"])}</div>
  <div class="art-head">
    <h1>{html.escape(m["title"] or m["machine"])}</h1>
    <div class="infobox">{''.join(info)}{vecs}</div>
  </div>
  <article class="prose">{prose}</article>
  <div class="article-nav">
    <a class="btn" href="../index.html#machines">← Todas las máquinas</a>
    <a class="btn" href="https://github.com/javierrr13/htb-operations-center">Ver en GitHub ↗</a>
  </div>
</div></main>
"""
    mermaid = (
        '<script type="module">import mermaid from '
        '"https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";'
        'mermaid.initialize({startOnLoad:true,theme:"dark"});</script>'
    )
    return page_shell(
        f'{m["machine"]} — HTB Operations Center',
        f'Writeup de la máquina {m["machine"]} ({m["os"]}, {m["difficulty"]}).',
        body, prefix="../", scripts=mermaid,
    )


# --------------------------------------------------------------------------- #
#  Build
# --------------------------------------------------------------------------- #
def copy_attachments(m):
    src = m["_src"].parent / "attachments"
    if src.is_dir():
        dst = OUT / "assets" / "machines" / m["slug"]
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "machines").mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(parents=True, exist_ok=True)

    # assets estáticos
    for f in (SITE_SRC / "assets").iterdir():
        if f.is_file():
            shutil.copy2(f, OUT / "assets" / f.name)
    # evita que Pages procese el sitio con Jekyll
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    machines = collect_machines()
    (OUT / "index.html").write_text(render_index(machines), encoding="utf-8")
    for m in machines:
        (OUT / "machines" / f'{m["slug"]}.html').write_text(render_machine(m), encoding="utf-8")
        copy_attachments(m)

    print(f"✅ Sitio generado en {OUT} — {len(machines)} máquina(s):")
    for m in machines:
        print(f"   · {m['machine']:<12} → machines/{m['slug']}.html  ({m['os']}, {m['difficulty']})")


if __name__ == "__main__":
    main()
