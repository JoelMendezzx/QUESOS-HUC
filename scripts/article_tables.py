"""
Extrae las tablas de artículos de acceso abierto (HTML de PMC o XML JATS de Europe PMC)
a CSV, sin dependencias externas. Conserva el texto de cada celda tal como está.

Uso: python scripts/article_tables.py <archivo.html|archivo.xml> <carpeta_salida>
"""
import csv
import html
import os
import re
import sys
from html.parser import HTMLParser


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.caps = [], []
        self._stack = []   # tablas anidadas
        self._cell = None
        self._cap = None
        self._last_cap = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "caption":
            self._cap = []
        elif tag == "table":
            self._stack.append(dict(rows=[], spans={}, cap=self._last_cap))
        elif tag == "tr" and self._stack:
            self._stack[-1]["rows"].append([])
        elif tag in ("td", "th") and self._stack:
            self._cell = dict(text=[], rs=int(a.get("rowspan", 1) or 1), cs=int(a.get("colspan", 1) or 1))
        elif tag in ("br",) and self._cell is not None:
            self._cell["text"].append(" ")

    def handle_endtag(self, tag):
        if tag == "caption" and self._cap is not None:
            self._last_cap = re.sub(r"\s+", " ", "".join(self._cap)).strip()
            self._cap = None
        elif tag in ("td", "th") and self._cell is not None and self._stack:
            t = self._stack[-1]
            if not t["rows"]:
                t["rows"].append([])
            row = t["rows"][-1]
            r_i = len(t["rows"]) - 1
            # saltar posiciones ocupadas por rowspan anteriores
            while (r_i, len(row)) in t["spans"]:
                row.append(t["spans"].pop((r_i, len(row))))
            txt = re.sub(r"\s+", " ", "".join(self._cell["text"])).strip()
            for k in range(self._cell["cs"]):
                c_i = len(row)
                row.append(txt)
                for dr in range(1, self._cell["rs"]):
                    t["spans"][(r_i + dr, c_i)] = txt
            self._cell = None
        elif tag == "tr" and self._stack:
            t = self._stack[-1]
            r_i = len(t["rows"]) - 1
            row = t["rows"][-1]
            while (r_i, len(row)) in t["spans"]:
                row.append(t["spans"].pop((r_i, len(row))))
        elif tag == "table" and self._stack:
            t = self._stack.pop()
            self.tables.append(t["rows"])
            self.caps.append(t["cap"])
            self._last_cap = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"].append(data)
        if self._cap is not None:
            self._cap.append(data)


def extract(path, outdir):
    raw = open(path, encoding="utf-8", errors="replace").read()
    if path.endswith(".xml"):  # JATS: <td>, <th>, <caption> ya tienen los mismos nombres
        raw = re.sub(r"<(/?)(label|title)>", "", raw)
    p = _TableParser()
    p.feed(raw)
    os.makedirs(outdir, exist_ok=True)
    out = []
    for i, (rows, cap) in enumerate(zip(p.tables, p.caps), start=1):
        fn = os.path.join(outdir, f"table_{i}.csv")
        with open(fn, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if cap:
                w.writerow([f"# CAPTION: {cap}"])
            for r in rows:
                w.writerow(r)
        out.append((fn, len(rows), cap))
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for fn, n, cap in extract(sys.argv[1], sys.argv[2]):
        print(f"{fn}: {n} filas | {(cap or '')[:120]}")
