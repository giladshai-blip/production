"""
אפליקציית מחשבון יחסי מתכון — Streamlit
"""

import io
from datetime import datetime

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

# ─── אתחול מצב ───────────────────────────────────────────────────────────────
if "recipes" not in st.session_state:
    st.session_state.recipes = {
        "מתכון חדש": [
            {"רכיב": "רכיב 1", "יחס": 1.0},
        ]
    }
if "active_recipe" not in st.session_state:
    st.session_state.active_recipe = "מתכון חדש"


# ─── סרגל צד — ניהול מתכונים ─────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 מתכונים")

    recipe_names = list(st.session_state.recipes.keys())
    selected = st.radio("בחר מתכון:", recipe_names,
                        index=recipe_names.index(st.session_state.active_recipe)
                        if st.session_state.active_recipe in recipe_names else 0)
    st.session_state.active_recipe = selected

    st.divider()

    # הוסף מתכון חדש
    new_name = st.text_input("שם מתכון חדש:", key="new_recipe_name")
    if st.button("➕ הוסף מתכון", use_container_width=True):
        name = new_name.strip()
        if name and name not in st.session_state.recipes:
            st.session_state.recipes[name] = [{"רכיב": "רכיב 1", "יחס": 1.0}]
            st.session_state.active_recipe = name
            st.rerun()
        elif not name:
            st.warning("הכנס שם למתכון")
        else:
            st.warning("מתכון בשם זה כבר קיים")

    # מחק מתכון
    if len(st.session_state.recipes) > 1:
        if st.button("🗑️ מחק מתכון נוכחי", use_container_width=True,
                     type="secondary"):
            del st.session_state.recipes[st.session_state.active_recipe]
            st.session_state.active_recipe = list(st.session_state.recipes.keys())[0]
            st.rerun()

    st.divider()

    # טעינת קובץ Excel
    st.subheader("📂 טעינת קובץ")
    uploaded = st.file_uploader("העלה קובץ מתכונים (xlsx):", type=["xlsx"])
    if uploaded:
        try:
            df_up = pd.read_excel(uploaded, dtype={COL_RECIPE: str, COL_INGREDIENT: str})
            required = [COL_RECIPE, COL_INGREDIENT, COL_RATIO]
            if all(c in df_up.columns for c in required):
                df_up[COL_RATIO] = pd.to_numeric(df_up[COL_RATIO], errors="coerce").fillna(0)
                loaded = {}
                for recipe, grp in df_up.groupby(COL_RECIPE, sort=False):
                    rows = [{"רכיב": r[COL_INGREDIENT], "יחס": r[COL_RATIO]}
                            for _, r in grp.iterrows()]
                    loaded[recipe] = rows
                st.session_state.recipes.update(loaded)
                st.session_state.active_recipe = list(loaded.keys())[0]
                st.success(f"נטענו {len(loaded)} מתכונים")
                st.rerun()
            else:
                st.error(f"עמודות חסרות: {[c for c in required if c not in df_up.columns]}")
        except Exception as e:
            st.error(f"שגיאה בטעינה: {e}")


# ─── אזור ראשי ───────────────────────────────────────────────────────────────
recipe_name = st.session_state.active_recipe
ingredients = st.session_state.recipes[recipe_name]

col_title, col_rename = st.columns([3, 2])
with col_title:
    st.subheader(f"📝 {recipe_name}")
with col_rename:
    new_recipe_name = st.text_input("שנה שם:", value=recipe_name,
                                    key="rename_input", label_visibility="collapsed")
    if new_recipe_name != recipe_name and new_recipe_name.strip():
        new_recipe_name = new_recipe_name.strip()
        if new_recipe_name not in st.session_state.recipes:
            st.session_state.recipes[new_recipe_name] = st.session_state.recipes.pop(recipe_name)
            st.session_state.active_recipe = new_recipe_name
            st.rerun()

# כמות אצווה
total_kg = st.number_input(
    "סה\"כ ק\"ג לאצווה:",
    min_value=0.001, value=10.0, step=0.5, format="%.3f",
)

st.divider()

# ─── טבלת רכיבים ─────────────────────────────────────────────────────────────
st.markdown("**רכיבים ויחסים:**")

df_edit = pd.DataFrame(ingredients)
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

# שמור שינויים בחזרה
edited_clean = edited.dropna(subset=["רכיב"]).copy()
edited_clean["יחס"] = pd.to_numeric(edited_clean["יחס"], errors="coerce").fillna(0)
st.session_state.recipes[recipe_name] = edited_clean.to_dict("records")
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
            "רכיב":     name_ing,
            "יחס":      ratio,
            "אחוז %":   round(pct, 2),
            'ק"ג':      round(kg, 3),
        })

    df_results = pd.DataFrame(results)

    # מדדים מהירים
    cols = st.columns(len(valid) if len(valid) <= 4 else 4)
    for i, row in enumerate(results[:4]):
        with cols[i]:
            kg_col = 'ק"ג'
            st.metric(row["רכיב"], f'{row[kg_col]:.3f} ק"ג',
                      f'{row["אחוז %"]:.1f}%')

    if len(results) > 4:
        st.markdown("")

    # טבלת תוצאות מלאה
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

    # שורת סה"כ
    st.markdown(f"**סה\"כ: {total_kg:.3f} ק\"ג**")

    st.divider()

    # ─── ייצוא Excel ────────────────────────────────────────────────────────
    st.subheader("💾 ייצוא")

    export_scope = st.radio("ייצא:", ["מתכון נוכחי בלבד", "כל המתכונים"],
                            horizontal=True)

    def build_export_df():
        recipes_to_export = (
            {recipe_name: ingredients}
            if export_scope == "מתכון נוכחי בלבד"
            else st.session_state.recipes
        )
        rows = []
        for r_name, r_ings in recipes_to_export.items():
            for ing in r_ings:
                if ing.get("רכיב") and float(ing.get("יחס", 0) or 0) > 0:
                    rows.append({
                        COL_RECIPE:     r_name,
                        COL_INGREDIENT: ing["רכיב"],
                        COL_RATIO:      float(ing["יחס"]),
                        COL_TOTAL_KG:   total_kg,
                    })
        return pd.DataFrame(rows)

    df_export = build_export_df()

    if not df_export.empty:
        buf = io.BytesIO()
        build_excel(df_export, total_kg, buf)
        buf.seek(0)
        filename = f"מתכון_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        st.download_button(
            label="📥 הורד Excel",
            data=buf,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
