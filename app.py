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
LOGO_B64 = "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"
st.markdown(f"""
<div style="background:linear-gradient(135deg,#1f4e78,#2e75b6 55%,#0f766e);
            border-radius:14px;padding:18px 26px;margin-bottom:14px;
            display:flex;align-items:center;gap:18px">
  <div style="background:#fff;border-radius:12px;padding:8px;flex:0 0 auto">
    <img src="data:image/png;base64,{LOGO_B64}" style="height:76px;display:block">
  </div>
  <div>
    <div style="color:#fff;font-size:30px;font-weight:800;letter-spacing:.3px">
      CCR Daily Log Report</div>
    <div style="color:#dbeafe;font-size:14px;margin-top:4px">
      Cu CCR Line — Process Parameters (Form PM2-CR-603) &nbsp;•&nbsp;
      Internal Department Dashboard &nbsp;•&nbsp; Pakistan Cables, Nooriabad</div>
  </div>
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
