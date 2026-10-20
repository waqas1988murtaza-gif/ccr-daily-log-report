"""CCR Daily Log Report — Cu CCR Line Process Parameters (PM2-CR-603).

Standalone INTERNAL DEPARTMENT dashboard. Completely separate from the
CCR Ops Excellence (management) app — different repo, different app.

Data flow: Daily entry happens ONLY in the web form -> Google Sheet
"CCR Process Parameters - PM2-CR-603". This app reads that Sheet LIVE
(gviz CSV) and falls back to the baked Jul-Oct 2026 snapshot in this
repo when the Sheet is not reachable.
"""
import json
import os
import urllib.parse
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="CCR Daily Log Report", page_icon="🏭", layout="wide")

SHEET_ID = "1A3MvsHLnMI8StxKT8RqZpmDCygkQCdFo2MLnKsCDQuw"
BASE = os.path.dirname(os.path.abspath(__file__))
MAIN_MT = {"2026-07": 501.1, "2026-08": 689.4, "2026-09": 301.8, "2026-10": 432.8}
BLUE, TEAL, AMBER, RED, GREEN = "#2563eb", "#0f766e", "#f59e0b", "#dc2626", "#16a34a"
NUMCOLS = ["weight_kg", "castbar", "speed", "cc_in_p", "cc_out_t", "rm",
           "em_t", "em_p", "q_t", "q_p", "amp", "sf", "hf", "tundish", "cc_in_t"]

# ---------------------------------------------------------------- header
st.markdown("""
<div style="background:linear-gradient(135deg,#1f4e78,#2e75b6 55%,#0f766e);
            border-radius:14px;padding:22px 26px;margin-bottom:14px">
  <div style="color:#fff;font-size:30px;font-weight:800;letter-spacing:.3px">
    🏭 CCR Daily Log Report</div>
  <div style="color:#dbeafe;font-size:14px;margin-top:4px">
    Cu CCR Line — Process Parameters (Form PM2-CR-603) &nbsp;•&nbsp;
    Internal Department Dashboard &nbsp;•&nbsp; Pakistan Cables, Nooriabad</div>
</div>""", unsafe_allow_html=True)


def section(title):
    st.markdown(
        f"<div style='border-left:5px solid #2e75b6;padding-left:10px;"
        f"margin:20px 0 8px;font-size:19px;font-weight:700;color:#1f4e78'>"
        f"{title}</div>", unsafe_allow_html=True)


def kpi_card(col, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#fff;border:1px solid #e2e8f0;border-top:5px solid {color};
                border-radius:12px;padding:14px 10px;text-align:center;
                box-shadow:0 1px 4px rgba(15,40,80,.08);min-height:96px">
      <div style="font-size:25px;font-weight:800;color:{color}">{value}</div>
      <div style="font-size:12px;color:#475569;margin-top:2px">{label}</div>
      <div style="font-size:11px;color:#94a3b8">{sub}</div>
    </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- data
def _clean(df):
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    for c in NUMCOLS + ["coil"]:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace("?", "", regex=False),
                errors="coerce")
    return df


def _map_sheet_columns(df):
    out = pd.DataFrame()
    low = {str(c).strip().lower(): c for c in df.columns}

    def pick(*needles):
        for k, orig in low.items():
            if all(n in k for n in needles):
                return df[orig]
        return None

    out["date"] = pick("date")
    out["shift"] = pick("shift")
    out["supervisor"] = pick("supervisor")
    out["operator"] = pick("operator")
    out["coil"] = pick("coil #") if pick("coil #") is not None else pick("coil")
    out["weight_kg"] = pick("coil weight net")
    out["time"] = pick("time")
    out["sf"] = pick("sf melt")
    out["hf"] = pick("hf melt")
    out["tundish"] = pick("tundish")
    out["castbar"] = pick("cast bar")
    out["speed"] = pick("casting speed")
    out["cc_in_t"] = pick("inlet temp")
    out["cc_in_p"] = pick("inlet press")
    out["cc_out_t"] = pick("outlet temp")
    out["rm"] = pick("rm speed") if pick("rm speed") is not None else pick("rm")
    out["em_t"] = pick("emulsion", "temp")
    out["em_p"] = pick("emulsion", "press")
    out["q_t"] = pick("quenching", "temp") if pick("quenching", "temp") is not None else pick("quench", "temp")
    out["q_p"] = pick("quenching", "press") if pick("quenching", "press") is not None else pick("quench", "press")
    out["amp"] = pick("amp")
    out["remarks"] = pick("remark")
    return out


@st.cache_data(ttl=300, show_spinner=False)
def load_live():
    frames = []
    start = date(2026, 7, 1)
    today = date.today()
    y, m = start.year, start.month
    while (y, m) <= (today.year, today.month):
        tab = date(y, m, 1).strftime("%b %y")
        url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
               f"?tqx=out:csv&sheet={urllib.parse.quote(tab)}")
        try:
            raw = pd.read_csv(url)
            if raw is not None and len(raw) and raw.shape[1] > 5:
                frames.append(_map_sheet_columns(raw))
        except Exception:
            pass
        m += 1
        if m == 13:
            y, m = y + 1, 1
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df[df["coil"].notna()] if "coil" in df.columns else df
    return _clean(df)


@st.cache_data(show_spinner=False)
def load_snapshot():
    with open(os.path.join(BASE, "process_months.json")) as f:
        mf = json.load(f)
    months = mf.get("months", []) if isinstance(mf, dict) else mf
    proc, coil = [], []
    for m in months:
        with open(os.path.join(BASE, f"process_data_{m}.json")) as f:
            d = json.load(f)
        proc += d["process"]
        coil += d["coiler"]
    pdf = _clean(pd.DataFrame(proc))
    cdf = _clean(pd.DataFrame(coil))
    if not cdf.empty and "net_kg" in cdf.columns:
        cdf["net_kg"] = pd.to_numeric(cdf["net_kg"], errors="coerce")
    return pdf, cdf


live = load_live()
if not live.empty:
    pdf = live
    cdf = pd.DataFrame({"date": pdf["date"], "shift": pdf["shift"],
                        "coil": pdf["coil"], "net_kg": pdf["weight_kg"]})
    LIVE = True
else:
    pdf, cdf = load_snapshot()
    LIVE = False

top = st.columns([3, 1])
with top[0]:
    if LIVE:
        st.success("● LIVE — data is being read directly from the Google Sheet. "
                   "New form entries appear here automatically (refreshes every 5 minutes).")
    else:
        st.warning("○ Showing the saved snapshot (Jul – 11 Oct 2026). The live Sheet "
                   "could not be read — once the Sheet is shared as 'Anyone with the "
                   "link — Viewer', this dashboard goes LIVE automatically.")
with top[1]:
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

months = sorted(pdf["date"].dt.strftime("%Y-%m").dropna().unique()) if not pdf.empty else []
sel = st.selectbox("Month", ["ALL (Jul–Oct)"] + months)
if sel == "ALL (Jul–Oct)":
    p, c, sel_months = pdf, cdf, months
else:
    p = pdf[pdf["date"].dt.strftime("%Y-%m") == sel]
    c = cdf[cdf["date"].dt.strftime("%Y-%m") == sel]
    sel_months = [sel]

# ---------------------------------------------------------------- KPIs
total_mt = c["net_kg"].sum() / 1000 if not c.empty else 0.0
a_mt = c[c["shift"] == "A"]["net_kg"].sum() / 1000 if not c.empty else 0.0
b_mt = c[c["shift"] == "B"]["net_kg"].sum() / 1000 if not c.empty else 0.0
ndays = c["date"].nunique() if not c.empty else 0
cb = p.dropna(subset=["castbar"]) if not p.empty and "castbar" in p.columns else pd.DataFrame()
n_out = int(((cb["castbar"] < 780) | (cb["castbar"] > 820)).sum()) if not cb.empty else 0
cols = st.columns(5)
kpi_card(cols[0], "Total Production", f"{total_mt:,.1f} MT", "#1f4e78", sel)
kpi_card(cols[1], "Shift A", f"{a_mt:,.1f} MT", BLUE, "day shift")
kpi_card(cols[2], "Shift B", f"{b_mt:,.1f} MT", AMBER, "night shift")
kpi_card(cols[3], "Coils (Process Sheet)", f"{len(p):,}", TEAL,
         f"{ndays} production days")
kpi_card(cols[4], "Cast Bar Out of SV", f"{n_out} / {len(cb)}", RED,
         "SV 800 ±20 °C")

# ---------------------------------------------------------------- daily
section("Daily Production (MT) — Shift A vs B")
if not c.empty:
    daily = (c.assign(mt=c["net_kg"] / 1000)
              .pivot_table(index="date", columns="shift", values="mt",
                           aggfunc="sum").fillna(0))
    for col in ("A", "B"):
        if col not in daily.columns:
            daily[col] = 0
    fig = go.Figure()
    fig.add_bar(x=daily.index, y=daily["A"], name="Shift A",
                marker_color=BLUE)
    fig.add_bar(x=daily.index, y=daily["B"], name="Shift B",
                marker_color=AMBER)
    fig.update_layout(barmode="stack", height=320, margin=dict(t=10, b=10),
                      legend=dict(orientation="h", y=1.08),
                      plot_bgcolor="#fff", yaxis_title="MT",
                      xaxis=dict(gridcolor="#eef2f7"),
                      yaxis=dict(gridcolor="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- cast bar
section("Cast Bar Temperature — Daily Average (SV: 800 ±20)")
if not cb.empty:
    avg = cb.groupby("date")["castbar"].mean()
    fig = go.Figure()
    fig.add_hrect(y0=780, y1=820, fillcolor=GREEN, opacity=0.10, line_width=0)
    fig.add_hline(y=820, line_dash="dash", line_color=RED)
    fig.add_hline(y=780, line_dash="dash", line_color=RED)
    fig.add_trace(go.Scatter(x=avg.index, y=avg.values, mode="lines+markers",
                             line=dict(color="#1f4e78", width=2.5),
                             marker=dict(size=6), name="Daily avg"))
    fig.update_layout(height=300, margin=dict(t=10, b=10), plot_bgcolor="#fff",
                      yaxis_title="°C", yaxis=dict(gridcolor="#e2e8f0"),
                      xaxis=dict(gridcolor="#eef2f7"), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"{n_out} of {len(cb)} coils are outside the printed SV band "
               f"780–820 °C (shaded). Readings are recorded exactly as written "
               f"in the register.")

# ---------------------------------------------------------------- campaigns
section("Campaigns")
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
    cs = pd.DataFrame(camps)
    cs.insert(0, "Campaign", [f"C-{i+1}" for i in range(len(cs))])
    cs["Start"] = cs["Start"].dt.strftime("%Y-%m-%d")
    cs["End"] = cs["End"].dt.strftime("%Y-%m-%d")
    cs["MT"] = cs["MT"].round(1)
    st.dataframe(cs, use_container_width=True, hide_index=True)
else:
    st.info("No campaigns detected yet.")

# ---------------------------------------------------------------- cross-check
section("Cross-check — Coiler Register vs Main Dashboard")
for m in sel_months:
    cm = cdf[cdf["date"].dt.strftime("%Y-%m") == m] if not cdf.empty else cdf
    ct = cm["net_kg"].sum() / 1000 if not cm.empty else 0.0
    mm = MAIN_MT.get(m)
    if mm:
        note = " (register photos only up to 11 Oct — coverage difference)" if m == "2026-10" else ""
        diff = ct - mm
        color = GREEN if abs(diff) <= 2 else AMBER
        st.markdown(
            f"**{m}:** Coiler total **{ct:,.1f} MT** vs Main dashboard "
            f"**{mm:,.1f} MT** → difference "
            f"<span style='color:{color};font-weight:700'>{diff:+.2f} MT</span>{note}",
            unsafe_allow_html=True)

# ---------------------------------------------------------------- per-coil
section("Per-coil Data (Process Sheet)")
if not p.empty:
    cols_show = [x for x in ["date", "shift", "supervisor", "operator", "coil",
                             "weight_kg", "time", "castbar", "speed", "cc_in_p",
                             "cc_out_t", "rm", "em_t", "em_p", "q_t", "q_p",
                             "amp", "remarks"] if x in p.columns]
    show = p.sort_values(["date", "shift", "coil"])[cols_show].copy()
    show["date"] = show["date"].dt.strftime("%Y-%m-%d")

    def sv_red(v):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return ""
        return ("background-color:#fee2e2;color:#b91c1c;font-weight:700"
                if (x < 780 or x > 820) else "")

    if "castbar" in show.columns:
        st.caption("Cast Bar SV: 800 ±20 (780–820) — out-of-SV values are shown "
                   "in red. Other printed SVs: SF 1200 ±50, HF 1120–1150, "
                   "Tundish 1130 ±20 (recorded as '-' in the register).")
        st.dataframe(show.style.map(sv_red, subset=["castbar"]),
                     use_container_width=True, hide_index=True)
    else:
        st.dataframe(show, use_container_width=True, hide_index=True)

st.markdown("<div style='text-align:center;color:#94a3b8;font-size:12px;"
            "margin-top:24px'>CCR Daily Log Report • PM2-CR-603 • "
            "Data source: CCR Process Parameters Google Sheet (form entries) • "
            "Snapshot fallback: register photos Jul – 11 Oct 2026</div>",
            unsafe_allow_html=True)
