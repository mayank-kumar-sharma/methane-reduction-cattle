# app.py
import streamlit as st

st.set_page_config(page_title="Cattle Methane Reduction Tool", page_icon="🐄", layout="centered")
# -----------------------------
# Defaults
# -----------------------------
EMISSION_FACTORS_KG_PER_HEAD_YR = {"dairy": 72.0, "beef": 60.0, "buffalo": 90.0}
DIET_REDUCTION = {"conventional": 0.00, "improved": 0.10, "high-quality": 0.15}
ADDITIVE_REDUCTION = {"none": 0.00, "seaweed": 0.30, "3-NOP": 0.31, "oils": 0.10}
GWP_CH4 = 28.0
TREE_T_CO2E_PER_YEAR = 0.021
CAR_T_CO2E_PER_YEAR = 4.6

# -----------------------------
# Functions
# -----------------------------
def fmt(x, ndigits=2): return f"{x:,.{ndigits}f}"
def combined_reduction_fraction(f_diet, f_add): return 1 - (1 - f_diet) * (1 - f_add)
def baseline_tCH4(EF, n): return (EF * n) / 1000.0

def compute_results(n, cattle_type, diet, additive):
    ef = EMISSION_FACTORS_KG_PER_HEAD_YR[cattle_type]
    f_diet, f_add = DIET_REDUCTION[diet], ADDITIVE_REDUCTION[additive]
    base_tCH4 = baseline_tCH4(ef, n)
    f_total = combined_reduction_fraction(f_diet, f_add)
    reduced_tCH4 = base_tCH4 * f_total
    avoided_tCO2e = reduced_tCH4 * GWP_CH4
    return dict(
        baseline_tCH4=base_tCH4,
        baseline_tCO2e=base_tCH4*GWP_CH4,
        reduced_tCH4=reduced_tCH4,
        avoided_tCO2e=avoided_tCO2e,
        cars=avoided_tCO2e/CAR_T_CO2E_PER_YEAR,
        trees=avoided_tCO2e/TREE_T_CO2E_PER_YEAR,
        ef=ef, f_diet=f_diet, f_add=f_add, f_total=f_total
    )

def compute_what_if(n, cattle_type, diet):
    ef = EMISSION_FACTORS_KG_PER_HEAD_YR[cattle_type]
    base_tCH4 = baseline_tCH4(ef, n)
    f_diet = DIET_REDUCTION[diet]
    rows = []
    for add, f_add in ADDITIVE_REDUCTION.items():
        if add == "none": continue
        f_total = combined_reduction_fraction(f_diet, f_add)
        tCO2e = base_tCH4 * f_total * GWP_CH4
        rows.append(dict(additive=add, f_total=f_total,
                         tCO2e=tCO2e, cars=tCO2e/CAR_T_CO2E_PER_YEAR,
                         trees=tCO2e/TREE_T_CO2E_PER_YEAR))
    return sorted(rows, key=lambda r: r["tCO2e"], reverse=True)

# -----------------------------
# UI
# -----------------------------
st.title("🐄 Cattle Methane Reduction Tool")
st.caption("Estimate methane emissions and reductions from cattle herds. Results in tonnes per year (t/yr).")

with st.form("inputs"):
    n = st.number_input("Number of cattle", min_value=1, value=100)
    cattle_type = st.selectbox("Type of cattle", ["dairy", "beef", "buffalo"])
    diet = st.selectbox("Diet type", ["conventional", "improved", "high-quality"])
    additive = st.selectbox("Additive used", ["none", "seaweed", "3-NOP", "oils"])
    submitted = st.form_submit_button("Calculate")

if submitted:
    res = compute_results(n, cattle_type, diet, additive)

    if additive != "none":
        st.subheader("✅ Results with Additive")
        st.write(f"**Baseline methane:** {fmt(res['baseline_tCH4'])} t CH₄/year "
                 f"(= {fmt(res['baseline_tCO2e'])} t CO₂e/year)")
        st.write(f"**Methane reduced:** {fmt(res['reduced_tCH4'])} t CH₄/year")
        st.write(f"🌍 **CO₂e avoided:** {fmt(res['avoided_tCO2e'])} t/year")
        st.write(f"🚗 **Cars removed:** {fmt(res['cars'])} per year")
        st.write(f"🌳 **Tree equivalent:** {fmt(res['trees'])} trees")

    else:
        st.subheader("📊 Baseline Emissions (no additive)")
        st.write(f"**{fmt(res['baseline_tCH4'])} t CH₄/year** "
                 f"(= {fmt(res['baseline_tCO2e'])} t CO₂e/year)")

        # What-if section
        st.subheader("🌿 What-if Savings (if you adopt an additive)")
        for row in compute_what_if(n, cattle_type, diet):
            st.markdown(f"### ➡️ {row['additive']}")
            st.write(f"Reduction: **{int(row['f_total']*100)}%**")
            st.write(f"🌍 CO₂e avoided: **{fmt(row['tCO2e'])} t/year**")
            st.write(f"🚗 Cars removed: **{fmt(row['cars'])}** per year")
            st.write(f"🌳 Tree equivalent: **{fmt(row['trees'])}** trees")

st.markdown("---")
st.markdown("**Assumptions:** Dairy 72, Beef 60, Buffalo 90 kg CH₄/head·yr. "
            "Diet reduction: 0–15%. Additives: Seaweed 30%, 3-NOP 31%, Oils 10%. "
            "Conversions: 1 kg CH₄ = 28 kg CO₂e; 1 car = 4.6 t CO₂e/year; "
            "1 tree = 0.021 t CO₂e/year.")
