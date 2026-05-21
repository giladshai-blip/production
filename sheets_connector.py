"""
חיבור לגוגל שיט — כל מתכון = גליון נפרד.

מבנה כל גליון:
  A1: "רכיב"   B1: "יחס"
  A2: רכיב 1  B2: יחס 1
  ...

מידע הגדרות (שם מתכון, סה"כ ק"ג) נשמר בגליון "_הגדרות":
  A: שם מתכון   B: סה"כ ק"ג
"""

import json
from pathlib import Path

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SPREADSHEET_NAME = "מחשבון יחסי מתכון"
CONFIG_FILE      = Path("google_config.json")
TOKEN_FILE       = Path("google_token.json")
SECRETS_FILE     = Path("client_secrets.json")
SETTINGS_SHEET   = "_הגדרות"

COL_RECIPE   = "מתכון"
COL_TOTAL_KG = 'סה"כ ק"ג'
HDR_ING      = "רכיב"
HDR_RATIO    = "יחס"


# ─── אימות ───────────────────────────────────────────────────────────────────

def _get_credentials() -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(SECRETS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def connect() -> gspread.Client:
    """מחזיר gspread Client מאומת."""
    return gspread.authorize(_get_credentials())


# ─── ניהול הספרדשיט ──────────────────────────────────────────────────────────

def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def get_or_create_spreadsheet(client: gspread.Client) -> gspread.Spreadsheet:
    cfg = _load_config()
    if "spreadsheet_id" in cfg:
        try:
            return client.open_by_key(cfg["spreadsheet_id"])
        except gspread.exceptions.SpreadsheetNotFound:
            pass

    # צור ספרדשיט חדש
    sh = client.create(SPREADSHEET_NAME)
    sh.share(None, perm_type="anyone", role="writer")

    # גליון הגדרות
    ws_settings = sh.sheet1
    ws_settings.update_title(SETTINGS_SHEET)
    ws_settings.append_row([COL_RECIPE, COL_TOTAL_KG])

    cfg["spreadsheet_id"] = sh.id
    cfg["spreadsheet_url"] = sh.url
    _save_config(cfg)
    return sh


# ─── גליון הגדרות ─────────────────────────────────────────────────────────────

def _read_settings(sh: gspread.Spreadsheet) -> dict[str, float]:
    """מחזיר {שם_מתכון: סה"כ_ק"ג}"""
    try:
        ws = sh.worksheet(SETTINGS_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(SETTINGS_SHEET, rows=100, cols=2)
        ws.append_row([COL_RECIPE, COL_TOTAL_KG])
        return {}

    rows = ws.get_all_values()
    result = {}
    for row in rows[1:]:  # דלג על כותרת
        if len(row) >= 2 and row[0]:
            try:
                result[row[0]] = float(row[1]) if row[1] else 10.0
            except ValueError:
                result[row[0]] = 10.0
    return result


def _write_setting(sh: gspread.Spreadsheet, recipe_name: str, total_kg: float):
    ws = sh.worksheet(SETTINGS_SHEET)
    rows = ws.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        if row and row[0] == recipe_name:
            ws.update_cell(i, 2, total_kg)
            return
    ws.append_row([recipe_name, total_kg])


def _delete_setting(sh: gspread.Spreadsheet, recipe_name: str):
    ws = sh.worksheet(SETTINGS_SHEET)
    rows = ws.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        if row and row[0] == recipe_name:
            ws.delete_rows(i)
            return


def _rename_setting(sh: gspread.Spreadsheet, old_name: str, new_name: str):
    ws = sh.worksheet(SETTINGS_SHEET)
    rows = ws.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        if row and row[0] == old_name:
            ws.update_cell(i, 1, new_name)
            return


# ─── קריאה וכתיבה ──────────────────────────────────────────────────────────

def load_all_recipes(sh: gspread.Spreadsheet) -> dict:
    """
    מחזיר {recipe_name: {"ingredients": [...], "total_kg": float}}
    """
    settings = _read_settings(sh)
    recipes = {}

    for ws in sh.worksheets():
        name = ws.title
        if name == SETTINGS_SHEET:
            continue
        rows = ws.get_all_values()
        if not rows:
            continue
        # שורה ראשונה = כותרות (רכיב, יחס)
        ingredients = []
        for row in rows[1:]:
            if len(row) >= 2 and row[0]:
                try:
                    ingredients.append({"רכיב": row[0], "יחס": float(row[1])})
                except ValueError:
                    ingredients.append({"רכיב": row[0], "יחס": 0.0})

        recipes[name] = {
            "ingredients": ingredients,
            "total_kg": settings.get(name, 10.0),
        }

    return recipes


def save_recipe(sh: gspread.Spreadsheet, recipe_name: str,
                ingredients: list[dict], total_kg: float):
    """יוצר/מעדכן גליון עבור המתכון."""
    try:
        ws = sh.worksheet(recipe_name)
        ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=recipe_name, rows=200, cols=2)

    # כותרות
    rows_to_write = [[HDR_ING, HDR_RATIO]]
    for ing in ingredients:
        name_ = ing.get("רכיב", "")
        ratio = ing.get("יחס", 0)
        if name_ and float(ratio or 0) > 0:
            rows_to_write.append([name_, ratio])

    ws.update(rows_to_write, value_input_option="USER_ENTERED")
    _write_setting(sh, recipe_name, total_kg)


def delete_recipe(sh: gspread.Spreadsheet, recipe_name: str):
    """מוחק גליון."""
    try:
        ws = sh.worksheet(recipe_name)
        sh.del_worksheet(ws)
    except gspread.exceptions.WorksheetNotFound:
        pass
    _delete_setting(sh, recipe_name)


def rename_recipe(sh: gspread.Spreadsheet, old_name: str, new_name: str):
    """משנה שם גליון."""
    try:
        ws = sh.worksheet(old_name)
        ws.update_title(new_name)
    except gspread.exceptions.WorksheetNotFound:
        pass
    _rename_setting(sh, old_name, new_name)


def get_spreadsheet_url(sh: gspread.Spreadsheet) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sh.id}"
