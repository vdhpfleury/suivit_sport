# -*- coding: utf-8 -*-
"""
Dashboard de suivi nutrition & performance - sportif (musculation + basket)
Suivi quotidien / hebdomadaire des apports par categorie + poids & mensurations.
Lancer avec : streamlit run app.py
Les donnees sont stockees dans un Google Sheet (accessible depuis n'importe quel
appareil une fois l'app deployee sur Streamlit Community Cloud) - voir README.md
pour la configuration du Sheet et des secrets.
"""

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------------------------
# CONFIG / CONSTANTES
# ---------------------------------------------------------------------------

conn = st.connection("gsheets", type=GSheetsConnection)

WS_DAILY = "daily_log"
WS_MEASURE = "measurements"
WS_PROFILE = "profile"

DAY_TYPES = ["Repos", "Musculation", "Basket", "Musculation + Basket"]

# categorie -> (unite, label affiche)
CATEGORIES = {
    "viande_poisson": ("g", "Viandes / Poissons blancs / Thon"),
    "oeufs": ("unite", "Oeufs"),
    "fromage_blanc": ("g", "Fromage blanc / yaourt 0-3%"),
    "lait": ("ml", "Lait demi-ecreme"),
    "feculents": ("g", "Feculents crus (riz, pates, avoine, pdt, lentilles, pain)"),
    "legumes": ("g", "Legumes"),
    "fruits": ("unite", "Fruits"),
    "huile_olive": ("g", "Huile d'olive"),
    "oleagineux": ("g", "Oleagineux / beurre de cacahuete"),
    "sucres": ("g", "Miel / confiture / sucres"),
}

# quantites cibles par categorie et par type de journee (point de depart, ajustable)
TARGETS = {
    "viande_poisson": {"Repos": 280, "Musculation": 350, "Basket": 350, "Musculation + Basket": 400},
    "oeufs": {"Repos": 3, "Musculation": 4, "Basket": 4, "Musculation + Basket": 5},
    "fromage_blanc": {"Repos": 600, "Musculation": 650, "Basket": 650, "Musculation + Basket": 650},
    "lait": {"Repos": 300, "Musculation": 300, "Basket": 500, "Musculation + Basket": 500},
    "feculents": {"Repos": 180, "Musculation": 340, "Basket": 360, "Musculation + Basket": 420},
    "legumes": {"Repos": 400, "Musculation": 400, "Basket": 400, "Musculation + Basket": 400},
    "fruits": {"Repos": 3, "Musculation": 4, "Basket": 5, "Musculation + Basket": 5},
    "huile_olive": {"Repos": 15, "Musculation": 20, "Basket": 20, "Musculation + Basket": 20},
    "oleagineux": {"Repos": 15, "Musculation": 20, "Basket": 20, "Musculation + Basket": 20},
    "sucres": {"Repos": 10, "Musculation": 20, "Basket": 25, "Musculation + Basket": 25},
}

# valeurs nutritionnelles moyennes par unite de suivi (proteines, lipides, glucides, kcal)
# indicatif, inspire des tables CIQUAL / USDA
NUTRI = {
    "viande_poisson": (0.23, 0.02, 0.0, 1.20),
    "oeufs": (6.3, 5.0, 0.5, 78.0),
    "fromage_blanc": (0.08, 0.002, 0.04, 0.50),
    "lait": (0.032, 0.015, 0.048, 0.46),
    "feculents": (0.10, 0.015, 0.70, 3.50),
    "legumes": (0.02, 0.003, 0.05, 0.30),
    "fruits": (1.0, 0.3, 25.0, 90.0),
    "huile_olive": (0.0, 1.0, 0.0, 8.84),
    "oleagineux": (0.25, 0.5, 0.20, 6.0),
    "sucres": (0.003, 0.0, 0.80, 3.04),
}

ACTIVITY_FACTOR = {"Repos": 1.30, "Musculation": 1.55, "Basket": 1.65, "Musculation + Basket": 1.75}
KCAL_ADJUST = {"Repos": -400, "Musculation": -100, "Basket": 50, "Musculation + Basket": 150}

MEASURE_FIELDS = {
    "poids": "Poids (kg)",
    "tour_taille": "Tour de taille (cm)",
    "tour_bras": "Tour de bras (cm)",
    "tour_cuisse": "Tour de cuisse (cm)",
    "tour_poitrine": "Tour de poitrine (cm)",
    "tour_hanches": "Tour de hanches (cm)",
    "masse_grasse": "% masse grasse estime (optionnel)",
}

DEFAULT_PROFILE = {"taille_cm": 195, "age": 24, "poids_defaut_kg": 88.0}

DAILY_COLS = ["date", "type_journee"] + list(CATEGORIES.keys())
MEASURE_COLS = ["date"] + list(MEASURE_FIELDS.keys())
PROFILE_COLS = list(DEFAULT_PROFILE.keys())

# ---------------------------------------------------------------------------
# PERSISTANCE (Google Sheets - ttl=0 pour toujours relire la derniere version,
# indispensable des lors que plusieurs appareils peuvent ecrire dans le meme Sheet)
# ---------------------------------------------------------------------------


def _clean_numeric(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_profile():
    try:
        df = conn.read(worksheet=WS_PROFILE, ttl=0)
        df = df.dropna(how="all")
    except Exception:
        df = pd.DataFrame(columns=PROFILE_COLS)
    if df.empty:
        return dict(DEFAULT_PROFILE)
    row = df.iloc[-1]
    return {
        "taille_cm": int(row.get("taille_cm", DEFAULT_PROFILE["taille_cm"])),
        "age": int(row.get("age", DEFAULT_PROFILE["age"])),
        "poids_defaut_kg": float(row.get("poids_defaut_kg", DEFAULT_PROFILE["poids_defaut_kg"])),
    }


def save_profile(profile):
    df = pd.DataFrame([{c: profile[c] for c in PROFILE_COLS}])
    conn.update(worksheet=WS_PROFILE, data=df)


def load_daily_log():
    try:
        df = conn.read(worksheet=WS_DAILY, ttl=0)
        df = df.dropna(how="all")
    except Exception:
        df = pd.DataFrame(columns=DAILY_COLS)
    for c in DAILY_COLS:
        if c not in df.columns:
            df[c] = 0
    df = df[DAILY_COLS].copy()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = _clean_numeric(df, list(CATEGORIES.keys())).fillna({c: 0 for c in CATEGORIES})
        df = df.dropna(subset=["date"])
    return df.sort_values("date")


def save_daily_entry(entry_date, type_journee, quantities):
    df = load_daily_log()
    df = df[df["date"] != pd.Timestamp(entry_date)]
    new_row = {"date": pd.Timestamp(entry_date), "type_journee": type_journee, **quantities}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).sort_values("date")
    df_out = df.copy()
    df_out["date"] = df_out["date"].dt.strftime("%Y-%m-%d")
    conn.update(worksheet=WS_DAILY, data=df_out)


def load_measurements():
    try:
        df = conn.read(worksheet=WS_MEASURE, ttl=0)
        df = df.dropna(how="all")
    except Exception:
        df = pd.DataFrame(columns=MEASURE_COLS)
    for c in MEASURE_COLS:
        if c not in df.columns:
            df[c] = None
    df = df[MEASURE_COLS].copy()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = _clean_numeric(df, list(MEASURE_FIELDS.keys()))
        df = df.dropna(subset=["date"])
    return df.sort_values("date")


def save_measurement(entry_date, values):
    df = load_measurements()
    df = df[df["date"] != pd.Timestamp(entry_date)]
    new_row = {"date": pd.Timestamp(entry_date), **values}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).sort_values("date")
    df_out = df.copy()
    df_out["date"] = df_out["date"].dt.strftime("%Y-%m-%d")
    conn.update(worksheet=WS_MEASURE, data=df_out)


def get_current_poids(profile):
    measurements = load_measurements()
    valid = measurements.dropna(subset=["poids"])
    if not valid.empty:
        return float(valid.sort_values("date").iloc[-1]["poids"])
    return float(profile["poids_defaut_kg"])


# ---------------------------------------------------------------------------
# CALCULS NUTRITION
# ---------------------------------------------------------------------------


def calc_bmr(poids, taille, age):
    return 10 * poids + 6.25 * taille - 5 * age + 5


def calc_objectifs(poids, taille, age, type_journee):
    bmr = calc_bmr(poids, taille, age)
    tdee = bmr * ACTIVITY_FACTOR[type_journee]
    kcal = tdee + KCAL_ADJUST[type_journee]
    protein = 2.2 * poids
    fat = 1.0 * poids
    carbs = (kcal - protein * 4 - fat * 9) / 4
    return {"kcal": kcal, "proteines": protein, "lipides": fat, "glucides": max(carbs, 0)}


def calc_totals_from_quantities(quantities):
    protein = fat = carbs = kcal = 0.0
    for cat, qty in quantities.items():
        p, f, c, k = NUTRI[cat]
        protein += qty * p
        fat += qty * f
        carbs += qty * c
        kcal += qty * k
    return {"kcal": kcal, "proteines": protein, "lipides": fat, "glucides": carbs}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Dashboard nutrition sportif", page_icon="🏋️", layout="wide")

profile = load_profile()

with st.sidebar:
    st.header("⚙️ Profil")
    taille = st.number_input("Taille (cm)", 140, 230, int(profile["taille_cm"]))
    age = st.number_input("Age (annees)", 10, 80, int(profile["age"]))
    poids_defaut = st.number_input(
        "Poids par defaut (kg) - utilise si aucun poids n'a encore ete enregistre",
        40.0, 200.0, float(profile["poids_defaut_kg"]), step=0.1,
    )
    if (taille, age, poids_defaut) != (profile["taille_cm"], profile["age"], profile["poids_defaut_kg"]):
        profile.update({"taille_cm": taille, "age": age, "poids_defaut_kg": poids_defaut})
        save_profile(profile)

    poids_actuel = get_current_poids(profile)
    st.metric("Poids actuel (dernier releve)", f"{poids_actuel:.1f} kg")
    st.caption("Renseigne le poids via l'onglet 'Poids & mensurations' pour qu'il se mette a jour ici.")

st.title("🏋️ Dashboard nutrition & performance")

tab_jour, tab_semaine, tab_corps = st.tabs(
    ["📅 Suivi quotidien", "📈 Suivi hebdomadaire", "📏 Poids & mensurations"]
)

# ---------------------------------------------------------------------------
# TAB 1 : SUIVI QUOTIDIEN
# ---------------------------------------------------------------------------
with tab_jour:
    col_date, col_type = st.columns([1, 1])
    with col_date:
        selected_date = st.date_input("Date", value=date.today(), key="daily_date")
    daily_log = load_daily_log()
    existing = daily_log[daily_log["date"] == pd.Timestamp(selected_date)]
    default_type = existing.iloc[0]["type_journee"] if not existing.empty else "Musculation"
    with col_type:
        type_journee = st.selectbox(
            "Type de journee", DAY_TYPES, index=DAY_TYPES.index(default_type), key="daily_type"
        )

    st.subheader("Aliments consommes")
    with st.form("daily_form"):
        quantities = {}
        cols = st.columns(2)
        for i, (cat_key, (unit, label)) in enumerate(CATEGORIES.items()):
            default_val = 0.0
            if not existing.empty and cat_key in existing.columns:
                default_val = float(existing.iloc[0][cat_key]) if pd.notna(existing.iloc[0][cat_key]) else 0.0
            with cols[i % 2]:
                quantities[cat_key] = st.number_input(
                    f"{label} ({unit})", min_value=0.0, value=default_val, step=1.0, key=f"qty_{cat_key}"
                )
        submitted = st.form_submit_button("💾 Enregistrer la journee")
        if submitted:
            save_daily_entry(selected_date, type_journee, quantities)
            st.success(f"Journee du {selected_date.strftime('%d/%m/%Y')} enregistree.")
            st.rerun()

    # recharge apres eventuel enregistrement
    daily_log = load_daily_log()
    existing = daily_log[daily_log["date"] == pd.Timestamp(selected_date)]
    current_quantities = (
        {cat: float(existing.iloc[0][cat]) for cat in CATEGORIES} if not existing.empty else {c: 0.0 for c in CATEGORIES}
    )

    st.divider()
    st.subheader("Comparaison objectif vs realise - par categorie")

    rows = []
    for cat_key, (unit, label) in CATEGORIES.items():
        cible = TARGETS[cat_key][type_journee]
        consomme = current_quantities[cat_key]
        rows.append({"Categorie": label, "Unite": unit, "Cible": cible, "Consomme": consomme,
                     "Ecart": consomme - cible})
    df_cat = pd.DataFrame(rows)
    st.dataframe(
        df_cat.style.format({"Cible": "{:.0f}", "Consomme": "{:.0f}", "Ecart": "{:+.0f}"})
        .applymap(lambda v: "color: #C00000;" if isinstance(v, (int, float)) and v < 0 else "color: #2E7D32;",
                  subset=["Ecart"]),
        use_container_width=True, hide_index=True,
    )

    fig_cat = go.Figure()
    fig_cat.add_bar(name="Cible", x=df_cat["Categorie"], y=df_cat["Cible"], marker_color="#B0C4DE")
    fig_cat.add_bar(name="Consomme", x=df_cat["Categorie"], y=df_cat["Consomme"], marker_color="#2E75B6")
    fig_cat.update_layout(barmode="group", height=420, xaxis_tickangle=-30,
                           margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_cat, use_container_width=True)

    st.divider()
    st.subheader("Bilan macro / calories du jour")

    objectifs = calc_objectifs(poids_actuel, taille, age, type_journee)
    totaux = calc_totals_from_quantities(current_quantities)

    m1, m2, m3, m4 = st.columns(4)
    for col, key, label, unit in zip(
        [m1, m2, m3, m4],
        ["kcal", "proteines", "lipides", "glucides"],
        ["Calories", "Proteines", "Lipides", "Glucides"],
        ["kcal", "g", "g", "g"],
    ):
        col.metric(
            label,
            f"{totaux[key]:.0f} {unit}",
            delta=f"{totaux[key] - objectifs[key]:+.0f} vs objectif ({objectifs[key]:.0f})",
        )
        pct = min(totaux[key] / objectifs[key], 1.5) if objectifs[key] > 0 else 0
        col.progress(min(pct, 1.0))

# ---------------------------------------------------------------------------
# TAB 2 : SUIVI HEBDOMADAIRE
# ---------------------------------------------------------------------------
with tab_semaine:
    st.subheader("Periode a analyser")
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Du", value=date.today() - timedelta(days=6), key="week_start")
    with c2:
        end_date = st.date_input("Au", value=date.today(), key="week_end")

    daily_log = load_daily_log()
    mask = (daily_log["date"] >= pd.Timestamp(start_date)) & (daily_log["date"] <= pd.Timestamp(end_date))
    period_log = daily_log[mask].sort_values("date")

    if period_log.empty:
        st.info("Aucune journee enregistree sur cette periode. Renseigne des journees dans l'onglet 'Suivi quotidien'.")
    else:
        records = []
        for _, row in period_log.iterrows():
            quantities = {cat: float(row[cat]) if pd.notna(row[cat]) else 0.0 for cat in CATEGORIES}
            totaux = calc_totals_from_quantities(quantities)
            objectifs = calc_objectifs(poids_actuel, taille, age, row["type_journee"])
            records.append({
                "date": row["date"], "type_journee": row["type_journee"],
                "kcal_consomme": totaux["kcal"], "kcal_objectif": objectifs["kcal"],
                "proteines_consomme": totaux["proteines"], "proteines_objectif": objectifs["proteines"],
                "lipides_consomme": totaux["lipides"], "lipides_objectif": objectifs["lipides"],
                "glucides_consomme": totaux["glucides"], "glucides_objectif": objectifs["glucides"],
            })
        df_week = pd.DataFrame(records)

        st.subheader("Moyennes sur la periode")
        m1, m2, m3, m4 = st.columns(4)
        for col, key, label in zip(
            [m1, m2, m3, m4],
            ["kcal", "proteines", "lipides", "glucides"],
            ["Calories (kcal)", "Proteines (g)", "Lipides (g)", "Glucides (g)"],
        ):
            moy_c = df_week[f"{key}_consomme"].mean()
            moy_o = df_week[f"{key}_objectif"].mean()
            col.metric(label, f"{moy_c:.0f}", delta=f"{moy_c - moy_o:+.0f} vs objectif moyen ({moy_o:.0f})")

        st.subheader("Evolution jour par jour")
        metric_choice = st.radio(
            "Indicateur", ["Calories", "Proteines", "Lipides", "Glucides"], horizontal=True, key="metric_choice"
        )
        key_map = {"Calories": "kcal", "Proteines": "proteines", "Lipides": "lipides", "Glucides": "glucides"}
        key = key_map[metric_choice]

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=df_week["date"], y=df_week[f"{key}_objectif"],
                                       name="Objectif", mode="lines+markers", line=dict(dash="dash", color="#B0C4DE")))
        fig_line.add_trace(go.Scatter(x=df_week["date"], y=df_week[f"{key}_consomme"],
                                       name="Consomme", mode="lines+markers", line=dict(color="#2E75B6")))
        fig_line.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10),
                                yaxis_title=metric_choice)
        st.plotly_chart(fig_line, use_container_width=True)

        st.subheader("Moyenne par categorie sur la periode")
        cat_records = []
        for cat_key, (unit, label) in CATEGORIES.items():
            consomme_moy = period_log[cat_key].astype(float).mean()
            cible_moy = period_log["type_journee"].map(lambda t: TARGETS[cat_key][t]).mean()
            cat_records.append({"Categorie": label, "Unite": unit, "Cible moyenne": cible_moy,
                                 "Consomme moyen": consomme_moy})
        df_cat_week = pd.DataFrame(cat_records)

        fig_cat_week = go.Figure()
        fig_cat_week.add_bar(name="Cible moyenne", x=df_cat_week["Categorie"], y=df_cat_week["Cible moyenne"],
                              marker_color="#B0C4DE")
        fig_cat_week.add_bar(name="Consomme moyen", x=df_cat_week["Categorie"], y=df_cat_week["Consomme moyen"],
                              marker_color="#2E75B6")
        fig_cat_week.update_layout(barmode="group", height=420, xaxis_tickangle=-30,
                                    margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_cat_week, use_container_width=True)

        with st.expander("Voir le detail jour par jour"):
            st.dataframe(period_log, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 3 : POIDS & MENSURATIONS
# ---------------------------------------------------------------------------
with tab_corps:
    st.subheader("Nouveau releve")
    measurements = load_measurements()

    meas_date = st.date_input("Date du releve", value=date.today(), key="meas_date")
    existing_meas = measurements[measurements["date"] == pd.Timestamp(meas_date)]

    with st.form("meas_form"):
        cols = st.columns(2)
        values = {}
        for i, (field_key, label) in enumerate(MEASURE_FIELDS.items()):
            default_val = 0.0
            if not existing_meas.empty and pd.notna(existing_meas.iloc[0][field_key]):
                default_val = float(existing_meas.iloc[0][field_key])
            with cols[i % 2]:
                values[field_key] = st.number_input(label, min_value=0.0, value=default_val, step=0.1,
                                                      key=f"meas_{field_key}")
        submitted_meas = st.form_submit_button("💾 Enregistrer le releve")
        if submitted_meas:
            save_measurement(meas_date, values)
            st.success(f"Releve du {meas_date.strftime('%d/%m/%Y')} enregistre.")
            st.rerun()

    measurements = load_measurements()

    if measurements.empty:
        st.info("Aucun releve enregistre pour le moment.")
    else:
        st.divider()
        measurements_sorted = measurements.sort_values("date")
        last_row = measurements_sorted.iloc[-1]
        prev_row = measurements_sorted.iloc[-2] if len(measurements_sorted) > 1 else None

        st.subheader("Derniers releves")
        cols = st.columns(len(MEASURE_FIELDS))
        for col, (field_key, label) in zip(cols, MEASURE_FIELDS.items()):
            val = last_row[field_key]
            delta = None
            if prev_row is not None and pd.notna(prev_row[field_key]) and pd.notna(val):
                delta = f"{val - prev_row[field_key]:+.1f}"
            col.metric(label, f"{val:.1f}" if pd.notna(val) else "-", delta=delta)

        st.divider()
        st.subheader("Evolution")
        field_choice = st.multiselect(
            "Mesures a afficher", list(MEASURE_FIELDS.values()),
            default=[MEASURE_FIELDS["poids"]],
        )
        label_to_key = {v: k for k, v in MEASURE_FIELDS.items()}
        fig_meas = go.Figure()
        for label in field_choice:
            key = label_to_key[label]
            serie = measurements_sorted.dropna(subset=[key])
            if not serie.empty:
                fig_meas.add_trace(go.Scatter(x=serie["date"], y=serie[key], name=label, mode="lines+markers"))
        fig_meas.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_meas, use_container_width=True)

        with st.expander("Historique complet"):
            st.dataframe(measurements_sorted.sort_values("date", ascending=False),
                         use_container_width=True, hide_index=True)
