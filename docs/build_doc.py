"""기획서_v2.md → HTML(이미지 base64 임베드, 인쇄용 CSS) 변환."""
import base64
import re
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
md_text = (HERE / "기획서_v2.md").read_text("utf-8")

# 이미지 base64 임베드
def embed(m):
    alt, src = m.group(1), m.group(2)
    p = HERE / src
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f"![{alt}](data:image/png;base64,{b64})"
    return m.group(0)

md_text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", embed, md_text)

body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

CSS = """
@page { size: A4; margin: 16mm 15mm; }
* { box-sizing: border-box; }
body { font-family:'Malgun Gothic','맑은 고딕',sans-serif; color:#222; line-height:1.65;
  font-size:11pt; max-width:820px; margin:0 auto; padding:20px; }
h1 { font-size:19pt; border-bottom:3px solid #d6452b; padding-bottom:10px; color:#b8381f; }
h2 { font-size:14.5pt; margin-top:26px; color:#b8381f; border-left:5px solid #d6452b;
  padding-left:10px; }
h3 { font-size:12.5pt; margin-top:18px; color:#3a2a20; }
table { border-collapse:collapse; width:100%; margin:12px 0; font-size:10pt; }
th,td { border:1px solid #d8cdbe; padding:7px 9px; text-align:left; vertical-align:top; }
th { background:#f6ece0; }
img { max-width:100%; border:1px solid #e3d8c8; border-radius:8px; margin:10px 0;
  box-shadow:0 2px 8px rgba(0,0,0,.08); }
code { background:#f3efe8; padding:1px 5px; border-radius:4px; font-size:9.5pt; }
pre { background:#f7f3ec; border:1px solid #e3d8c8; border-radius:8px; padding:12px;
  overflow:auto; font-size:9.5pt; }
pre code { background:none; padding:0; }
h2 { page-break-after:avoid; } img { page-break-inside:avoid; }
strong { color:#a8341c; }
"""

html = f"""<!doctype html><html lang=ko><head><meta charset=utf-8>
<title>K-Food Match 기획서</title><style>{CSS}</style></head>
<body>{body}</body></html>"""

out = HERE / "기획서_v2.html"
out.write_text(html, encoding="utf-8")
print("saved", out)
