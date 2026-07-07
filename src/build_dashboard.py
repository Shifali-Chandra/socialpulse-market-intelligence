"""
SocialPulse - build a self-contained interactive dashboard (dark BI theme).
Reads the feature dataset and trend/feature reports and writes a single
data/reports/dashboard.html (opens in any browser, no server needed).
All numbers are computed live from our analysis; only the production model fact
(sentiment model + macro-F1) is a documented constant.
"""

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CLEAN = Path("data/clean")
TRENDS = Path("data/reports/trends")
FEAT = Path("data/reports/features")
OUT = Path("data/reports/dashboard.html")

# palette (kept in sync with the CSS below)
BG = "#0e1422"; CARD = "#1a2336"; TEXT = "#e8edf7"; MUTE = "#8b97ad"; GRID = "rgba(255,255,255,0.06)"
TEAL = "#2dd4bf"; VIOLET = "#8b7cff"; GOLD = "#f0c64c"; CORAL = "#f27059"; BLUE = "#5aa9e6"
POS = "#34d399"; NEU = "#8b95a7"; NEG = "#f27059"

# documented model fact (see docs/methodology_report.md and insights_summary.md)
MODEL_NAME = "VADER"; MODEL_F1 = "0.649"
NAMES = {"youtube": "YouTube", "instagram": "Instagram"}


def _category_trends() -> pd.DataFrame:
    """Share shift of the tracked collection categories: early vs late half of the window."""
    k = pd.read_csv(TRENDS / "keyword_over_time.csv")
    weeks = sorted(k["week"].unique())
    mid = len(weeks) // 2
    early, late = weeks[:mid], weeks[mid:]

    def share(ws):
        s = k[k["week"].isin(ws)].groupby("Keyword")["posts"].sum()
        return s / s.sum() * 100

    d = pd.DataFrame({"early": share(early), "late": share(late)}).fillna(0)
    d["change"] = (d["late"] - d["early"]).round(2)
    return d.sort_values("change", ascending=False)


def _dark(fig: go.Figure, height: int = 300, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Segoe UI, Arial, sans-serif", size=12),
        margin=dict(t=28, l=10, r=16, b=10), showlegend=legend,
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center",
                    bgcolor="rgba(0,0,0,0)", font=dict(color=MUTE)),
        title=None, hoverlabel=dict(bgcolor=CARD, font_color=TEXT, bordercolor=GRID),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=MUTE), title=None)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=MUTE), title=None)
    return fig


# ---------------- figures ----------------
def _fig_sentiment(sp: pd.DataFrame) -> go.Figure:
    piv = sp.pivot(index="Platform", columns="sentiment_label", values="count").fillna(0)
    fig = go.Figure()
    doms = {"youtube": [0.0, 0.46], "instagram": [0.54, 1.0]}
    centers = {"youtube": 0.20, "instagram": 0.80}
    order = ["positive", "neutral", "negative"]
    for plat, title in [("youtube", "YouTube"), ("instagram", "Instagram")]:
        vals = [float(piv.loc[plat, s]) for s in order]
        pos_pct = 100 * vals[0] / sum(vals)
        fig.add_trace(go.Pie(labels=order, values=vals, hole=0.64, sort=False, direction="clockwise",
                             domain={"x": doms[plat], "y": [0.05, 0.92]}, textinfo="none",
                             marker=dict(colors=[POS, NEU, NEG], line=dict(color=BG, width=2)),
                             hovertemplate="%{label}: %{value:,.0f} (%{percent})<extra></extra>"))
        fig.add_annotation(x=centers[plat], y=0.52, xref="paper", yref="paper", showarrow=False,
                           text=f"<b>{pos_pct:.0f}%</b>", font=dict(size=22, color=TEXT))
        fig.add_annotation(x=centers[plat], y=0.40, xref="paper", yref="paper", showarrow=False,
                           text="positive", font=dict(size=11, color=MUTE))
        fig.add_annotation(x=centers[plat], y=1.0, xref="paper", yref="paper", showarrow=False,
                           text=f"<b>{title}</b>", font=dict(size=13, color=TEXT))
    return _dark(fig, height=300)


def _fig_keywords(df: pd.DataFrame) -> go.Figure:
    k = df["Keyword"].value_counts().head(8).sort_values()
    fig = go.Figure(go.Bar(x=k.values, y=k.index, orientation="h",
                           marker=dict(color=VIOLET, line_width=0),
                           text=[f"{v:,}" for v in k.values], textposition="outside",
                           textfont=dict(color=MUTE), cliponaxis=False,
                           hovertemplate="%{y}: %{x:,} posts<extra></extra>"))
    fig = _dark(fig, height=320)
    fig.update_xaxes(showgrid=True)
    return fig


def _fig_platform(sp: pd.DataFrame) -> go.Figure:
    piv = sp.pivot(index="Platform", columns="sentiment_label", values="count").fillna(0)
    order = [("positive", POS), ("neutral", NEU), ("negative", NEG)]
    x = ["YouTube", "Instagram"]
    fig = go.Figure()
    for sent, color in order:
        fig.add_trace(go.Bar(name=sent, x=x, y=[float(piv.loc["youtube", sent]), float(piv.loc["instagram", sent])],
                             marker_color=color, hovertemplate="%{x} " + sent + ": %{y:,}<extra></extra>"))
    fig.update_layout(barmode="stack")
    return _dark(fig, height=320, legend=True)


def _fig_volume() -> go.Figure:
    v = pd.read_csv(TRENDS / "volume_over_time.csv")
    fig = px.line(v, x="week", y="posts", color="Platform", markers=True,
                  color_discrete_sequence=[TEAL, VIOLET])
    fig = _dark(fig, height=300, legend=True)
    fig.update_traces(line=dict(width=2.5))
    return fig


# ---------------- html assembly ----------------
def _kpi_cards(total, pos_overall, rise_name, rise_pts, best_plat, best_pct, big_plat, big_n, n_cat) -> str:
    cards = [
        (f"{total:,}", "Total posts", "YouTube + Instagram", TEAL, str(total)),
        (f"{pos_overall:.1f}%", "Positive sentiment", "English-scored posts", POS, f"{pos_overall:.1f}"),
        (rise_name, "Fastest rising", f"+{rise_pts:.2f} pts share", GOLD, ""),
        (best_plat, "Most positive channel", f"{best_pct:.0f}% positive", BLUE, ""),
        (big_plat, "Largest channel", f"{big_n:,} posts", VIOLET, ""),
        (str(n_cat), "Categories tracked", "search themes collected", CORAL, str(n_cat)),
    ]
    out = []
    for val, lab, sub, color, count in cards:
        dc = f" data-count='{count}'" if count else ""
        out.append(f"<div class='kpi'><span class='accent' style='background:{color}'></span>"
                   f"<div class='eyebrow'>{lab}</div><div class='val'{dc}>{val}</div>"
                   f"<div class='sub' style='color:{color}'>{sub}</div></div>")
    return "".join(out)


def _trend_rows(cat: pd.DataFrame, kw_counts: pd.Series) -> str:
    movers = pd.concat([cat.head(3), cat.tail(3)])
    rows = []
    for i, (name, r) in enumerate(movers.iterrows(), 1):
        ch = float(r["change"])
        up = ch >= 0
        cls = "up" if up else "down"
        arrow = "&#9650;" if up else "&#9660;"
        sign = "+" if up else ""
        posts = int(kw_counts.get(name, 0))
        rows.append(f"<div class='trow'><span class='rank'>{i}</span>"
                    f"<div class='tmain'><div class='tname'>{name}</div>"
                    f"<div class='tkw'>{posts:,} posts collected</div></div>"
                    f"<div class='delta {cls}'>{arrow} {sign}{ch:.2f}</div></div>")
    return "".join(rows)


def _phead(title: str, meta_html: str, hint: str) -> str:
    return (f"<div class='phead'><div class='pleft'><span class='eyebrow'>{title}</span>{meta_html}</div>"
            f"<span class='hint'>&#9656;&nbsp;{hint}</span></div>")


CSS = """
:root{--bg:#0e1422;--side:#141c2e;--card:#1a2336;--card2:#1d2740;--bd:#28324c;--txt:#e8edf7;
--mute:#8b97ad;--faint:#5c6880;--teal:#2dd4bf}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--txt);
font-family:"Segoe UI",-apple-system,"Helvetica Neue",Arial,sans-serif;font-size:15px;line-height:1.4}
.layout{display:flex;min-height:100vh}
.sidebar{width:232px;flex:0 0 232px;background:var(--side);border-right:1px solid var(--bd);
position:sticky;top:0;height:100vh;padding:22px 16px;display:flex;flex-direction:column;gap:26px}
.brand{display:flex;align-items:center;gap:11px}
.logo{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,#2dd4bf,#5aa9e6);
display:flex;align-items:center;justify-content:center;font-size:16px}
.brand b{font-size:16px;letter-spacing:.2px}
.nav{display:flex;flex-direction:column;gap:4px}
.nav a{display:flex;align-items:center;gap:12px;padding:10px 13px;border-radius:10px;color:var(--mute);
text-decoration:none;font-size:14px;position:relative;transition:background .15s,color .15s}
.nav a .ico{width:17px;height:17px;border:1.6px solid currentColor;border-radius:5px;opacity:.9}
.nav a:hover{background:#1b243a;color:var(--txt)}
.nav a.active{background:#1f2a42;color:var(--txt)}
.nav a.active::before{content:"";position:absolute;left:0;top:9px;bottom:9px;width:3px;
border-radius:3px;background:var(--teal)}
.side-foot{margin-top:auto;color:var(--faint);font-size:11px;line-height:1.5}
.main{flex:1;min-width:0;padding:26px 34px 40px}
.header{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:22px;flex-wrap:wrap}
.header h1{margin:0 0 3px;font-size:26px;letter-spacing:.2px}
.header .tagline{color:var(--teal);font-size:14.5px;font-weight:600;margin-bottom:6px}
.header .sub{color:var(--mute);font-size:13px}
.chips{display:flex;gap:10px;flex-wrap:wrap}
.chip{background:var(--card);border:1px solid var(--bd);border-radius:22px;padding:8px 16px;
font-size:13px;font-weight:600;white-space:nowrap}
.chip.accent{color:var(--teal);border-color:#25514c}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(172px,1fr));gap:14px;margin-bottom:18px}
.kpi{background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--bd);
border-radius:14px;padding:15px 16px 15px 20px;position:relative;overflow:hidden;
transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
.kpi:hover{transform:translateY(-5px) scale(1.04);box-shadow:0 14px 32px rgba(0,0,0,.5);
border-color:#3c4a6b;z-index:3}
.kpi .accent{position:absolute;left:0;top:15px;bottom:15px;width:4px;border-radius:0 3px 3px 0}
.kpi .eyebrow{text-transform:uppercase;letter-spacing:.7px;font-size:10.5px;color:var(--mute);font-weight:700}
.kpi .val{font-size:25px;font-weight:700;margin:7px 0 6px;font-variant-numeric:tabular-nums;line-height:1.12}
.kpi .sub{font-size:12.5px;font-weight:600}
.panels{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.panel{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:18px 20px;
min-width:0;scroll-margin-top:20px;transition:box-shadow .18s ease,border-color .18s ease}
.panel:hover{box-shadow:0 10px 28px rgba(0,0,0,.35);border-color:#33405e}
.panel.full{grid-column:1 / -1}
.phead{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;gap:12px;flex-wrap:wrap}
.pleft{display:flex;flex-direction:column;gap:6px;min-width:0}
.phead .eyebrow{text-transform:uppercase;letter-spacing:.8px;font-size:12px;color:var(--mute);font-weight:700}
.phead .meta{font-size:11.5px;color:var(--faint)}
.hint{font-size:11px;font-weight:700;color:var(--teal);background:rgba(45,212,191,.12);
border:1px solid rgba(45,212,191,.35);border-radius:20px;padding:5px 12px;text-transform:uppercase;
letter-spacing:.4px;white-space:nowrap;flex:0 0 auto}
.legend{display:flex;gap:14px;font-size:12px;color:var(--mute)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:9px;height:9px;border-radius:50%;display:inline-block}
.trend-list{display:flex;flex-direction:column}
.trow{display:flex;align-items:center;gap:14px;padding:11px 10px;border-bottom:1px solid #212a41;
border-radius:9px;transition:background .15s ease,transform .15s ease}
.trow:last-child{border-bottom:none}
.trow:hover{background:#1f2a42;transform:translateX(3px)}
.rank{color:var(--faint);font-weight:700;font-size:15px;width:16px;text-align:center}
.tmain{flex:1;min-width:0}
.tname{font-weight:700;font-size:14.5px}
.tkw{color:var(--mute);font-size:12px;margin-top:1px}
.delta{font-weight:700;font-size:14px;font-variant-numeric:tabular-nums;white-space:nowrap}
.delta.up{color:#34d399}.delta.down{color:#f27059}
.foot{color:var(--faint);font-size:12px;margin-top:26px;border-top:1px solid var(--bd);padding-top:16px;line-height:1.6}
@media(max-width:1024px){.panels{grid-template-columns:1fr}.panel.full{grid-column:auto}}
@media(max-width:760px){.sidebar{display:none}.main{padding:18px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.kpi:hover{transform:none}.trow:hover{transform:none}}
"""

JS = """
const links=[...document.querySelectorAll('.nav a')];
const map={};links.forEach(a=>{const t=a.getAttribute('href').slice(1);if(t)map[t]=a;});
const obs=new IntersectionObserver((es)=>{es.forEach(e=>{if(e.isIntersecting){
 links.forEach(l=>l.classList.remove('active'));if(map[e.target.id])map[e.target.id].classList.add('active');}});},
 {rootMargin:'-45% 0px -50% 0px'});
document.querySelectorAll('[data-spy]').forEach(s=>obs.observe(s));

const reduce=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
if(!reduce){document.querySelectorAll('.val[data-count]').forEach(el=>{
 const end=parseFloat(el.dataset.count);const dec=(el.dataset.count.indexOf('.')>=0)?1:0;
 const suf=el.textContent.trim().endsWith('%')?'%':'';let t0=null;const dur=900;
 function step(ts){if(!t0)t0=ts;const p=Math.min((ts-t0)/dur,1);const v=end*(1-Math.pow(1-p,3));
  el.textContent=v.toLocaleString(undefined,{minimumFractionDigits:dec,maximumFractionDigits:dec})+suf;
  if(p<1)requestAnimationFrame(step);}
 requestAnimationFrame(step);});}

// pop the hovered pie segment out (grow on hover)
const pie=document.getElementById('g-p-sentiment');
if(pie&&window.Plotly){
 pie.on('plotly_hover',d=>{const p=d.points[0];const n=p.data.values.length;
  const pull=new Array(n).fill(0);pull[p.pointNumber]=0.09;
  Plotly.restyle(pie,{pull:[pull]},[p.curveNumber]);});
 pie.on('plotly_unhover',d=>{const p=d.points[0];const n=p.data.values.length;
  Plotly.restyle(pie,{pull:[new Array(n).fill(0)]},[p.curveNumber]);});}
"""


def _nav() -> str:
    items = [("kpis", "Dashboard"), ("p-sentiment", "Sentiment"), ("p-topics", "Topics"),
             ("p-keywords", "Keywords"), ("p-platforms", "Platforms"), ("p-trends", "Trends")]
    a = [f"<a href='#{i}'{' class=active' if i=='kpis' else ''}><span class='ico'></span>{n}</a>"
         for i, n in items]
    return ("<aside class='sidebar'><div class='brand'><div class='logo'>&#128202;</div><b>SocialPulse</b></div>"
            f"<nav class='nav'>{''.join(a)}</nav>"
            "<div class='side-foot'>Group 8<br>M.Tech Data Engineering<br>Capstone Project</div></aside>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the interactive dashboard HTML.")
    parser.add_argument("--cdn", action="store_true",
                        help="Load Plotly.js from CDN (small file, needs internet) instead of inline (offline).")
    args = parser.parse_args()
    plotlyjs = "cdn" if args.cdn else "inline"

    df = pd.read_csv(CLEAN / "features_dataset.csv")
    sp = pd.read_csv(FEAT / "sentiment_by_platform.csv")
    cat = _category_trends()

    total = len(df)
    pos_overall = 100 * sp[sp["sentiment_label"] == "positive"]["count"].sum() / sp["count"].sum()
    kw_counts = df["Keyword"].value_counts()
    n_cat = int(df["Keyword"].nunique())
    rise_name, rise_pts = cat.index[0], float(cat.iloc[0]["change"])

    pos_share = (sp[sp["sentiment_label"] == "positive"].set_index("Platform")["count"]
                 / sp.groupby("Platform")["count"].sum() * 100)
    best = pos_share.idxmax()
    best_plat, best_pct = NAMES.get(best, best.title()), float(pos_share.max())
    plat_counts = df["Platform"].value_counts()
    big = plat_counts.idxmax()
    big_plat, big_n = NAMES.get(big, big.title()), int(plat_counts.max())

    figs = [("p-sentiment", _fig_sentiment(sp)), ("p-keywords", _fig_keywords(df)),
            ("p-platforms", _fig_platform(sp)), ("p-trends", _fig_volume())]
    div = {}
    for i, (key, fig) in enumerate(figs):
        div[key] = fig.to_html(full_html=False, include_plotlyjs=(plotlyjs if i == 0 else False),
                               div_id=f"g-{key}", config={"displayModeBar": False, "responsive": True})

    dot = lambda c: f"<i style='background:{c}'></i>"
    sent_legend = (f"<div class='legend'><span>{dot(POS)}positive</span>"
                   f"<span>{dot(NEU)}neutral</span><span>{dot(NEG)}negative</span></div>")

    kpi = _kpi_cards(total, pos_overall, rise_name, rise_pts, best_plat, best_pct, big_plat, big_n, n_cat)
    trend = _trend_rows(cat, kw_counts)

    ph = {
        "sentiment": _phead("Sentiment Analysis", sent_legend, "read audience mood"),
        "topics": _phead("Trending Topics", "<div class='meta'>shift in share (recent vs earlier)</div>",
                         "ride rising themes"),
        "keywords": _phead("Audience Interest &middot; Top Categories",
                          "<div class='meta'>posts collected per category</div>", "prioritize content themes"),
        "platforms": _phead("Platform Comparison", "<div class='meta'>english-scored posts</div>",
                           "focus channel budget"),
        "trends": _phead("Activity Over Time", "<div class='meta'>posts per week by platform</div>",
                        "time your campaigns"),
    }

    main_html = (
        "<main class='main'>"
        "<div class='header'><div><h1>SocialPulse Market Intelligence</h1>"
        "<div class='tagline'>One stop for your next marketing campaign ideas to excel</div>"
        "<div class='sub'>YouTube + Instagram &nbsp;&middot;&nbsp; Twitter (EDA only) "
        "&nbsp;&middot;&nbsp; data through 2026-07-05</div></div>"
        f"<div class='chips'><span class='chip accent'>Group 8</span>"
        f"<span class='chip'>{total:,} posts</span><span class='chip'>{MODEL_NAME} sentiment</span></div></div>"
        f"<section class='kpis' id='kpis' data-spy>{kpi}</section>"
        "<section class='panels'>"
        f"<div class='panel' id='p-sentiment' data-spy>{ph['sentiment']}{div['p-sentiment']}</div>"
        f"<div class='panel' id='p-topics' data-spy>{ph['topics']}<div class='trend-list'>{trend}</div></div>"
        f"<div class='panel' id='p-keywords' data-spy>{ph['keywords']}{div['p-keywords']}</div>"
        f"<div class='panel' id='p-platforms' data-spy>{ph['platforms']}{div['p-platforms']}</div>"
        f"<div class='panel full' id='p-trends' data-spy>{ph['trends']}{div['p-trends']}</div>"
        "</section>"
        "<div class='foot'>Sentiment scored with the production model (VADER), selected on an independent "
        "YouTube/Instagram gold set; topics from NMF (k=6). Engagement is normalized within platform. "
        "Twitter is retained for EDA only (source bias). See docs/final_report.md for interpretation and recommendations."
        "</div></main>"
    )

    page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>SocialPulse Market Intelligence</title><style>" + CSS + "</style></head><body>"
            "<div class='layout'>" + _nav() + main_html + "</div>"
            "<script>" + JS + "</script></body></html>")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"Dashboard written: {OUT} ({OUT.stat().st_size // 1024} KB, {len(figs)} charts, "
          f"top riser {rise_name} +{rise_pts:.2f}, most positive {best_plat} {best_pct:.0f}%)")


if __name__ == "__main__":
    main()
