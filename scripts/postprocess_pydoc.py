#!/usr/bin/env python3
"""Style generated pydoc pages for GitHub Pages."""

from __future__ import annotations

from html import escape
from pathlib import Path
import re
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
API_DIR = DOCS_DIR / "api"
STYLESHEET_PATH = DOCS_DIR / "pydoc.css"

HEAD_RE = re.compile(
    r"<head>\s*<meta charset=\"utf-8\">\s*<title>(.*?)</title>\s*</head>",
    re.DOTALL,
)
BODY_RE = re.compile(r"<body>", re.DOTALL)
INDEX_LINK_RE = re.compile(r'href="\."')
FILE_LINK_RE = re.compile(r'<a href="(file:[^"]+)">([^<]+)</a>')
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)

STYLESHEET = """\
:root {
  --bg: #f7f4eb;
  --surface: #fffdf8;
  --surface-strong: #f0e8d6;
  --border: #d9ccb0;
  --text: #1f2430;
  --muted: #5d6472;
  --accent: #b96d1a;
  --accent-soft: #efe1c7;
  --link: #1f5fa8;
  --code-bg: #f4efe4;
  --shadow: 0 16px 40px rgba(31, 36, 48, 0.08);
}

* {
  box-sizing: border-box;
}

html {
  background: linear-gradient(180deg, #f3eee1 0%, #fbf8f2 100%);
}

body {
  margin: 0;
  padding: 32px 20px 64px;
  color: var(--text);
  font: 15px/1.6 "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif;
}

body.pydoc-page,
body.docs-home {
  max-width: 1100px;
  margin: 0 auto;
}

a {
  color: var(--link);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

code,
.code,
tt {
  font-family: "SFMono-Regular", "Cascadia Code", "JetBrains Mono", Consolas, monospace;
  font-size: 0.95em;
}

code,
.source-path {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.1rem 0.4rem;
}

.heading,
.section,
.hero,
.module-list {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.heading {
  margin-bottom: 24px;
}

.heading td {
  padding: 20px 24px;
  vertical-align: top;
}

.heading .title {
  font-size: 2rem;
  line-height: 1.1;
}

.heading .extra {
  width: 32%;
  text-align: right;
  color: var(--muted);
  font-size: 0.95rem;
}

.section {
  margin: 24px 0;
}

.section td {
  padding: 12px 16px;
  vertical-align: top;
}

.section-title,
.bigsection {
  font-size: 1rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.decor,
.heading-text,
.pkg-content-decor,
.index-decor,
.title-decor,
.data-decor,
.functions-decor,
.error-decor {
  background: var(--surface-strong);
}

.singlecolumn,
.multicolumn {
  width: auto;
}

dl {
  margin: 0.5rem 0 0;
}

dt {
  margin-top: 0.8rem;
}

dd {
  margin-left: 1.25rem;
}

hr {
  border: 0;
  border-top: 1px solid var(--border);
  margin: 1rem 0;
}

.white {
  color: inherit;
}

.hero,
.module-list {
  padding: 28px 32px;
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--accent);
  font: 700 0.78rem/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero h1 {
  margin: 0 0 12px;
  font-size: 2.8rem;
  line-height: 1;
}

.hero p,
.module-list p {
  margin: 0;
  color: var(--muted);
  max-width: 58rem;
}

.cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 22px;
}

.cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.7rem 1rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  font: 600 0.92rem/1.1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.cta.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fffdf8;
}

.cta.secondary {
  background: var(--accent-soft);
  color: var(--text);
}

.module-list {
  margin-top: 24px;
}

.module-list ul {
  list-style: none;
  padding: 0;
  margin: 20px 0 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.module-list li {
  margin: 0;
}

.module-list a {
  display: block;
  height: 100%;
  padding: 14px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  color: var(--text);
}

.module-list a:hover {
  border-color: var(--accent);
  box-shadow: 0 10px 24px rgba(185, 109, 26, 0.08);
  text-decoration: none;
}

.module-list .label {
  display: block;
  font: 700 1rem/1.3 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.module-list .meta {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 0.9rem;
}

@media (max-width: 800px) {
  .heading tr,
  .heading td {
    display: block;
    width: 100%;
    text-align: left;
  }

  .heading .extra {
    padding-top: 0;
  }

  .hero,
  .module-list {
    padding: 22px 20px;
  }

  .hero h1 {
    font-size: 2.2rem;
  }
}
"""


def extract_title(text: str) -> str:
    """Return the document title, or a stable fallback."""
    match = TITLE_RE.search(text)
    if match:
        return match.group(1).strip()
    return "ClawDeck API Docs"


def sanitize_source_links(text: str) -> str:
    """Replace local file URLs with repo-relative source paths."""

    def replace(match: re.Match[str]) -> str:
        href = match.group(1)
        parsed = urlparse(href)
        path = Path(unquote(parsed.path))
        try:
            display = path.relative_to(ROOT).as_posix()
        except ValueError:
            display = path.name or match.group(2)
        return f'<code class="source-path">{escape(display)}</code>'

    return FILE_LINK_RE.sub(replace, text)


def style_api_page(path: Path) -> None:
    """Inject shared styling and fix links in one generated pydoc page."""
    text = path.read_text(encoding="utf-8")
    title = extract_title(text)
    text = HEAD_RE.sub(
        (
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{title}</title>\n"
            '<link rel="stylesheet" href="../pydoc.css">\n'
            "</head>"
        ),
        text,
        count=1,
    )
    text = BODY_RE.sub('<body class="pydoc-page">', text, count=1)
    text = INDEX_LINK_RE.sub('href="index.html"', text)
    text = sanitize_source_links(text)
    path.write_text(text, encoding="utf-8")


def title_from_stem(stem: str) -> str:
    """Build a display title from a generated HTML stem."""
    if stem == "clawdeck":
        return "clawdeck package"
    return stem


def category_from_stem(stem: str) -> str:
    """Return a short descriptor for the generated page."""
    if stem == "clawdeck":
        return "Package overview"
    if stem.startswith("clawdeck."):
        return "Module"
    return "Entrypoint"


def write_api_index(stems: list[str]) -> None:
    """Write an index page within docs/api for pydoc's built-in nav link."""
    items = "\n".join(
        (
            "      <li>"
            f'<a href="{escape(stem)}.html">'
            f'<span class="label">{escape(title_from_stem(stem))}</span>'
            f'<span class="meta">{escape(category_from_stem(stem))}</span>'
            "</a>"
            "</li>"
        )
        for stem in stems
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ClawDeck API Index</title>
  <link rel="stylesheet" href="../pydoc.css">
</head>
<body class="docs-home">
  <section class="hero">
    <p class="eyebrow">ClawDeck</p>
    <h1>API Index</h1>
    <p>Browsable module documentation generated from <code>pydoc</code> and polished for GitHub Pages.</p>
    <div class="cta-row">
      <a class="cta primary" href="../index.html">Docs Home</a>
      <a class="cta secondary" href="clawdeck.html">Package Overview</a>
    </div>
  </section>
  <section class="module-list">
    <p>Generated pages in this build.</p>
    <ul>
{items}
    </ul>
  </section>
</body>
</html>
"""
    (API_DIR / "index.html").write_text(html, encoding="utf-8")


def write_docs_home() -> None:
    """Write the top-level GitHub Pages landing page."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ClawDeck API Docs</title>
  <link rel="stylesheet" href="pydoc.css">
</head>
<body class="docs-home">
  <section class="hero">
    <p class="eyebrow">ClawDeck</p>
    <h1>API Docs</h1>
    <p>Static <code>pydoc</code> output for GitHub Pages, with a cleaner landing page and styled module docs.</p>
    <div class="cta-row">
      <a class="cta primary" href="api/index.html">Browse All Pages</a>
      <a class="cta secondary" href="api/clawdeck.html">Package Overview</a>
      <a class="cta secondary" href="api/clawdeck.controller.html">Controller Module</a>
    </div>
  </section>
  <section class="module-list">
    <p>The docs site is regenerated with <code>make docs-pydoc</code>. The published Pages site serves the files directly from this repository’s <code>docs/</code> folder.</p>
  </section>
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    """Style the generated pydoc output in-place."""
    API_DIR.mkdir(parents=True, exist_ok=True)
    STYLESHEET_PATH.write_text(STYLESHEET, encoding="utf-8")

    pages = sorted(path for path in API_DIR.glob("*.html") if path.name != "index.html")
    stems = [path.stem for path in pages]

    for page in pages:
        style_api_page(page)

    write_api_index(stems)
    write_docs_home()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
