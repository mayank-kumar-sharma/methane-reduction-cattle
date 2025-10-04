# app.py
# Cattle Methane Reduction Tool — Streamlit UI (simple version)
# No CSS, only Streamlit native layout + emojis

import streamlit as st

# -----------------------------
# Config / Defaults
# -----------------------------
EMISSION_FACTORS_KG_PER_HEAD_YR = {
    "dairy": 72.0,
    "beef": 60.0,
    "buffalo": 90.0,
}

DIET_REDUCTION = {
    "conventional": 0.00,
    "improved": 0.10,
    "high-quality": 0.15,
}

ADDITIVE_REDUCTION = {
    "none": 0.00,
    "seaweed": 0.30,
    "3-NOP": 0.31,
    "oils": 0.10,
}

GWP_CH4 = 28.0                   # 1 kg CH4 = 28 kg CO2e
TREE_T_CO2E_PER_YEAR = 0.021     # t CO2e/tree/year
CAR_T_CO2E_PER_YEAR = 4.6        # t CO2e/car/year

# -----------------------------
# Helper functions
# -----------------------------
def fmt(x, ndigits=2):
    return f"{x:,.{ndigits}f}"

def combined_reduction_fraction(f_diet, f_add):
    return 1 - (1 - f_diet) * (1 - f_add)

def baseline_tCH4(EF, n_animals):
    return (EF * n_animals) / 1000.0

def compute_results(n_animals, cattle_type, diet, additive):
    ef = EMISSION_FACTORS_KG_PER_HEAD_YR[cattle_type]
    f_diet = DIET_REDUCTION[diet]
    f_add = ADDITIVE_REDUCTION[additive]

    base_tCH4 = baseline_tCH4(ef, n_animals)
    total_frac = combined_reduction_fraction(f_diet, f_add)
    reduced_tCH4 = base_tCH4 * total_frac
    avoided_tCO2e = reduced_tCH4 * GWP_CH4

    cars = avoided_tCO2e / CAR_T_CO2E_PER_YEAR
    trees = avoided_tCO2e / TREE_T_CO2E_PER_YEAR

    base_tCO2e = base_tCH4 * GWP_CH4
    base_cars = base_tCO2e / CAR_T_CO2E_PER_YEAR
    base_trees = base_tCO2e / TREE_T_CO2E_PER_YEAR

    return dict(
        ef=ef,
        f_diet=f_diet,
        f_add=f_add,
        f_total=total_frac,
        baseline_tCH4=base_tCH4,
        baseline_tCO2e=base_tCO2e,
        baseline_cars=base_cars,
        baseline_trees=base_trees,
        reduced_tCH4=reduced_tCH4,
        avoided_tCO2e=avoided_tCO2e,
        cars_removed=cars,
        trees_equivalent=trees,
    )

def compute_what_if(n_animals, cattle_type, diet):
    ef = EMISSION_FACTORS_KG_PER_HEAD_YR[cattle_type]
    base_tCH4 = baseline_tCH4(ef, n_animals)
    f_diet = DIET_REDUCTION[diet]

    rows = []
    for add_name, f_add in ADDITIVE_REDUCTION.items():
        if add_name == "none":
            continue
        f_total = combined_reduction_fraction(f_diet, f_add)
        tCH4_red = base_tCH4 * f_total
        tCO2e = tCH4_red * GWP_CH4
        cars = tCO2e / CAR_T_CO2E_PER_YEAR
        trees = tCO2e / TREE_T_CO2E_PER_YEAR
        rows.append(
            dict(
                additive=add_name,
                f_total=f_total,
                tCH4_reduced=tCH4_red,
                tCO2e_avoided=tCO2e,
                cars_removed=cars,
                trees_equivalent=trees,
            )
        )
    rows.sort(key=lambda r: r["tCO2e_avoided"], reverse=True)
    return rows

# -----------------------------
# UI
# -----------------------------
st.title("🐄 Cattle Methane Reduction Tool")
st.caption("Estimate methane emissions and reductions from cattle herds. Results in tonnes per year (t/yr).")

# Inputs
with st.form("inputs"):
    n_animals = st.number_input("Number of cattle 🐄", min_value=0, step=1, value=100)
    cattle_type = st.selectbox("Type of cattle", ["dairy", "beef", "buffalo"])
    diet = st.selectbox("Diet type", ["conventional", "improved", "high-quality"])
    additive = st.selectbox("Additive used", ["none", "seaweed", "3-NOP", "oils"])
    submitted = st.form_submit_button("Calculate")

if submitted:
    if n_animals <= 0:
        st.warning("Please enter a number of cattle greater than 0.")
        st.stop()

    results = compute_results(n_animals, cattle_type, diet, additive)

    if additive != "none":
        st.subheader("✅ Results with Additive")
        st.write(f"**Baseline methane:** {fmt(results['baseline_tCH4'])} t CH₄/year "
                 f"(= {fmt(results['baseline_tCO2e'])} t CO₂e/year)")
        st.write(f"**Methane reduced:** {fmt(results['reduced_tCH4'])} t CH₄/year")
        st.write(f"🌍 **CO₂e avoided:** {fmt(results['avoided_tCO2e'])} t/year")
        st.write(f"🚗 **Cars removed:** {fmt(results['cars_removed'])} per year")
        st.write(f"🌳 **Tree equivalent:** {fmt(results['trees_equivalent'])} trees")

    else:
        st.subheader("📊 Baseline Emissions (no additive)")
        st.write(f"**{fmt(results['baseline_tCH4'])} t CH₄/year** "
                 f"(= {fmt(results['baseline_tCO2e'])} t CO₂e/year)")
        st.write(f"🚗 Cars equivalent: {fmt(results['baseline_cars'])}")
        st.write(f"🌳 Tree equivalent: {fmt(results['baseline_trees'])}")

        # What-if savings
        st.subheader("🌿 What-if Savings (if you adopt an additive)")
        rows = compute_what_if(n_animals, cattle_type, diet)
        for r in rows:
            st.markdown(f"### ➡️ {r['additive']}")
            st.write(f"Reduction: **{int(r['f_total']*100)}%**")
            st.write(f"🌍 CO₂e avoided: **{fmt(r['tCO2e_avoided'])} t/year**")
            st.write(f"🚗 Cars removed: **{fmt(r['cars_removed'])}** per year")
            st.write(f"🌳 Tree equivalent: **{fmt(r['trees_equivalent'])}** trees")

# Notes
st.markdown("---")
st.markdown("**Assumptions:** Emission factors: Dairy 72, Beef 60, Buffalo 90 (kg CH₄/head·yr). "
            "Diet reduction: 0–15%. Additives: Seaweed 30%, 3-NOP 31%, Oils 10%. "
            "Conversions: 1 kg CH₄ = 28 kg CO₂e, 1 car = 4.6 t CO₂e/year, 1 tree = 0.021 t CO₂e/year.")
