"""
אפליקציית מחשבון יחסי מתכון — Streamlit + Google Sheets
"""

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from recipe_ratio_calculator import build_excel, COL_RECIPE, COL_INGREDIENT, COL_RATIO, COL_TOTAL_KG

# ─── הגדרות עמוד ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="מחשבון יחסי מתכון",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { direction: rtl; text-align: right; }
    h1, h2, h3, p, label, .stMarkdown { direction: rtl; text-align: right; }
    div[data-testid="metric-container"] { direction: rtl; text-align: right; }
    div[data-testid="stSidebar"] { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ מחשבון יחסי מתכון")
st.caption("חשב כמה ק\"ג דרוש מכל רכיב לפי יחסי המתכון")

SECRETS_FILE = Path("client_secrets.json")


# ─── Google Sheets — חיבור ───────────────────────────────────────────────────

@st.cache_resource
def _get_sheets_client():
    from sheets_connector import connect
    return connect()


@st.cache_resource
def _get_spreadsheet(_client):
    from sheets_connector import get_or_create_spreadsheet
    return get_or_create_spreadsheet(_client)


def sheets_connected() -> bool:
    return "sheets_client" in st.session_state and st.session_state.sheets_client is not None


def try_connect_sheets():
    if not SECRETS_FILE.exists():
        return False
    try:
        client = _get_sheets_client()
        sh = _get_spreadsheet(client)
        st.session_state.sheets_client = client
        st.session_state.spreadsheet = sh
        return True
    except Exception as e:
        st.session_state.sheets_error = str(e)
        return False


def sync_to_sheets(recipe_name: str, ingredients: list, total_kg: float):
    if not sheets_connected():
        return
    try:
        from sheets_connector import save_recipe
        save_recipe(st.session_state.spreadsheet, recipe_name, ingredients, total_kg)
        st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
    except Exception as e:
        st.session_state.sheets_error = str(e)


def load_from_sheets():
    if not sheets_connected():
        return
    try:
        from sheets_connector import load_all_recipes
        data = load_all_recipes(st.session_state.spreadsheet)
        if data:
            new_recipes = {}
            new_totals = {}
            for name, info in data.items():
                new_recipes[name] = info["ingredients"]
                new_totals[name] = info["total_kg"]
            st.session_state.recipes = new_recipes
            st.session_state.total_kg_per_recipe = new_totals
            if st.session_state.active_recipe not in new_recipes:
                st.session_state.active_recipe = list(new_recipes.keys())[0]
    except Exception as e:
        st.session_state.sheets_error = str(e)


# ─── אתחול מצב ───────────────────────────────────────────────────────────────
if "recipes" not in st.session_state:
    st.session_state.recipes = {
        "מתכון חדש": [{"רכיב": "רכיב 1", "יחס": 1.0}]
    }
if "active_recipe" not in st.session_state:
    st.session_state.active_recipe = "מתכון חדש"
if "total_kg_per_recipe" not in st.session_state:
    st.session_state.total_kg_per_recipe = {}
if "sheets_client" not in st.session_state:
    st.session_state.sheets_client = None
if "spreadsheet" not in st.session_state:
    st.session_state.spreadsheet = None
if "last_sync" not in st.session_state:
    st.session_state.last_sync = None

# ניסיון חיבור אוטומטי בהפעלה ראשונה
if st.session_state.sheets_client is None and SECRETS_FILE.exists():
    if "auto_connect_tried" not in st.session_state:
        st.session_state.auto_connect_tried = True
        try_connect_sheets()
        if sheets_connected():
            load_from_sheets()


# ─── סרגל צד ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 מתכונים")

    recipe_names = list(st.session_state.recipes.keys())
    active = st.session_state.active_recipe
    if active not in recipe_names:
        active = recipe_names[0]
    selected = st.radio("בחר מתכון:", recipe_names,
                        index=recipe_names.index(active))
    st.session_state.active_recipe = selected

    st.divider()

    # הוספת מתכון
    new_name = st.text_input("שם מתכון חדש:", key="new_recipe_name")
    if st.button("➕ הוסף מתכון", use_container_width=True):
        name = new_name.strip()
        if name and name not in st.session_state.recipes:
            st.session_state.recipes[name] = [{"רכיב": "רכיב 1", "יחס": 1.0}]
            st.session_state.total_kg_per_recipe[name] = 10.0
            st.session_state.active_recipe = name
            if sheets_connected():
                sync_to_sheets(name, st.session_state.recipes[name], 10.0)
            st.rerun()
        elif not name:
            st.warning("הכנס שם למתכון")
        else:
            st.warning("מתכון בשם זה כבר קיים")

    # מחיקת מתכון
    if len(st.session_state.recipes) > 1:
        if st.button("🗑️ מחק מתכון נוכחי", use_container_width=True, type="secondary"):
            del_name = st.session_state.active_recipe
            del st.session_state.recipes[del_name]
            st.session_state.total_kg_per_recipe.pop(del_name, None)
            st.session_state.active_recipe = list(st.session_state.recipes.keys())[0]
            if sheets_connected():
                from sheets_connector import delete_recipe
                delete_recipe(st.session_state.spreadsheet, del_name)
            st.rerun()

    st.divider()

    # טעינת קובץ Excel
    st.subheader("📂 טעינת קובץ")
    uploaded = st.file_uploader("Excel מתכונים:", type=["xlsx"])
    if uploaded:
        try:
            df_up = pd.read_excel(uploaded, dtype={COL_RECIPE: str, COL_INGREDIENT: str})
            required = [COL_RECIPE, COL_INGREDIENT, COL_RATIO]
            if all(c in df_up.columns for c in required):
                df_up[COL_RATIO] = pd.to_numeric(df_up[COL_RATIO], errors="coerce").fillna(0)
                for recipe, grp in df_up.groupby(COL_RECIPE, sort=False):
                    rows = [{"רכיב": r[COL_INGREDIENT], "יחס": r[COL_RATIO]}
                            for _, r in grp.iterrows()]
                    st.session_state.recipes[recipe] = rows
                    total = float(grp[COL_TOTAL_KG].iloc[0]) if COL_TOTAL_KG in grp.columns else 10.0
                    st.session_state.total_kg_per_recipe[recipe] = total
                    if sheets_connected():
                        sync_to_sheets(recipe, rows, total)
                st.session_state.active_recipe = list(df_up[COL_RECIPE].unique())[0]
                st.success(f"נטענו {df_up[COL_RECIPE].nunique()} מתכונים")
                st.rerun()
            else:
                st.error(f"עמודות חסרות: {[c for c in required if c not in df_up.columns]}")
        except Exception as e:
            st.error(f"שגיאה: {e}")

    st.divider()

    # ─── גוגל שיט ────────────────────────────────────────────────────────────
    st.subheader("🔗 Google Sheets")

    if sheets_connected():
        from sheets_connector import get_spreadsheet_url
        url = get_spreadsheet_url(st.session_state.spreadsheet)
        st.success("מחובר ✓")
        if st.session_state.last_sync:
            st.caption(f"סנכרון אחרון: {st.session_state.last_sync}")
        st.link_button("פתח בגוגל שיט ↗", url, use_container_width=True)
        if st.button("🔄 טען מגוגל שיט", use_container_width=True):
            load_from_sheets()
            st.rerun()
    else:
        if not SECRETS_FILE.exists():
            st.info("להחברת Google Sheets:\n\n1. הורד `client_secrets.json` מ-Google Cloud Console\n2. שמור בתיקיית הפרויקט\n3. הפעל מחדש")
        else:
            if st.button("🔑 התחבר לגוגל", use_container_width=True, type="primary"):
                with st.spinner("מתחבר..."):
                    if try_connect_sheets():
                        load_from_sheets()
                        st.rerun()
                    else:
                        err = st.session_state.get("sheets_error", "")
                        st.error(f"שגיאה: {err}")


# ─── אזור ראשי ───────────────────────────────────────────────────────────────
recipe_name = st.session_state.active_recipe
ingredients = st.session_state.recipes.get(recipe_name, [])
default_kg  = st.session_state.total_kg_per_recipe.get(recipe_name, 10.0)

col_title, col_rename = st.columns([3, 2])
with col_title:
    st.subheader(f"📝 {recipe_name}")
with col_rename:
    new_recipe_name = st.text_input("שנה שם:", value=recipe_name,
                                    key="rename_input", label_visibility="collapsed")
    if new_recipe_name.strip() and new_recipe_name.strip() != recipe_name:
        new_name_clean = new_recipe_name.strip()
        if new_name_clean not in st.session_state.recipes:
            old_name = recipe_name
            st.session_state.recipes[new_name_clean] = st.session_state.recipes.pop(old_name)
            kg = st.session_state.total_kg_per_recipe.pop(old_name, 10.0)
            st.session_state.total_kg_per_recipe[new_name_clean] = kg
            st.session_state.active_recipe = new_name_clean
            if sheets_connected():
                from sheets_connector import rename_recipe
                rename_recipe(st.session_state.spreadsheet, old_name, new_name_clean)
            st.rerun()

# כמות אצווה
total_kg = st.number_input(
    "סה\"כ ק\"ג לאצווה:",
    min_value=0.001,
    value=float(default_kg),
    step=0.5,
    format="%.3f",
    key=f"total_kg_{recipe_name}",
)
# שמור שינוי
if total_kg != default_kg:
    st.session_state.total_kg_per_recipe[recipe_name] = total_kg

st.divider()

# ─── טבלת רכיבים ─────────────────────────────────────────────────────────────
st.markdown("**רכיבים ויחסים:**")

df_edit = pd.DataFrame(ingredients if ingredients else [{"רכיב": "", "יחס": 0.0}])
edited = st.data_editor(
    df_edit,
    column_config={
        "רכיב": st.column_config.TextColumn("שם רכיב", width="large"),
        "יחס":  st.column_config.NumberColumn("יחס", min_value=0.0,
                                               format="%.3f", width="small"),
    },
    num_rows="dynamic",
    use_container_width=True,
    key=f"editor_{recipe_name}",
)

edited_clean = edited.dropna(subset=["רכיב"]).copy()
edited_clean["יחס"] = pd.to_numeric(edited_clean["יחס"], errors="coerce").fillna(0)
new_ingredients = edited_clean.to_dict("records")

# אם הרכיבים השתנו — שמור וסנכרן
if new_ingredients != st.session_state.recipes.get(recipe_name):
    st.session_state.recipes[recipe_name] = new_ingredients
    if sheets_connected():
        sync_to_sheets(recipe_name, new_ingredients, total_kg)

ingredients = st.session_state.recipes[recipe_name]

# ─── חישוב ותצוגה ────────────────────────────────────────────────────────────
st.divider()
st.subheader("📊 תוצאות")

valid = [(r["רכיב"], float(r["יחס"])) for r in ingredients
         if r.get("רכיב") and float(r.get("יחס", 0) or 0) > 0]
total_ratio = sum(v for _, v in valid)

if not valid or total_ratio == 0:
    st.info("הוסף רכיבים עם יחסים חיוביים כדי לראות תוצאות")
else:
    results = []
    for name_ing, ratio in valid:
        pct = ratio / total_ratio * 100
        kg  = ratio / total_ratio * total_kg
        results.append({
            "רכיב":    name_ing,
            "יחס":     ratio,
            "אחוז %":  round(pct, 2),
            'ק"ג':     round(kg, 3),
        })

    df_results = pd.DataFrame(results)

    # מדדים גדולים (עד 4)
    cols = st.columns(min(len(valid), 4))
    for i, row in enumerate(results[:4]):
        with cols[i]:
            kg_col = 'ק"ג'
            st.metric(row["רכיב"], f'{row[kg_col]:.3f} ק"ג',
                      f'{row["אחוז %"]:.1f}%')

    st.dataframe(
        df_results,
        column_config={
            "רכיב":   st.column_config.TextColumn("רכיב", width="large"),
            "יחס":    st.column_config.NumberColumn("יחס", format="%.3f"),
            "אחוז %": st.column_config.NumberColumn("אחוז %", format="%.2f%%"),
            'ק"ג':    st.column_config.NumberColumn('ק"ג', format="%.3f"),
        },
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(f"**סה\"כ: {total_kg:.3f} ק\"ג**")

    st.divider()

    # ─── ייצוא Excel ────────────────────────────────────────────────────────
    st.subheader("💾 ייצוא Excel")
    export_scope = st.radio("ייצא:", ["מתכון נוכחי בלבד", "כל המתכונים"], horizontal=True)

    def build_export_df():
        source = (
            {recipe_name: ingredients}
            if export_scope == "מתכון נוכחי בלבד"
            else st.session_state.recipes
        )
        rows = []
        for r_name, r_ings in source.items():
            t_kg = st.session_state.total_kg_per_recipe.get(r_name, total_kg)
            for ing in r_ings:
                if ing.get("רכיב") and float(ing.get("יחס", 0) or 0) > 0:
                    rows.append({
                        COL_RECIPE:     r_name,
                        COL_INGREDIENT: ing["רכיב"],
                        COL_RATIO:      float(ing["יחס"]),
                        COL_TOTAL_KG:   t_kg,
                    })
        return pd.DataFrame(rows)

    df_export = build_export_df()
    if not df_export.empty:
        buf = io.BytesIO()
        build_excel(df_export, total_kg, buf)
        buf.seek(0)
        st.download_button(
            label="📥 הורד Excel",
            data=buf,
            file_name=f"מתכון_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
