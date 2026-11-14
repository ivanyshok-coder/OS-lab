#!/usr/bin/env python3
"""Собирает report.docx из REPORT.md (заголовки, абзацы, таблицы, код, картинки).
Запуск (в папке, где лежат REPORT.md и results/): pip install python-docx ; python build_docx.py
"""
import os, re, sys
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

SRC = sys.argv[1] if len(sys.argv) > 1 else "REPORT.md"
DST = sys.argv[2] if len(sys.argv) > 2 else "report.docx"

doc = Document()
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(12)
for s in doc.sections:
    s.left_margin = Cm(3); s.right_margin = Cm(1.5); s.top_margin = Cm(2); s.bottom_margin = Cm(2)

def add_runs(par, text):
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if part:
            r = par.add_run(part); r.bold = (i % 2 == 1)

lines = open(SRC, encoding="utf-8").read().split("\n")
i = 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("```"):
        i += 1; code = []
        while i < len(lines) and not lines[i].startswith("```"):
            code.append(lines[i]); i += 1
        p = doc.add_paragraph(); r = p.add_run("\n".join(code)); r.font.name = "Consolas"; r.font.size = Pt(9)
    elif ln.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells): rows.append(cells)
            i += 1
        t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"
        for ri, row in enumerate(rows):
            for ci, c in enumerate(row):
                cell = t.cell(ri, ci); cell.text = ""
                run = cell.paragraphs[0].add_run(c); run.font.size = Pt(10); run.bold = (ri == 0)
        doc.add_paragraph(); continue
    elif ln.startswith("!["):
        m = re.match(r"!\[(.*?)\]\((.*?)\)", ln)
        if m and os.path.exists(m.group(2)):
            doc.add_picture(m.group(2), width=Cm(15)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c = doc.add_paragraph(f"Рисунок. {m.group(1)}"); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            doc.add_paragraph(f"[Нет файла {m.group(2) if m else ln} — вставьте график вручную]")
    elif ln.startswith("#"):
        lvl = len(ln) - len(ln.lstrip("#")); doc.add_heading(ln.lstrip("#").strip(), level=min(lvl, 4))
    elif re.match(r"\d+\. ", ln):
        add_runs(doc.add_paragraph(style="List Number"), re.sub(r"^\d+\. ", "", ln))
    elif ln.strip():
        add_runs(doc.add_paragraph(), ln)
    i += 1
doc.save(DST); print("Готово:", DST)
