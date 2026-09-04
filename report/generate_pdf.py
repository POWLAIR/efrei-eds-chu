#!/usr/bin/env python3
"""report/dossier.md  ->  report/dossier.pdf  (A4 multi-pages, design corporate).

Charte reprise du skill `rapport-performance-pdf` (~/projets/.claude/skills), adaptée
à un dossier multi-pages : parseur Markdown générique (markdown-it-py) -> flowables
ReportLab. Boucle de contrôle visuel via pymupdf en option (`--qa`).
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE = Path(__file__).parent
MD = BASE / "dossier.md"
PDF = BASE / "dossier.pdf"

# --- Charte (identique au skill) --------------------------------------------
INK = colors.HexColor("#1a1f36")
MUTED = colors.HexColor("#6b7280")
ACCENT = colors.HexColor("#0052cc")
ACCENT_SOFT = colors.HexColor("#eaf1ff")
OK = colors.HexColor("#00875a")
LINE = colors.HexColor("#e4e7ec")
ROW_ALT = colors.HexColor("#fafbfc")
HEAD_BG = colors.HexColor("#f1f4f9")
WHITE = colors.white

CONTENT_W = 180 * mm
FOOTER = "EDS CHU · Dossier — Épreuve Big Data M2 · E05"


def styles() -> dict:
    b = getSampleStyleSheet()

    def s(name, **kw):
        return ParagraphStyle(name, parent=b["Normal"], **kw)

    return {
        "title": s("title", fontName="Helvetica-Bold", fontSize=20, textColor=WHITE, leading=24),
        "badge": s("badge", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#bcd3ff")),
        "sub": s("sub", fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#dce8ff"), leading=14),
        "h1": s("h1", fontName="Helvetica-Bold", fontSize=15, textColor=ACCENT, spaceBefore=6, spaceAfter=8),
        "h2": s("h2", fontName="Helvetica-Bold", fontSize=12.5, textColor=ACCENT, spaceBefore=14, spaceAfter=6),
        "h3": s("h3", fontName="Helvetica-Bold", fontSize=10.5, textColor=INK, spaceBefore=9, spaceAfter=4),
        "body": s("body", fontName="Helvetica", fontSize=9.2, textColor=INK, leading=13.5, spaceAfter=5, alignment=TA_LEFT),
        "li": s("li", fontName="Helvetica", fontSize=9.2, textColor=INK, leading=13),
        "quote": s("quote", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#334155"), leading=13.5),
        "code": s("code", fontName="Courier", fontSize=8, textColor=colors.HexColor("#334155"), leading=11),
        "th": s("th", fontName="Helvetica-Bold", fontSize=7.5, textColor=colors.HexColor("#44506a"), leading=10),
        "td": s("td", fontName="Helvetica", fontSize=8, textColor=INK, leading=10.5),
        "kpi_v": s("kpi_v", fontName="Helvetica-Bold", fontSize=16, textColor=INK, alignment=TA_CENTER, leading=19),
        "kpi_l": s("kpi_l", fontName="Helvetica", fontSize=6.8, textColor=MUTED, alignment=TA_CENTER, leading=9),
        "caption": s("caption", fontName="Helvetica-Oblique", fontSize=8, textColor=MUTED, alignment=TA_CENTER, spaceBefore=2, spaceAfter=8),
        "footer": s("footer", fontName="Helvetica", fontSize=7.5, textColor=MUTED, alignment=TA_CENTER),
    }


ST = styles()

# --- Rendu de l'inline (Markdown -> mini-HTML ReportLab) --------------------
def inline(tok) -> str:
    out = []
    for c in tok.children or []:
        t = c.type
        if t == "text":
            out.append(html.escape(c.content))
        elif t == "code_inline":
            out.append(f'<font face="Courier" size=8>{html.escape(c.content)}</font>')
        elif t == "strong_open":
            out.append("<b>")
        elif t == "strong_close":
            out.append("</b>")
        elif t == "em_open":
            out.append("<i>")
        elif t == "em_close":
            out.append("</i>")
        elif t == "softbreak":
            out.append(" ")  # CommonMark : un retour à la ligne simple = une espace
        elif t == "hardbreak":
            out.append("<br/>")
        elif t == "link_open":
            href = dict(c.attrs).get("href", "")
            out.append(f'<font color="#0052cc">{html.escape(href) if False else ""}')
        elif t == "link_close":
            out.append("</font>")
        elif t == "image":
            out.append("")  # géré au niveau bloc
    return "".join(out).strip()


def split_images(tok):
    """(liste (src, alt), texte_restant) pour un paragraphe éventuellement mixte image+texte."""
    imgs, text_children = [], []
    for c in tok.children or []:
        if c.type == "image":
            imgs.append((dict(c.attrs).get("src", ""), c.content or ""))
        else:
            text_children.append(c)  # softbreak/hardbreak compris (gérés par inline())
    clone = type(tok)("inline", "", 0)
    clone.children = text_children
    return imgs, inline(clone)


# --- Bandeau de titre -------------------------------------------------------
def header_band(title: str, subtitle: str) -> Table:
    inner = Table(
        [
            [Paragraph("ÉPREUVE E05 · BIG DATA M2 · ARCHITECTURE DE DONNÉES", ST["badge"])],
            [Paragraph(title, ST["title"])],
            [Spacer(1, 4)],
            [Paragraph(subtitle, ST["sub"])],
        ],
        colWidths=[CONTENT_W - 28],
    )
    inner.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    outer = Table([[inner]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 18), ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("ROUNDEDCORNERS", [7, 7, 7, 7]),
    ]))
    return outer


def kpi_strip(pairs: list[tuple[str, str]]) -> Table:
    n = len(pairs)
    col_w = CONTENT_W / n
    top = [Paragraph(v, ST["kpi_v"]) for _, v in pairs]
    bot = [Paragraph(k.upper(), ST["kpi_l"]) for k, _ in pairs]
    t = Table([top, bot], colWidths=[col_w] * n)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 11), ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 1), (-1, 1), 11),
    ]
    for c in range(1, n):
        cmds.append(("LINEBEFORE", (c, 0), (c, -1), 0.5, LINE))
    t.setStyle(TableStyle(cmds))
    return t


def md_table(header: list[str], rows: list[list[str]]) -> Table:
    ncol = len(header)
    data = [[Paragraph(h, ST["th"]) for h in header]]
    for r in rows:
        data.append([Paragraph(c, ST["td"]) for c in r])
    w = CONTENT_W / ncol
    t = Table(data, colWidths=[w] * ncol, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(2, len(data), 2):
        cmds.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    t.setStyle(TableStyle(cmds))
    return t


def callout(text_html: str):
    inner = Paragraph(text_html, ST["quote"])
    t = Table([[inner]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_SOFT),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


# Hauteur max par figure. Défaut volontairement modéré pour qu'une figure tienne
# dans le bas d'une page courante ; on ajuste au cas par cas : schéma ER dense =
# plus de place, captures d'écran peu denses = moins.
_MAX_H = {
    "silver.png": 122 * mm,
    "01-cloisonnement-recherche.png": 92 * mm,
    "02-rbac-clickhouse-denied.png": 96 * mm,
}
_MAX_H_DEFAULT = 114 * mm


def scaled_image(src: str) -> Image | None:
    p = (BASE / src).resolve()
    if not p.exists():
        print(f"  ⚠ image absente : {p}", file=sys.stderr)
        return None
    img = Image(str(p))
    ratio = img.imageHeight / img.imageWidth
    max_w = CONTENT_W
    max_h = _MAX_H.get(Path(src).name, _MAX_H_DEFAULT)
    w = min(max_w, img.imageWidth)
    h = w * ratio
    if h > max_h:
        h = max_h
        w = h / ratio
    img.drawWidth, img.drawHeight = w, h
    return img


def _section_has_image(tokens, start: int, level: str) -> bool:
    """Une image apparaît-elle dans la section (jusqu'au prochain titre de niveau <= `level`) ?"""
    for j in range(start, len(tokens)):
        t = tokens[j]
        if t.type == "heading_open" and t.tag <= level:  # h2 <= h2, h2 <= h3 est faux
            return False
        if t.type == "inline" and any(c.type == "image" for c in t.children or []):
            return True
    return False


# --- Parcours des tokens ---------------------------------------------------
def build_story(md_text: str) -> list:
    md = MarkdownIt("commonmark").enable("table").enable("strikethrough")
    tokens = md.parse(md_text)

    story: list = []
    title, subtitle = "Entrepôt de Données de Santé du CHU", ""
    i = 0
    got_title = False
    list_stack: list[list] = []

    while i < len(tokens):
        tok = tokens[i]
        tt = tok.type

        if tt == "heading_open":
            content = inline(tokens[i + 1])
            lvl = tok.tag  # h1..h6
            if lvl == "h1" and not got_title:
                title = re.sub("<[^>]+>", "", content)
                got_title = True
                # sous-titre = paragraphe qui suit immédiatement le titre, s'il existe
                nxt = i + 3
                if nxt < len(tokens) and tokens[nxt].type == "paragraph_open":
                    subtitle = re.sub("<[^>]+>", "", inline(tokens[nxt + 1]))
                    i = nxt + 3
                else:
                    i = nxt
                story.insert(0, header_band(title, subtitle))
                story.insert(1, Spacer(1, 16))
                continue
            style = {"h1": "h1", "h2": "h2", "h3": "h3"}.get(lvl, "h3")
            heading = Paragraph(content, ST[style])
            i += 3

            # Le titre reste solidaire de sa figure (jamais de titre seul en bas de
            # page, jamais de figure orpheline) ; le paragraphe descriptif SOUS la
            # figure, lui, coule librement -> il remplit le bas de page.
            block: list = [heading]
            trailing: list = []
            if i < len(tokens) and tokens[i].type == "paragraph_open":
                imgs, txt = split_images(tokens[i + 1])
                for src, alt in imgs:
                    flow = scaled_image(src)
                    if flow:
                        block.append(flow)
                        if alt:
                            block.append(Paragraph(html.escape(alt), ST["caption"]))
                if txt:
                    (trailing if imgs else block).append(
                        Paragraph(txt, ST["caption"] if imgs else ST["body"])
                    )
                if imgs or txt:
                    i += 3

            # Réserve courte : juste de quoi éviter un titre en dernière ligne.
            # Le KeepTogether ci-dessous fait le vrai travail anti-coupure.
            reserve = 40 * mm if _section_has_image(tokens, i, lvl) else 30 * mm
            story.append(CondPageBreak(reserve))
            story.append(KeepTogether(block) if len(block) > 1 else heading)
            story.extend(trailing)
            continue

        if tt == "paragraph_open":
            child = tokens[i + 1]
            imgs, txt = split_images(child)
            for src, alt in imgs:
                flow = scaled_image(src)
                if flow:
                    story.append(flow)
                    if alt:
                        story.append(Paragraph(html.escape(alt), ST["caption"]))
            if txt:
                target = list_stack[-1] if list_stack else story
                target.append(Paragraph(txt, ST["caption"] if imgs else ST["body"]))
            i += 3
            continue

        if tt in ("bullet_list_open", "ordered_list_open"):
            list_stack.append([])
            i += 1
            continue
        if tt in ("bullet_list_close", "ordered_list_close"):
            items = list_stack.pop()
            bullet = "bullet" if tt == "bullet_list_close" else "1"
            lf = ListFlowable(
                [ListItem(it, leftIndent=6) for it in items],
                bulletType=bullet, bulletColor=ACCENT, bulletFontSize=7,
                leftIndent=12, spaceBefore=2, spaceAfter=6,
            )
            (list_stack[-1] if list_stack else story).append(lf)
            i += 1
            continue
        if tt == "list_item_open":
            # le contenu (paragraph inline) est capté par paragraph_open -> list_stack[-1]
            i += 1
            continue
        if tt == "list_item_close":
            i += 1
            continue

        if tt == "blockquote_open":
            # concatène les paragraphes internes
            j = i + 1
            parts = []
            while j < len(tokens) and tokens[j].type != "blockquote_close":
                if tokens[j].type == "inline":
                    parts.append(inline(tokens[j]))
                j += 1
            story.append(callout("<br/>".join(parts)))
            story.append(Spacer(1, 4))
            i = j + 1
            continue

        if tt == "hr":
            story.append(PageBreak())
            i += 1
            continue

        if tt == "fence":
            if (tok.info or "").strip() == "kpi":
                pairs = []
                for line in tok.content.strip().splitlines():
                    if "|" in line:
                        k, v = line.split("|", 1)
                        pairs.append((k.strip(), v.strip()))
                if pairs:
                    story.append(kpi_strip(pairs))
                    story.append(Spacer(1, 8))
            else:
                for line in tok.content.rstrip().splitlines() or [""]:
                    story.append(Paragraph(html.escape(line) or "&nbsp;", ST["code"]))
                story.append(Spacer(1, 6))
            i += 1
            continue

        if tt == "table_open":
            header: list[str] = []
            rows: list[list[str]] = []
            cur: list[str] = []
            in_head = False
            j = i + 1
            while j < len(tokens) and tokens[j].type != "table_close":
                tj = tokens[j].type
                if tj == "thead_open":
                    in_head = True
                elif tj == "thead_close":
                    in_head = False
                elif tj == "tr_open":
                    cur = []
                elif tj == "tr_close":
                    if in_head:
                        header = cur
                    else:
                        rows.append(cur)
                elif tj == "inline":
                    cur.append(inline(tokens[j]))
                j += 1
            story.append(md_table(header, rows))
            story.append(Spacer(1, 8))
            i = j + 1
            continue

        i += 1

    return story


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"{FOOTER}  ·  page {canvas.getPageNumber()}")
    canvas.restoreState()


def main() -> None:
    story = build_story(MD.read_text(encoding="utf-8"))
    doc = SimpleDocTemplate(
        str(PDF), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
        title="EDS CHU — Dossier E05",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(PDF)

    if "--qa" in sys.argv:
        import fitz  # pymupdf

        pdf = fitz.open(str(PDF))
        print(f"  {pdf.page_count} pages")
        for n in range(pdf.page_count):
            pix = pdf[n].get_pixmap(dpi=110)
            out = BASE / f"_qa_p{n + 1}.png"
            pix.save(str(out))
            print(f"  QA -> {out}")


if __name__ == "__main__":
    main()
