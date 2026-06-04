"""
Build the installer's Quick Start Guide (Guide.html) from docs/USER_GUIDE.md.

The installer's "View Quick Start Guide" action opens this page in the user's
default browser: properly rendered headings, tables, callouts, and confidence
badges with subtle Darksquare branding — no Markdown viewer required, fully
offline (inline CSS, no external resources).

Screenshots referenced as assets/guide/<name>.png are used if present. Any
that are missing are replaced at build time with a clean styled placeholder,
so the page always looks finished. Drop real screenshots into assets/guide/
and rebuild to swap them in.

Run automatically by build_installer.bat, or manually:
    python installer/make_guide_html.py
"""

import html as _html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SRC = os.path.join(ROOT, "docs", "USER_GUIDE.md")
DEST = os.path.join(ROOT, "Guide.html")

_CSS = """
:root { --accent:#7c3aed; --accent-dark:#5b21b6; --ink:#1f2330; --muted:#5b6472;
        --line:#e3e6ec; --code-bg:#f5f6f9; }
* { box-sizing:border-box; }
body { margin:0; background:#fafbfc; color:var(--ink);
       font-family:"Segoe UI",-apple-system,system-ui,Arial,sans-serif; line-height:1.65; }
.banner { background:linear-gradient(135deg,var(--accent),var(--accent-dark));
          color:#fff; padding:30px 40px; }
.banner h1 { margin:0; font-size:25px; font-weight:700; letter-spacing:.2px; }
.banner p { margin:5px 0 0; opacity:.9; font-size:14px; }
main { max-width:860px; margin:0 auto; padding:8px 40px 64px; }
h2 { font-size:21px; border-bottom:2px solid var(--line); padding-bottom:6px;
     color:var(--accent-dark); margin-top:2em; }
h3 { font-size:17px; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
p,li { font-size:15px; }
code { background:var(--code-bg); padding:2px 6px; border-radius:4px;
       font-family:"Cascadia Code",Consolas,"Courier New",monospace; font-size:13px; }
pre { background:var(--code-bg); padding:14px 16px; border-radius:8px;
      border:1px solid var(--line); overflow-x:auto; }
table { border-collapse:collapse; width:100%; margin:16px 0; font-size:14px; }
th,td { border:1px solid var(--line); padding:9px 13px; text-align:left; vertical-align:top; }
th { background:#f0ecfb; color:var(--accent-dark); font-weight:600; }
tr:nth-child(even) td { background:#fafafe; }
hr { border:none; border-top:1px solid var(--line); margin:30px 0; }
ol li, ul li { margin:5px 0; }
/* callouts */
.note,.tip { margin:18px 0; padding:12px 16px; border-radius:8px; font-size:14.5px; }
.note { background:#f7f5fd; border-left:4px solid var(--accent); }
.tip  { background:#eefbf3; border-left:4px solid #16a34a; }
/* confidence badges */
.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:13px;
         font-weight:600; white-space:nowrap; }
.badge.high { background:#dcfce7; color:#15803d; }
.badge.med  { background:#fef9c3; color:#a16207; }
.badge.low  { background:#fee2e2; color:#b91c1c; }
/* screenshots */
figure { margin:22px 0; }
figure img { width:100%; border:1px solid var(--line); border-radius:10px;
             box-shadow:0 2px 10px rgba(20,20,40,.08); display:block; }
figcaption { color:var(--muted); font-size:13px; margin-top:7px; text-align:center; }
.shot-missing { border:2px dashed #c9c2e8; border-radius:10px; background:#f7f5fd;
                color:var(--accent-dark); text-align:center; padding:34px 20px; font-size:14px; }
.shot-missing .ico { font-size:26px; display:block; margin-bottom:6px; opacity:.7; }
footer { max-width:860px; margin:0 auto; padding:0 40px 48px; color:var(--muted); font-size:13px; }
"""

_BANNER = (
    '<div class="banner">'
    '<h1>Markwell — Quick Start Guide</h1>'
    '<p>by Darksquare &middot; darksquare.dev</p>'
    '</div>'
)

_FOOTER = (
    '<footer><hr>Darksquare &middot; '
    '<a href="https://darksquare.dev">darksquare.dev</a> &middot; '
    'darksquare.ai@gmail.com</footer>'
)

_IMG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
_SRC_RE = re.compile(r'src="([^"]*)"')
_ALT_RE = re.compile(r'alt="([^"]*)"')


def _resolve_images(html_body: str) -> tuple[str, int, int]:
    """Wrap present screenshots in <figure>; replace missing ones with a placeholder."""
    present = [0]
    missing = [0]

    def repl(m):
        tag = m.group(0)
        src_m = _SRC_RE.search(tag)
        alt_m = _ALT_RE.search(tag)
        src = src_m.group(1) if src_m else ""
        alt = alt_m.group(1) if alt_m else ""
        disk_path = os.path.join(ROOT, src.replace("/", os.sep))
        if src and os.path.isfile(disk_path):
            present[0] += 1
            return f'<figure>{tag}<figcaption>{alt}</figcaption></figure>'
        missing[0] += 1
        return (f'<figure><div class="shot-missing">'
                f'<span class="ico">&#128247;</span>{_html.escape(alt)}</div>'
                f'<figcaption>Screenshot placeholder</figcaption></figure>')

    return _IMG_RE.sub(repl, html_body), present[0], missing[0]


def main():
    with open(SRC, encoding="utf-8") as fh:
        md_text = fh.read()

    try:
        import markdown
        body = markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code", "sane_lists", "md_in_html", "attr_list"],
        )
    except Exception as e:
        body = "<pre>" + _html.escape(md_text) + "</pre>"
        print(f"  WARNING: python-markdown unavailable ({e}); wrote <pre> fallback.")

    body, present, missing = _resolve_images(body)

    doc = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Markwell — Quick Start Guide</title>\n"
        "<style>" + _CSS + "</style>\n</head>\n<body>\n"
        + _BANNER + "\n<main>\n" + body + "\n</main>\n" + _FOOTER
        + "\n</body>\n</html>\n"
    )

    with open(DEST, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"  Wrote {DEST} ({len(doc):,} bytes)")
    print(f"  Screenshots: {present} present, {missing} placeholder(s)")


if __name__ == "__main__":
    main()
