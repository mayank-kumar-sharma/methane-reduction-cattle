# app.py
# Cattle Methane Reduction Tool — Streamlit UI
# Language: English only
# Shows cars removed + tree equivalents
# "What-if savings" section appears when additive = none
# No CSV/PDF export; simple, farmer-friendly UI

import streamlit as st
from typing import Dict, Tuple, List

# -----------------------------
# Page Config & Basic Styling
# -----------------------------
st.set_page_config(
    page_title="Cattle Methane Reduction Tool",
    page_icon="🐄",
    layout="centered",
)

# Minimal CSS for clean "cards"
st.markdown(
    """
    <style>
      .card {
        border: 1px solid #e6e6e6;
        border-radius: 14px;
        padding: 16px 18px;
        margin: 10px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        background: white;
      }
      .card.emphasis {
        border: 2px solid #22c55e;
        box-shadow: 0 4px 10px rgba(34,197,94,0.12);
      }
      .card-title {
        font-weight: 700;
        font-size: 1.05rem;
        margin-bottom: 6px;
      }
      .kpi {
        font-weight: 800;
        font-size: 1.25rem;
        margin: 4px 0 2px 0;
      }
      .subtext {
        color: #6b7280;
        font-size: 0.9rem;
        margin-top: 0;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(1, minmax(0, 1fr));
        gap: 12px;
      }
      @media (min-width: 700px) {
        .grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      }
      .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.8rem;
        background: #f1f5f9;
        color: #0f172a;
        border: 1px solid #e2e8f0;
        margin-top: 4px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Defaults (editable)
# -----------------------------
EMISSION_FACTORS_KG_PER_HEAD_YR: Dict[str, float] = {
    "dairy": 72.0,     # kg CH4/head·year
    "beef": 60.0,      # kg CH4/head·year
    "buffalo": 90.0,   # kg CH4/head·year
}

DIET_REDUCTION: Dict[str, float] = {
    "conventional": 0.00,
    "improved": 0.10,
    "high-quality": 0.15,
}

ADDITIVE_REDUCTION: Dict[str, float] = {
    "none": 0.00,
    "seaweed": 0.30,  # Asparagopsis (field-realistic average)
    "3-NOP": 0.31,
    "oils": 0.10,
}

# Conversions / equivalences
GWP_CH4 = 28.0                   # 1 kg CH4 = 28 kg CO2e
TREE_T_CO2E_PER_YEAR = 0.021     # t CO2e sequestered per tree per year
CAR_T_CO2E_PER_YEAR = 4.6        # t CO2e per car per year

# -----------------------------
# Helper Functions
# -----------------------------
def fmt(x: float, ndigits: int = 2) -> str:
    """Format number with fixed decimals and thousands separator."""
    return f"{x:,.{ndigits}f}"

def combined_reduction_fraction(f_diet: float, f_add: float) -> float:
    """Combine reductions multiplicatively to avoid double counting."""
    return 1.0 - (1.0 - f_diet) * (1.0 - f_add)

def baseline_tCH4(EF_kg_per_head_yr: float, n_animals: int) -> float:
    """Baseline methane in tonnes CH4 per year for the herd."""
    return (EF_kg_per_head_yr * n_animals) / 1000.0

def compute_results(
    n_animals: int,
    cattle_type: str,
    diet: str,
    additive: str
) -> Dict[str, float]:
    """Compute baseline, reductions, and equivalences."""
    ef = EMISSION_FACTORS_KG_PER_HEAD_YR[cattle_type]
    f_diet = DIET_REDUCTION[diet]
    f_add = ADDITIVE_REDUCTION[additive]

    base_tCH4 = baseline_tCH4(ef, n_animals)
    total_frac = combined_reduction_fraction(f_diet, f_add)
    reduced_tCH4 = base_tCH4 * total_frac
    avoided_tCO2e = reduced_tCH4 * GWP_CH4

    cars = avoided_tCO2e / CAR_T_CO2E_PER_YEAR if CAR_T_CO2E_PER_YEAR > 0 else 0.0
    trees = avoided_tCO2e / TREE_T_CO2E_PER_YEAR if TREE_T_CO2E_PER_YEAR > 0 else 0.0

    # Also report baseline CO2e (no reduction) for context
    base_tCO2e = base_tCH4 * GWP_CH4
    base_cars = base_tCO2e / CAR_T_CO2E_PER_YEAR if CAR_T_CO2E_PER_YEAR > 0 else 0.0
    base_trees = base_tCO2e / TREE_T_CO2E_PER_YEAR if TREE_T_CO2E_PER_YEAR > 0 else 0.0

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

def compute_what_if_rows(
    n_animals: int, cattle_type: str, diet: str
) -> List[Dict[str, float]]:
    """When additive='none', compute savings for each possible additive using current diet."""
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
    # Sort by highest CO2e avoided
    rows.sort(key=lambda r: r["tCO2e_avoided"], reverse=True)
    return rows

# -----------------------------
# Header
# -----------------------------
st.title("Cattle Methane Reduction Tool")
st.caption(
    "Estimate baseline methane and potential reductions using diet and feed additives. "
    "Outputs are shown in **tonnes per year (t/yr)**. Equivalences include **cars removed** and **tree equivalents**."
)

# -----------------------------
# Inputs (4 only)
# -----------------------------
with st.form("inputs"):
    n_animals = st.number_input("Number of cattle", min_value=0, step=1, value=100)
    cattle_type = st.selectbox("Type of cattle", options=["dairy", "beef", "buffalo"], index=0)
    diet = st.selectbox("Diet type", options=["conventional", "improved", "high-quality"], index=0)
    additive = st.selectbox("Additive used", options=["none", "seaweed", "3-NOP", "oils"], index=0)

    submitted = st.form_submit_button("Calculate")

# -----------------------------
# Validate & Compute
# -----------------------------
if submitted:
    if n_animals <= 0:
        st.warning("Please enter a number of cattle greater than 0.")
        st.stop()

    results = compute_results(n_animals, cattle_type, diet, additive)

    # -------------------------
    # Case A: Additive chosen
    # -------------------------
    if additive != "none":
        st.markdown('<div class="card emphasis">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Results</div>', unsafe_allow_html=True)

        st.write(
            f"**Baseline methane:** {fmt(results['baseline_tCH4'])} t CH₄/year "
            f"(= {fmt(results['baseline_tCO2e'])} t CO₂e/year)"
        )
        st.write(
            f"**Methane reduced:** {fmt(results['reduced_tCH4'])} t CH₄/year "
            f"→ **CO₂e avoided:** {fmt(results['avoided_tCO2e'])} t/year"
        )
        st.write(
            f"**Cars removed:** {fmt(results['cars_removed'])} cars/year &nbsp;•&nbsp; "
            f"**Tree equivalent:** {fmt(results['trees_equivalent'])} trees"
        )

        st.markdown(
            f"<p class='subtext'>Assumptions: EF={fmt(results['ef'],0)} kg CH₄/head·yr, "
            f"Diet reduction={int(results['f_diet']*100)}%, "
            f"Additive ({additive}) reduction={int(results['f_add']*100)}%, "
            f"combined reduction={int(results['f_total']*100)}%.</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------
    # Case B: Additive = none  (Baseline + What-if savings)
    # -------------------------
    else:
        # Baseline card
        st.markdown('<div class="card emphasis">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Your herd baseline</div>', unsafe_allow_html=True)
        st.write(
            f"**{fmt(results['baseline_tCH4'])} t CH₄/year** "
            f"(= {fmt(results['baseline_tCO2e'])} t CO₂e/year)"
        )
        st.write(
            f"**Cars equivalent:** {fmt(results['baseline_cars'])} cars/year &nbsp;•&nbsp; "
            f"**Tree equivalent:** {fmt(results['baseline_trees'])} trees"
        )
        st.markdown(
            f"<span class='badge'>Diet: {diet.replace('-', ' ')}</span> "
            f"<span class='badge'>Type: {cattle_type}</span> "
            f"<span class='badge'>EF: {fmt(results['ef'],0)} kg CH₄/head·yr</span>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # What-if section
        st.subheader("What-if savings if you adopt an additive (with your current diet)")
        rows = compute_what_if_rows(n_animals, cattle_type, diet)

        if not rows:
            st.info("No additive options available.")
        else:
            # Identify best option for emphasis
            best_additive_name = rows[0]["additive"] if rows else None

            # Render cards in a responsive grid
            st.markdown('<div class="grid">', unsafe_allow_html=True)
            for r in rows:
                is_best = (r["additive"] == best_additive_name)
                card_class = "card emphasis" if is_best else "card"
                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                st.markdown(f'<div class="card-title">{r["additive"]}</div>', unsafe_allow_html=True)

                pct = int(round(r["f_total"] * 100))
                st.write(f"**% Reduction (with current diet):** {pct}%")
                st.write(
                    f"**CO₂e avoided:** {fmt(r['tCO2e_avoided'])} t/year"
                )
                st.write(
                    f"**Cars removed:** {fmt(r['cars_removed'])} cars/year"
                )
                st.write(
                    f"**Tree equivalent:** {fmt(r['trees_equivalent'])} trees"
                )
                if is_best:
                    st.markdown("<span class='badge'>Top recommendation</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Footer / Notes
# -----------------------------
with st.expander("Assumptions & Notes"):
    st.markdown(
        """
- **Emission factors (EF)** used here are conservative starting defaults and can be refined later:
  - Dairy: 72 kg CH₄/head·year
  - Beef: 60 kg CH₄/head·year
  - Buffalo: 90 kg CH₄/head·year
- **Diet reduction factors:** conventional 0%, improved 10%, high-quality 15%.
- **Additive reduction factors:** seaweed 30%, 3-NOP 31%, oils 10%.
- **Conversions / equivalences:** 1 kg CH₄ = 28 kg CO₂e; 1 car ≈ 4.6 t CO₂e/year; 1 tree ≈ 0.021 t CO₂e/year.
- **Method:** Reductions from diet and additive are combined **multiplicatively** to avoid double counting.
- All outputs are annualized (per year) and reported in **tonnes** (t).
        """
    )
