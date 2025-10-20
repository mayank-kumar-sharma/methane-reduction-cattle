# app.py
import streamlit as st

st.set_page_config(page_title="Cattle Methane Reduction Tool", page_icon="🐄", layout="centered")

# -----------------------------
# Defaults (permanently conservative & India-ready)
# -----------------------------
# Renamed "dairy" -> "cow"
EMISSION_FACTORS_KG_PER_HEAD_YR = {
    "cow": 72.0,      # kg CH4/head·year (conservative default)
    "buffalo": 90.0,  # kg CH4/head·year
}

# Diet reduction (more conservative)
DIET_REDUCTION = {
    "conventional": 0.00,
    "improved": 0.08,       # was 0.10
    "high-quality": 0.12,   # was 0.15
}

# Additive reduction (more conservative + India-specific Harit Dhara)
ADDITIVE_REDUCTION = {
    "none": 0.00,
    "harit dhara (icar)": 0.18,  # was 0.20
    "seaweed": 0.25,             # was 0.30
    "3-NOP": 0.30,               # was 0.31
    "oils": 0.08,                # was 0.10
}

# FIXED GWP (CH4 -> CO2e); AR6 only
GWP_VALUE = 27.2  # IPCC AR6 (27.2) — Latest Update (Best for India)

TREE_T_CO2E_PER_YEAR = 0.021
CAR_T_CO2E_PER_YEAR = 4.6

# -----------------------------
# Tier-2 style dynamic EF helpers (if weight provided)
# -----------------------------
# DMI%: dry matter intake as % of body weight (per day) — more conservative
DMI_PCT_BY_DIET = {
    "conventional": 0.019,   # was 0.020
    "improved": 0.022,       # was 0.023
    "high-quality": 0.025,   # was 0.026
}
# Ym: % of gross energy lost as CH4 (kept realistic & stable)
YM_BY_DIET = {
    "conventional": 7.0,     # %
    "improved": 6.5,         # %
    "high-quality": 6.0,     # %
}
GE_DENSITY_MJ_PER_KG_DM = 18.45   # MJ/kg DM
CH4_ENERGY_MJ_PER_KG = 55.65      # MJ per kg CH4

# -----------------------------
# Functions
# -----------------------------
def fmt(x, ndigits=2):
    return f"{x:,.{ndigits}f}"

def combined_reduction_fraction(f_diet, f_add):
    return 1 - (1 - f_diet) * (1 - f_add)

def baseline_tCH4(ef_kg_per_head_yr, n):
    return (ef_kg_per_head_yr * n) / 1000.0

def calc_dynamic_ef_kg_per_head_yr(weight_kg: float, diet: str) -> float:
    """
    Compute annual EF (kg CH4/head·yr) from weight + diet (Tier-2 style):
      1) DMI (kg DM/day) = BW * DMI%
      2) GE (MJ/day) = DMI * 18.45
      3) CH4 energy (MJ/day) = GE * (Ym/100)
      4) kg CH4/day = CH4 energy / 55.65
      5) EF (kg/yr) = kg/day * 365
    """
    if weight_kg is None or weight_kg <= 0:
        return 0.0
    dmi_pct = DMI_PCT_BY_DIET.get(diet, 0.019)
    ym = YM_BY_DIET.get(diet, 7.0)
    dmi_kg_day = weight_kg * dmi_pct
    ge_mj_day = dmi_kg_day * GE_DENSITY_MJ_PER_KG_DM
    ch4_energy_mj_day = ge_mj_day * (ym / 100.0)
    kg_ch4_day = ch4_energy_mj_day / CH4_ENERGY_MJ_PER_KG
    ef_kg_yr = kg_ch4_day * 365.0
    return ef_kg_yr

def compute_results(n, cattle_type, diet, additive, ef_override_kg_per_head_yr=None):
    # choose EF: use dynamic if provided, else defaults
    if ef_override_kg_per_head_yr and ef_override_kg_per_head_yr > 0:
        ef = ef_override_kg_per_head_yr
    else:
        ef = EMISSION_FACTORS_KG_PER_HEAD_YR[cattle_type]

    f_diet = DIET_REDUCTION[diet]
    f_add = ADDITIVE_REDUCTION[additive]
    base_tCH4 = baseline_tCH4(ef, n)
    f_total = combined_reduction_fraction(f_diet, f_add)
    reduced_tCH4 = base_tCH4 * f_total
    avoided_tCO2e = reduced_tCH4 * GWP_VALUE

    cars = avoided_tCO2e / CAR_T_CO2E_PER_YEAR
    trees = avoided_tCO2e / TREE_T_CO2E_PER_YEAR

    base_tCO2e = base_tCH4 * GWP_VALUE

    return dict(
        ef_used=ef,
        f_diet=f_diet,
        f_add=f_add,
        f_total=f_total,
        baseline_tCH4=base_tCH4,
        baseline_tCO2e=base_tCO2e,
        reduced_tCH4=reduced_tCH4,
        avoided_tCO2e=avoided_tCO2e,
        cars=cars,
        trees=trees,
        gwp=GWP_VALUE,
    )

def compute_what_if(n, cattle_type, diet, ef_override_kg_per_head_yr=None):
    if ef_override_kg_per_head_yr and ef_override_kg_per_head_yr > 0:
        ef = ef_override_kg_per_head_yr
    else:
        ef = EMISSION_FACTORS_KG_PER_HEAD_YR[cattle_type]

    base_tCH4 = baseline_tCH4(ef, n)
    f_diet = DIET_REDUCTION[diet]

    rows = []
    for add_name, f_add in ADDITIVE_REDUCTION.items():
        if add_name == "none":
            continue
        f_total = combined_reduction_fraction(f_diet, f_add)
        tCH4_red = base_tCH4 * f_total
        tCO2e = tCH4_red * GWP_VALUE
        rows.append(
            dict(
                additive=add_name,
                f_total=f_total,
                tCO2e=tCO2e,
                cars=tCO2e / CAR_T_CO2E_PER_YEAR,
                trees=tCO2e / TREE_T_CO2E_PER_YEAR,
            )
        )
    rows.sort(key=lambda r: r["tCO2e"], reverse=True)
    return rows

# -----------------------------
# UI
# -----------------------------
st.markdown(
    """
    <div style='background-color:#f0fdf4; padding:20px; border-radius:12px; text-align:center'>
        <h1 style='color:#166534;'>🐄 Cattle Methane Reduction Tool</h1>
        <p style='color:#374151; font-size:17px;'>
            Estimate methane emissions and reductions from cattle herds.<br>
            Includes <b>CO₂e 🌍, cars 🚗, and trees 🌳 equivalents</b>.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("### 📥 Enter Herd Details")

with st.container():
    with st.form("inputs"):
        n = st.number_input("Number of animals", min_value=1, value=100)
        cattle_type = st.selectbox("Type of animal", ["cow", "buffalo"])

        # Diet + simple explanation
        diet = st.selectbox("Diet type", ["conventional", "improved", "high-quality"])
        st.caption("""
**Conventional =** Mostly dry fodder / crop residue / low nutrition  
**Improved =** Mix of dry + green fodder, better feed balance  
**High-quality =** Good nutrition with protein-rich feed / concentrates
""")

        # Optional weight input (string to allow blank)
        weight_text = st.text_input("Average animal weight (kg) — Optional, improves accuracy", placeholder="e.g., 400")

        # Additives with Harit Dhara
        additive = st.selectbox("Additive used", ["none", "harit dhara (icar)", "seaweed", "3-NOP", "oils"])

        submitted = st.form_submit_button("🚀 Calculate")

if submitted:
    # Parse weight if provided
    weight_val = None
    if weight_text.strip():
        try:
            w = float(weight_text.strip())
            if w > 0:
                weight_val = w
        except:
            weight_val = None

    # If weight provided, compute dynamic EF
    ef_dynamic = calc_dynamic_ef_kg_per_head_yr(weight_val, diet) if weight_val else None

    # Friendly nudge line ABOVE results
    st.info("Results will be more accurate if average animal weight is provided." if not weight_val else
            f"Using weight-based emission factor from {int(weight_val)} kg (Tier-2 style).")

    res = compute_results(n, cattle_type, diet, additive, ef_override_kg_per_head_yr=ef_dynamic)

    if additive != "none":
        st.subheader("✅ Results with Additive")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Baseline CH₄ (t/yr)", fmt(res['baseline_tCH4']))
            st.metric("Methane Reduced (t/yr)", fmt(res['reduced_tCH4']))
        with col2:
            st.metric(f"CO₂e Avoided (t/yr) 🌍 (GWP={fmt(res['gwp'],0)})", fmt(res['avoided_tCO2e']))
            st.metric("Cars Removed 🚗", fmt(res['cars']))

        st.metric("Tree Equivalent 🌳", fmt(res['trees']))

        # Show EF used for transparency
        st.caption(f"Emission factor used: {fmt(res['ef_used'], 1)} kg CH₄/head·yr "
                   f"({ 'weight-based' if ef_dynamic else 'default' }).")

    else:
        st.subheader("📊 Baseline Emissions (no additive)")
        st.metric("Baseline CH₄ (t/yr)", fmt(res['baseline_tCH4']))
        st.metric(f"Baseline CO₂e (t/yr) (GWP={fmt(res['gwp'],0)})", fmt(res['baseline_tCO2e']))
        st.caption(f"Emission factor used: {fmt(res['ef_used'], 1)} kg CH₄/head·yr "
                   f"({ 'weight-based' if ef_dynamic else 'default' }).")

        # What-if section
        st.subheader("🌿 What-if Savings (if you adopt an additive)")
        for row in compute_what_if(n, cattle_type, diet, ef_override_kg_per_head_yr=ef_dynamic):
            with st.expander(f"➡️ {row['additive']}"):
                st.write(f"Reduction: **{int(row['f_total']*100)}%**")
                st.write(f"🌍 CO₂e avoided: **{fmt(row['tCO2e'])} t/year**")
                st.write(f"🚗 Cars removed: **{fmt(row['cars'])}** per year")
                st.write(f"🌳 Tree equivalent: **{fmt(row['trees'])}** trees")

st.markdown("---")
st.markdown("💡 Made with ❤️ by **Mayank Kumar Sharma**")

# -----------------------------
# Sources & Assumptions
# -----------------------------
st.markdown("### 📚 Sources & Assumptions")
st.markdown(
"""
| Parameter | Value Used | Notes / Source |
|---|---:|---|
| **EF – Cow** | 72 kg CH₄/head·yr | Conservative mid-range from IPCC/ICAR/FAO |
| **EF – Buffalo** | 90 kg CH₄/head·yr | Buffalo emits more (India research) |
| **Diet reduction** | 0% / 8% / 12% | Conservative values (real-world achievable) |
| **Harit Dhara (ICAR)** | 18% reduction | ICAR studies show ~17–20% |
| **Seaweed** | 25% reduction | Average from multiple trials |
| **3-NOP** | 30% reduction | Proven in global studies |
| **Oils** | 8% reduction | Typical range 8–15% |
| **CH₄ → CO₂e (GWP)** | **27.2 (IPCC AR6 — Latest Update)** | Most up-to-date science |
| **Cars** | 4.6 t CO₂e/car·yr | US EPA |
| **Trees** | 0.021 t CO₂e/tree·yr | FAO/UNEP global avg |
"""
)

st.markdown(
    "**Note:** If weight is provided, EF is computed from weight and diet using a Tier-2 style approach "
    "(DMI% by diet, GE=18.45 MJ/kg DM, Ym by diet, CH₄ energy=55.65 MJ/kg). "
    "If weight is not provided, the tool uses conservative default EF values."
)
