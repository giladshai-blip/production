"""
גנט ייצור שבועי → Google Sheets
שימוש: python gantt_sheets.py <קובץ_WMS.xlsx> [שם-גיליון]

אימות ראשוני:
  1. הורד credentials.json מ-Google Cloud Console (OAuth Desktop)
  2. הנח אותו באותה תיקייה עם הסקריפט
  3. בהרצה הראשונה — דפדפן ייפתח לאישור גישה
  הטוקן יישמר ב-~/.config/gspread/authorized_user.json לשימוש עתידי
"""

import sys
from datetime import datetime

import gspread
import pandas as pd

from daily_production import (
    load_wms, filter_and_prepare, _day_index,
    DAYS_HE, NUM_DAYS, COL_FIXED, TOTAL_COLS,
    COL_FAM, COL_FAM_NAME, COL_SKU, COL_DESC,
    COL_STOCK, COL_MIN, COL_DAYS_STOCK,
    C_ZERO, C_LOW, C_PLAN, C_TOTAL, C_GRAND,
    C_HEADER, C_TODAY_HDR, C_CAT,
)

# ─── עזרי צבע ───────────────────────────────────────────────────────────────

def _rgb(hex_color: str) -> dict:
    """FFRRGGBB → Sheets API RGB dict (0-1 scale)"""
    return {
        "red":   int(hex_color[2:4], 16) / 255,
        "green": int(hex_color[4:6], 16) / 255,
        "blue":  int(hex_color[6:8], 16) / 255,
    }

WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
BLACK = {"red": 0.0, "green": 0.0, "blue": 0.0}

# צבעי רקע שדורשים טקסט לבן
_WHITE_TEXT = {C_HEADER, C_TODAY_HDR, C_GRAND}


def _fg(bg_hex: str) -> dict:
    return WHITE if bg_hex in _WHITE_TEXT else BLACK


# ─── בוני בקשות Sheets API ──────────────────────────────────────────────────

def _cell_fmt(bg_hex=None, bold=False, size=10, halign="CENTER",
              number_pattern=None, fg_override=None):
    fmt = {
        "textFormat": {
            "bold": bold,
            "fontSize": size,
            "foregroundColor": fg_override or (BLACK if not bg_hex else _fg(bg_hex)),
            "fontFamily": "Arial",
        },
        "horizontalAlignment": halign,
        "verticalAlignment": "MIDDLE",
        "wrapStrategy": "WRAP",
    }
    if bg_hex:
        fmt["backgroundColor"] = _rgb(bg_hex)
    if number_pattern:
        fmt["numberFormat"] = {"type": "NUMBER", "pattern": number_pattern}
    return fmt


def _repeat(sid, r0, c0, r1, c1, **kw):
    return {
        "repeatCell": {
            "range": {
                "sheetId": sid,
                "startRowIndex": r0, "endRowIndex": r1,
                "startColumnIndex": c0, "endColumnIndex": c1,
            },
            "cell": {"userEnteredFormat": _cell_fmt(**kw)},
            "fields": "userEnteredFormat",
        }
    }


def _merge(sid, row, c0, c1):
    """mergeCells — c1 exclusive"""
    return {
        "mergeCells": {
            "range": {
                "sheetId": sid,
                "startRowIndex": row, "endRowIndex": row + 1,
                "startColumnIndex": c0, "endColumnIndex": c1,
            },
            "mergeType": "MERGE_ALL",
        }
    }


def _col_width(sid, col, px):
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": col, "endIndex": col + 1},
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def _row_height(sid, row, px):
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "ROWS",
                      "startIndex": row, "endIndex": row + 1},
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


# ─── בניית הגנט ─────────────────────────────────────────────────────────────

def build_sheet(df_need: pd.DataFrame, gc: gspread.Client, title: str = None) -> str:
    today         = datetime.now()
    weekday       = today.weekday()
    mapping       = {6: 0, 0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 0}
    today_day_idx = mapping[weekday]
    date_str      = today.strftime("%d/%m/%Y")
    week_num      = today.isocalendar()[1]

    if not title:
        title = f"גנט ייצור — שבוע {week_num} — {today.strftime('%Y%m%d')}"

    print(f"יוצר גיליון: {title}")
    spreadsheet = gc.create(title)
    ws  = spreadsheet.sheet1
    sid = ws.id

    data    = []   # 2D list of cell values
    reqs    = []   # repeatCell / other formatting requests
    merges  = []   # mergeCells requests

    def cur():
        return len(data) - 1  # 0-based index of last appended row

    # ── שורה 1: כותרת ─────────────────────────────────────────────────────
    hdr_text = f"תוכנית ייצור שבועית — שבוע {week_num}     {date_str}"
    data.append([hdr_text] + [""] * (TOTAL_COLS - 1))
    merges.append(_merge(sid, cur(), 0, TOTAL_COLS))
    reqs.append(_repeat(sid, cur(), 0, cur()+1, TOTAL_COLS,
                         bg_hex=C_HEADER, bold=True, size=12, halign="CENTER"))
    reqs.append(_row_height(sid, cur(), 42))

    # ── שורה 2: כותרות עמודות ─────────────────────────────────────────────
    col_headers = ["קטגוריה", "מק'ט", "תאור מוצר", "מלאי נוכחי"] + DAYS_HE + ['סה"כ']
    data.append(col_headers)
    # 4 עמודות קבועות
    reqs.append(_repeat(sid, cur(), 0, cur()+1, COL_FIXED,
                         bg_hex=C_HEADER, bold=True, size=10, halign="CENTER"))
    # 6 עמודות ימים — יום נוכחי מודגש
    for d in range(NUM_DAYS):
        bg = C_TODAY_HDR if d == today_day_idx else C_HEADER
        reqs.append(_repeat(sid, cur(), COL_FIXED+d, cur()+1, COL_FIXED+d+1,
                             bg_hex=bg, bold=True, size=10, halign="CENTER"))
    # עמודת סה"כ
    reqs.append(_repeat(sid, cur(), TOTAL_COLS-1, cur()+1, TOTAL_COLS,
                         bg_hex=C_HEADER, bold=True, size=10, halign="CENTER"))
    reqs.append(_row_height(sid, cur(), 30))

    # ── לולאת קבוצות ──────────────────────────────────────────────────────
    grand_day = {d: 0 for d in range(NUM_DAYS)}
    grand_tot  = 0

    for (fam_code, fam_name), grp in df_need.groupby([COL_FAM, COL_FAM_NAME], sort=True):

        # כותרת קטגוריה
        data.append([f"◆  {fam_name}  ({fam_code})"] + [""] * (TOTAL_COLS - 1))
        merges.append(_merge(sid, cur(), 0, TOTAL_COLS))
        reqs.append(_repeat(sid, cur(), 0, cur()+1, TOTAL_COLS,
                             bg_hex=C_CAT, bold=True, size=10, halign="RIGHT"))
        reqs.append(_row_height(sid, cur(), 26))

        fam_day = {d: 0 for d in range(NUM_DAYS)}
        fam_tot  = 0

        for _, item in grp.iterrows():
            stock   = int(item[COL_STOCK])
            min_s   = int(item[COL_MIN])
            boxes   = int(item["לייצור באריזות"])
            day_idx = _day_index(item[COL_DAYS_STOCK])

            bg = C_ZERO if stock == 0 else (C_LOW if stock < min_s else C_PLAN)

            day_vals = [""] * NUM_DAYS
            day_vals[day_idx] = boxes

            data.append([fam_name, str(item[COL_SKU]), item[COL_DESC], stock]
                        + day_vals + [boxes])
            ri = cur()

            # עמודות קבועות
            reqs.append(_repeat(sid, ri, 0, ri+1, 1,  bg_hex=bg, halign="RIGHT"))
            reqs.append(_repeat(sid, ri, 1, ri+1, 2,  bg_hex=bg, halign="CENTER"))
            reqs.append(_repeat(sid, ri, 2, ri+1, 3,  bg_hex=bg, halign="RIGHT"))
            reqs.append(_repeat(sid, ri, 3, ri+1, 4,  bg_hex=bg, bold=True,
                                 halign="CENTER", number_pattern="#,##0"))
            # עמודות ימים
            for d in range(NUM_DAYS):
                c = COL_FIXED + d
                if d == day_idx:
                    reqs.append(_repeat(sid, ri, c, ri+1, c+1, bg_hex=bg, bold=True,
                                         halign="CENTER", number_pattern="#,##0"))
                else:
                    reqs.append(_repeat(sid, ri, c, ri+1, c+1, halign="CENTER"))
            # סה"כ שורה
            reqs.append(_repeat(sid, ri, TOTAL_COLS-1, ri+1, TOTAL_COLS, bg_hex=bg,
                                 bold=True, halign="CENTER", number_pattern="#,##0"))

            fam_day[day_idx] += boxes;  fam_tot += boxes
            grand_day[day_idx] += boxes; grand_tot += boxes

        # שורת סה"כ משפחה
        fam_day_vals = [fam_day[d] if fam_day[d] > 0 else "" for d in range(NUM_DAYS)]
        data.append([f'סה"כ  {fam_name}', "", "", ""] + fam_day_vals + [fam_tot])
        ri = cur()
        merges.append(_merge(sid, ri, 0, COL_FIXED))
        reqs.append(_repeat(sid, ri, 0, ri+1, COL_FIXED,
                             bg_hex=C_TOTAL, bold=True, halign="RIGHT"))
        for d in range(NUM_DAYS):
            c = COL_FIXED + d
            reqs.append(_repeat(sid, ri, c, ri+1, c+1, bg_hex=C_TOTAL, bold=True,
                                 halign="CENTER", number_pattern="#,##0"))
        reqs.append(_repeat(sid, ri, TOTAL_COLS-1, ri+1, TOTAL_COLS, bg_hex=C_TOTAL,
                             bold=True, halign="CENTER", number_pattern="#,##0"))
        reqs.append(_row_height(sid, ri, 24))

    # ── שורת סה"כ כולל ────────────────────────────────────────────────────
    grand_vals = [grand_day[d] if grand_day[d] > 0 else "" for d in range(NUM_DAYS)]
    data.append(['סה"כ כולל', "", "", ""] + grand_vals + [grand_tot])
    ri = cur()
    merges.append(_merge(sid, ri, 0, COL_FIXED))
    reqs.append(_repeat(sid, ri, 0, ri+1, COL_FIXED,
                         bg_hex=C_GRAND, bold=True, halign="CENTER"))
    for d in range(NUM_DAYS):
        c = COL_FIXED + d
        reqs.append(_repeat(sid, ri, c, ri+1, c+1, bg_hex=C_GRAND, bold=True,
                             halign="CENTER", number_pattern="#,##0"))
    reqs.append(_repeat(sid, ri, TOTAL_COLS-1, ri+1, TOTAL_COLS, bg_hex=C_GRAND,
                         bold=True, halign="CENTER", number_pattern="#,##0"))
    reqs.append(_row_height(sid, ri, 32))

    # ── עדכון נתונים ──────────────────────────────────────────────────────
    end_col = chr(ord('A') + TOTAL_COLS - 1)   # 'K'
    ws.update(data, f"A1:{end_col}{len(data)}", value_input_option="USER_ENTERED")

    # ── עיצוב + הגדרות גיליון ─────────────────────────────────────────────
    col_widths_px = [155, 75, 225, 90, 72, 72, 72, 72, 72, 72, 85]

    spreadsheet.batch_update({"requests": [
        # RTL
        {"updateSheetProperties": {
            "properties": {"sheetId": sid, "rightToLeft": True},
            "fields": "rightToLeft",
        }},
        # הקפאת 2 שורות עליונות
        {"updateSheetProperties": {
            "properties": {
                "sheetId": sid,
                "gridProperties": {"frozenRowCount": 2},
            },
            "fields": "gridProperties.frozenRowCount",
        }},
        # AutoFilter משורה 2
        {"setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 1,
                    "endRowIndex": len(data),
                    "startColumnIndex": 0,
                    "endColumnIndex": TOTAL_COLS,
                }
            }
        }},
        # רוחב עמודות
        *[_col_width(sid, i, px) for i, px in enumerate(col_widths_px)],
        # מיזוגים לפני עיצוב
        *merges,
        # עיצוב תאים
        *reqs,
    ]})

    print(f"✅  נשמר: {spreadsheet.url}")
    return spreadsheet.url


# ─── אימות ──────────────────────────────────────────────────────────────────

def get_gc() -> gspread.Client:
    """
    מחזיר gspread client מאומת.
    מנסה OAuth (credentials.json) ואם לא קיים — service account.
    """
    import os
    from pathlib import Path

    sa_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_env and Path(sa_env).exists():
        return gspread.service_account(filename=sa_env)

    cred_file = Path("credentials.json")
    if cred_file.exists():
        return gspread.oauth(credentials_filename=str(cred_file))

    print("❌  לא נמצאו credentials.\n"
          "    אחת מהאפשרויות:\n"
          "    1. הנח credentials.json (OAuth Desktop) באותה תיקייה\n"
          "    2. הגדר GOOGLE_APPLICATION_CREDENTIALS לקובץ service-account JSON")
    sys.exit(1)


# ─── נקודת כניסה ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("שימוש: python gantt_sheets.py <קובץ_WMS.xlsx> [שם-גיליון]")
        sys.exit(1)

    input_path = sys.argv[1]
    sheet_name = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"טוען: {input_path}")
    df = load_wms(input_path)
    print(f"  סה\"כ שורות: {len(df)}")

    df_need = filter_and_prepare(df)
    print(f"  פריטים לייצור: {len(df_need)}")

    gc = get_gc()
    url = build_sheet(df_need, gc, title=sheet_name)
    print(f"\n🔗  {url}")


if __name__ == "__main__":
    main()
