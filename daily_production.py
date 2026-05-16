"""
תוכנית ייצור יומית — מעבד קובץ WMS ומייצר גיליון Excel יומי.
"""

import sys
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import (
    Alignment, Border, Font, PatternFill, Side
)
from openpyxl.utils import get_column_letter
import pandas as pd

# ─── קבועים ────────────────────────────────────────────────────────────────
UNITS_PER_CART = 10

# צבעי רקע
C_ZERO   = "FFFF0000"   # אדום  — אין מלאי
C_LOW    = "FFFFA500"   # כתום  — מתחת למינימום
C_PLAN   = "FFFFFF00"   # צהוב  — תכנון
C_TOTAL  = "FF92D050"   # ירוק  — סה"כ משפחה
C_GRAND  = "FF4472C4"   # כחול  — סה"כ כולל
C_HEADER = "FF203864"   # כחול כהה — כותרת ראשית
C_CAT    = "FFD9E1F2"   # תכלת  — כותרת קטגוריה

FONT_WHITE = Font(name="Arial", bold=True, color="FFFFFFFF", size=11)
FONT_BOLD  = Font(name="Arial", bold=True, size=10)
FONT_REG   = Font(name="Arial", size=10)

THIN = Side(style="thin", color="FF000000")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
RIGHT  = Alignment(horizontal="right",  vertical="center", wrap_text=True)

# עמודות קובץ WMS
COL_FAM      = "משפחה"
COL_FAM_NAME = "תאור משפחה"
COL_SKU      = "מק\"ט"
COL_DESC     = "תאור מוצר"
COL_STOCK    = "מלאי מרלוג ביח'"
COL_MIN      = "מינימום מלאי"        # אופציונלי — ייתכן שאין
COL_DIFF_U   = "הפרש לייצור ביחידות"
COL_DIFF_B   = "הפרש לייצור באריזות"

DAYS_HE = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"]


# ─── פונקציות עזר ───────────────────────────────────────────────────────────

def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)


def _style_cell(cell, value, font=None, fill=None, alignment=None, border=True, number_format=None):
    cell.value = value
    if font:
        cell.font = font
    if fill:
        cell.fill = fill
    if alignment:
        cell.alignment = alignment
    if border:
        cell.border = BORDER
    if number_format:
        cell.number_format = number_format


def _merge_and_style(ws, row, col_start, col_end, value, font, fill, alignment=None):
    ws.merge_cells(
        start_row=row, start_column=col_start,
        end_row=row, end_column=col_end
    )
    cell = ws.cell(row=row, column=col_start)
    _style_cell(cell, value, font=font, fill=fill, alignment=alignment or CENTER)
    # גבולות לתאים הממוזגים
    for c in range(col_start, col_end + 1):
        ws.cell(row=row, column=c).border = BORDER


# ─── טעינת נתונים ───────────────────────────────────────────────────────────

def load_wms(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, dtype={COL_FAM: str, COL_SKU: str})
    required = [COL_FAM, COL_FAM_NAME, COL_SKU, COL_DESC, COL_DIFF_U, COL_DIFF_B]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"עמודות חסרות בקובץ WMS: {missing}")
    return df


def filter_and_prepare(df: pd.DataFrame) -> pd.DataFrame:
    # שמור רק פריטים שחסרים לייצור
    df_need = df[df[COL_DIFF_U] < 0].copy()
    # המר הפרשים לערכים חיוביים
    df_need["לייצור ביחידות"] = df_need[COL_DIFF_U].abs()
    df_need["לייצור באריזות"] = df_need[COL_DIFF_B].abs()
    # מלאי ומינימום — ברירות מחדל אם עמודות חסרות
    if COL_STOCK not in df_need.columns:
        df_need[COL_STOCK] = 0
    if COL_MIN not in df_need.columns:
        df_need[COL_MIN] = 0
    df_need[COL_STOCK] = pd.to_numeric(df_need[COL_STOCK], errors="coerce").fillna(0)
    df_need[COL_MIN]   = pd.to_numeric(df_need[COL_MIN],   errors="coerce").fillna(0)
    return df_need


# ─── בניית Excel ─────────────────────────────────────────────────────────────

def build_excel(df_need: pd.DataFrame, output_path: str) -> str:
    today    = datetime.now()
    weekday  = today.weekday()   # 0=Mon … 5=Sat … 6=Sun
    # ממפה: Python weekday → יום עברי (א=0 בפייתון זה יום ב)
    # weekday(): Mon=0,Tue=1,Wed=2,Thu=3,Fri=4,Sat=5,Sun=6
    # ימי עבודה: א(Sun=6),ב(Mon=0),ג(Tue=1),ד(Wed=2),ה(Thu=3),ו(Fri=4)
    mapping = {6: 0, 0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 0}  # שבת → ראשון
    day_name = DAYS_HE[mapping[weekday]]
    date_str = today.strftime("%d/%m/%Y")
    week_num = today.isocalendar()[1]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"ייצור {today.strftime('%Y%m%d')}"
    ws.sheet_view.rightToLeft = True

    # ─── שורה 1: כותרת ראשית ───────────────────────────────────────────────
    COLS = 6
    title_text = f"תוכנית ייצור יומית — {day_name}  {date_str}     שבוע {week_num}"
    _merge_and_style(ws, 1, 1, COLS, title_text,
                     font=FONT_WHITE, fill=_fill(C_HEADER))
    ws.row_dimensions[1].height = 28

    # ─── שורה 2: כותרות עמודות ─────────────────────────────────────────────
    headers = ["קטגוריה", "מק\"ט", "תאור מוצר", "מלאי נוכחי", "אריזות לייצור", "עגלות"]
    col_widths = [22, 10, 32, 14, 16, 10]
    for i, (h, w) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=2, column=i)
        _style_cell(cell, h, font=FONT_WHITE, fill=_fill(C_HEADER),
                    alignment=CENTER)
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[2].height = 22

    row = 3
    grand_boxes = 0
    grand_carts = 0

    groups = df_need.groupby([COL_FAM, COL_FAM_NAME], sort=True)

    for (fam_code, fam_name), grp in groups:
        # ─── כותרת קטגוריה ─────────────────────────────────────────────────
        cat_text = f"◆  {fam_name}  ({fam_code})"
        _merge_and_style(ws, row, 1, COLS, cat_text,
                         font=Font(name="Arial", bold=True, size=10),
                         fill=_fill(C_CAT))
        ws.row_dimensions[row].height = 20
        row += 1

        fam_boxes = 0

        for _, item in grp.iterrows():
            stock    = int(item[COL_STOCK])
            min_s    = int(item[COL_MIN])
            boxes    = int(item["לייצור באריזות"])
            carts    = boxes // UNITS_PER_CART

            if stock == 0:
                row_color = C_ZERO
            elif stock < min_s:
                row_color = C_LOW
            else:
                row_color = C_PLAN

            fill = _fill(row_color)
            vals = [
                fam_name,
                item[COL_SKU],
                item[COL_DESC],
                stock,
                boxes,
                carts,
            ]
            fmts = [None, None, None, "#,##0", "#,##0", "#,##0"]
            fonts = [FONT_REG, FONT_REG, FONT_REG, FONT_BOLD, FONT_BOLD, FONT_BOLD]
            aligns = [RIGHT, CENTER, RIGHT, CENTER, CENTER, CENTER]

            for col_i, (v, fmt, fnt, aln) in enumerate(zip(vals, fmts, fonts, aligns), start=1):
                cell = ws.cell(row=row, column=col_i)
                _style_cell(cell, v, font=fnt, fill=fill,
                            alignment=aln, number_format=fmt)

            fam_boxes += boxes
            row += 1

        # ─── שורת סה"כ משפחה ───────────────────────────────────────────────
        fam_carts = fam_boxes // UNITS_PER_CART
        grand_boxes += fam_boxes
        grand_carts += fam_carts

        total_label = f"סה\"כ  {fam_name}"
        _merge_and_style(ws, row, 1, 3, total_label,
                         font=FONT_BOLD, fill=_fill(C_TOTAL), alignment=RIGHT)
        for col_i, val in [(4, ""), (5, fam_boxes), (6, fam_carts)]:
            cell = ws.cell(row=row, column=col_i)
            _style_cell(cell, val, font=FONT_BOLD, fill=_fill(C_TOTAL),
                        alignment=CENTER, number_format="#,##0")
        ws.row_dimensions[row].height = 18
        row += 1

    # ─── שורת סה"כ כולל ────────────────────────────────────────────────────
    _merge_and_style(ws, row, 1, 4, "סה\"כ כולל",
                     font=FONT_WHITE, fill=_fill(C_GRAND), alignment=CENTER)
    for col_i, val in [(5, grand_boxes), (6, grand_carts)]:
        cell = ws.cell(row=row, column=col_i)
        _style_cell(cell, val, font=FONT_WHITE, fill=_fill(C_GRAND),
                    alignment=CENTER, number_format="#,##0")
    ws.row_dimensions[row].height = 22
    row += 1

    # ─── AutoFilter ────────────────────────────────────────────────────────
    ws.auto_filter.ref = f"A2:{get_column_letter(COLS)}{row - 1}"

    # הקפא שורת כותרות
    ws.freeze_panes = "A3"

    wb.save(output_path)
    return output_path


# ─── נקודת כניסה ─────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("שימוש: python daily_production.py <קובץ_WMS.xlsx> [קובץ_פלט.xlsx]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else (
        Path(input_path).stem + f"_ייצור_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

    print(f"טוען: {input_path}")
    df = load_wms(input_path)
    print(f"  סה\"כ שורות: {len(df)}")

    df_need = filter_and_prepare(df)
    print(f"  פריטים לייצור: {len(df_need)}")

    out = build_excel(df_need, output_path)
    print(f"✅  נשמר: {out}")


if __name__ == "__main__":
    main()
