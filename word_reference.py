"""產生 Pandoc --reference-doc 用的 Word 範本：微軟正黑體與固定字級。"""

from __future__ import annotations

from pathlib import Path

# 微軟正黑體（Word 內建名稱）
FONT = "Microsoft JhengHei"
# 內文
BODY_PT = 12
# 標題 1–6：字級（pt）、是否粗體
HEADING_SPECS: list[tuple[float, bool]] = [
    (22, True),  # H1
    (18, True),  # H2
    (16, True),  # H3
    (14, True),  # H4
    (13, False),  # H5
    (12, False),  # H6
]
# 程式碼區塊（等寬，仍維持可讀字級）
CODE_PT = 10
CODE_FONT = "Consolas"


def _set_style_font(style, font_name: str, size_pt: float, bold: bool = False) -> None:
    from docx.oxml.ns import qn
    from docx.shared import Pt

    style.font.name = font_name
    style.font.size = Pt(size_pt)
    style.font.bold = bold
    r_pr = style.element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), font_name)
    r_fonts.set(qn("w:hAnsi"), font_name)
    r_fonts.set(qn("w:eastAsia"), font_name)
    r_fonts.set(qn("w:cs"), font_name)


def _set_code_style_font(style, latin: str, east_asia: str, size_pt: float) -> None:
    """程式碼：拉丁用 Consolas，中文仍用正黑體避免缺字。"""
    from docx.oxml.ns import qn
    from docx.shared import Pt

    style.font.name = latin
    style.font.size = Pt(size_pt)
    style.font.bold = False
    r_pr = style.element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), latin)
    r_fonts.set(qn("w:hAnsi"), latin)
    r_fonts.set(qn("w:eastAsia"), east_asia)
    r_fonts.set(qn("w:cs"), latin)


def build_word_reference_docx(out_path: Path) -> None:
    """寫入一個最小 .docx，供 Pandoc 當 reference-doc。"""
    from docx import Document

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()

    _set_style_font(doc.styles["Normal"], FONT, BODY_PT, False)

    for i, (pt, bold) in enumerate(HEADING_SPECS, start=1):
        _set_style_font(doc.styles[f"Heading {i}"], FONT, pt, bold)

    # 清單段落
    try:
        _set_style_font(doc.styles["List Paragraph"], FONT, BODY_PT, False)
    except KeyError:
        pass

    # 引言
    try:
        _set_style_font(doc.styles["Quote"], FONT, BODY_PT, False)
    except KeyError:
        pass

    # 行內／區塊程式碼常用樣式（名稱依 Word 預設）
    for code_style_name in ("No Spacing", "Intense Quote"):
        try:
            _set_code_style_font(doc.styles[code_style_name], CODE_FONT, FONT, CODE_PT)
        except KeyError:
            pass

    doc.save(str(out_path))


def ensure_word_reference_docx(base_dir: Path) -> Path | None:
    """
    回傳 reference.docx 路徑；若不存在則用 python-docx 產生。
    若未安裝 python-docx 則回傳 None（匯出時改走僅 Pandoc 預設樣式）。
    """
    path = base_dir / "assets" / "word-reference.docx"
    if path.is_file():
        return path
    try:
        build_word_reference_docx(path)
    except ImportError:
        return None
    except Exception:
        return None
    return path if path.is_file() else None
