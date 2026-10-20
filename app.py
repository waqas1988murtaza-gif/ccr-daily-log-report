"""CCR Process Parameters Dashboard — PM2-CR-603 (Cu CCR Line).

Standalone internal-department dashboard. Completely separate from the
CCR Ops Excellence (management) app. Data: register photos Jul-Oct 2026,
baked into per-month JSON files in this repo.
"""
import json
import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="CCR Daily Log Report",
                   page_icon="🏭", layout="wide")

BASE = os.path.dirname(os.path.abspath(__file__))
BLUE = "#1f4e78"


@st.cache_data
def load_all():
    with open(os.path.join(BASE, "process_months.json")) as f:
        months = json.load(f)
    if isinstance(months, dict):
        months = months.get("months", [])
    proc, coil, main_mt = [], [], {}
    for m in months:
        with open(os.path.join(BASE, f"process_data_{m}.json")) as f:
            d = json.load(f)
        proc += d["process"]
        coil += d["coiler"]
        main_mt[m] = d["main_dashboard_mt"]
    return months, pd.DataFrame(proc), pd.DataFrame(coil), main_mt


months, pdf, cdf, main_mt = load_all()
for df in (pdf, cdf):
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])

st.markdown(f"<h2 style='color:{BLUE};margin-bottom:0'>CCR Daily Log Report</h2>",
            unsafe_allow_html=True)
st.caption("Cu CCR Line • Internal Department Dashboard • Source: PM2-CR-603 register "
           "(Jul – 11 Oct 2026) • Coil weights matched from Coiler register PM2-CR-609")

sel = st.selectbox("Month", ["ALL (Jul–Oct)"] + months)
if sel == "ALL (Jul–Oct)":
    p, c = pdf, cdf
    sel_months = months
else:
    p = pdf[pdf["date"].dt.strftime("%Y-%m") == sel]
    c = cdf[cdf["date"].dt.strftime("%Y-%m") == sel]
    sel_months = [sel]

# ---------- KPIs ----------
total_mt = c["net_kg"].sum() / 1000 if not c.empty else 0.0
a_mt = c[c["shift"] == "A"]["net_kg"].sum() / 1000 if not c.empty else 0.0
b_mt = c[c["shift"] == "B"]["net_kg"].sum() / 1000 if not c.empty else 0.0
ndays = c["date"].nunique() if not c.empty else 0
k = st.columns(4)
k[0].metric("Total Production", f"{total_mt:,.1f} MT")
k[1].metric("Shift A / Shift B", f"{a_mt:,.1f} / {b_mt:,.1f} MT")
k[2].metric("Coils (Process Sheet)", f"{len(p):,}")
k[3].metric("Production Days", f"{ndays}",
            f"Avg {total_mt/ndays:,.1f} MT/day" if ndays else None)

# ---------- Daily production ----------
st.subheader("Daily Production (MT) — Shift A vs B")
if not c.empty:
    daily = (c.assign(mt=c["net_kg"] / 1000)
              .pivot_table(index="date", columns="shift", values="mt",
                           aggfunc="sum").fillna(0))
    for col in ("A", "B"):
        if col not in daily.columns:
            daily[col] = 0
    st.bar_chart(daily[["A", "B"]])

# ---------- Cast Bar trend + SV ----------
st.subheader("Cast Bar Temperature — Daily Average (SV: 800 ±20)")
if not p.empty and "castbar" in p.columns:
    cb = p.dropna(subset=["castbar"])
    if not cb.empty:
        st.line_chart(cb.groupby("date")["castbar"].mean())
        n_out = int(((cb["castbar"] < 780) | (cb["castbar"] > 820)).sum())
        st.caption(f"{n_out} of {len(cb)} coils are outside the printed SV band "
                   f"780–820 °C. Readings are recorded exactly as written in the register.")

# ---------- Campaigns ----------
st.subheader("Campaigns")
if not c.empty:
    day_tot = c.groupby("date")["net_kg"].sum() / 1000
    camps, cur = [], None
    for d, mt in day_tot.items():
        if cur is None:
            cur = {"Start": d, "End": d, "Days": 0, "MT": 0.0}
        elif (d - cur["End"]).days > 3:
            camps.append(cur)
            cur = {"Start": d, "End": d, "Days": 0, "MT": 0.0}
        cur["End"] = d
        cur["Days"] += 1
        cur["MT"] += mt
    if cur:
        camps.append(cur)
    cdf_show = pd.DataFrame(camps)
    cdf_show.insert(0, "Campaign", [f"C-{i+1}" for i in range(len(cdf_show))])
    cdf_show["Start"] = cdf_show["Start"].dt.strftime("%Y-%m-%d")
    cdf_show["End"] = cdf_show["End"].dt.strftime("%Y-%m-%d")
    cdf_show["MT"] = cdf_show["MT"].round(1)
    st.dataframe(cdf_show, use_container_width=True, hide_index=True)
else:
    st.info("No campaigns detected yet.")

# ---------- Cross-check ----------
st.subheader("Cross-check — Coiler Register vs Main Dashboard")
for m in sel_months:
    cm = cdf[cdf["date"].dt.strftime("%Y-%m") == m] if not cdf.empty else cdf
    ct = cm["net_kg"].sum() / 1000 if not cm.empty else 0.0
    mm = main_mt.get(m)
    if mm:
        note = " (register photos only up to 11 Oct — coverage difference)" if m == "2026-10" else ""
        st.write(f"**{m}:** Coiler total **{ct:,.1f} MT** vs Main dashboard "
                 f"**{mm:,.1f} MT** → difference **{ct-mm:+.2f} MT**{note}")

# ---------- Per-coil data ----------
with st.expander("Per-coil Data (Process Sheet)"):
    if not p.empty:
        cols = [x for x in ["date", "shift", "supervisor", "coil", "weight_kg",
                            "time", "castbar", "speed", "cc_in_p", "cc_out_t",
                            "rm", "em_t", "q_t", "remarks"] if x in p.columns]
        show = p.sort_values(["date", "shift", "coil"])[cols].copy()
        show["date"] = show["date"].dt.strftime("%Y-%m-%d")

        def sv_red(v):
            try:
                x = float(v)
            except (TypeError, ValueError):
                return ""
            return ("background-color:#fee2e2;color:#b91c1c;font-weight:700"
                    if (x < 780 or x > 820) else "")

        if "castbar" in show.columns:
            cb = pd.to_numeric(show["castbar"], errors="coerce")
            n_out = int(((cb < 780) | (cb > 820)).sum())
            st.caption(f"Cast Bar SV: 800 ±20 (780–820) — {n_out} coil(s) in this view "
                       f"are outside the SV (shown in red). Other printed SVs: "
                       f"SF 1200 ±50, HF 1120–1150, Tundish 1130 ±20 "
                       f"(these three are recorded as '-' in the register).")
            st.dataframe(show.style.map(sv_red, subset=["castbar"]),
                         use_container_width=True, hide_index=True)
        else:
            st.dataframe(show, use_container_width=True, hide_index=True)
