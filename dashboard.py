import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from fpdf import FPDF
import tempfile
from datetime import timedelta
from pandas.errors import ParserError, EmptyDataError

# --- Page Configuration ---
st.set_page_config(page_title="Dashboard JoueClub Nice", layout="wide")
st.title("Dashboard Communication & Animations — JoueClub Nice")

# --- Sidebar: Data Uploads & Period Selection ---
st.sidebar.header("1. Importer tes données")
followers_file  = st.sidebar.file_uploader("CSV « Followers en plus »", type="csv")
visites_file    = st.sidebar.file_uploader("CSV « Visites »",        type="csv")
vues_file       = st.sidebar.file_uploader("CSV « Vues »",           type="csv")
animations_file = st.sidebar.file_uploader("CSV « Animations »",     type="csv")

if not (followers_file and visites_file and vues_file and animations_file):
    st.sidebar.warning("Merci de charger tous les fichiers avant de poursuivre.")
    st.stop()

# --- CSV Loader & Cleaner ---
@st.cache_data
def load_and_clean_csv(f, col_name):
    df = pd.read_csv(
        f, encoding='utf-16', sep=',', skiprows=2,
        names=["Date", col_name], dtype=str, na_filter=False
    )
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df[col_name] = df[col_name].str.extract(r"(\d+)").astype(int)
    df["Mois"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    return df

# --- Animations Loader ---
@st.cache_data
def load_animations(f):
    f.seek(0)
    try:
        df = pd.read_csv(f, sep=None, engine='python', dtype=str, on_bad_lines='skip')
    except:
        return pd.DataFrame(columns=["Date","Animation"])
    df = df.dropna(axis=1, how='all')
    if df.shape[1] < 2:
        return pd.DataFrame(columns=["Date","Animation"])
    df = df.iloc[:,:2].copy()
    df.columns = ["Date","Animation"]
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    return df.dropna(subset=["Date","Animation"]).reset_index(drop=True)

# --- Load DataFrames ---
df_f    = load_and_clean_csv(followers_file, "Followers")
df_v    = load_and_clean_csv(visites_file,   "Visites")
df_w    = load_and_clean_csv(vues_file,      "Vues")
df_anim = load_animations(animations_file)

# --- Date-picker & Period filter ---
min_date = min(df_f.Date.min(), df_anim.Date.min())
max_date = max(df_f.Date.max(), df_anim.Date.max())

d1, d2 = st.sidebar.date_input(
    "2. Choix de la période",
    [min_date.date(), max_date.date()],
    min_value=min_date.date(), max_value=max_date.date()
)
if d1 > d2:
    st.sidebar.error("La date de début doit être antérieure à la date de fin.")
    st.stop()
start_date, end_date = pd.to_datetime(d1), pd.to_datetime(d2)

df_f    = df_f[df_f.Date.between(start_date, end_date)].reset_index(drop=True)
df_v    = df_v[df_v.Date.between(start_date, end_date)].reset_index(drop=True)
df_w    = df_w[df_w.Date.between(start_date, end_date)].reset_index(drop=True)
df_anim = df_anim[df_anim.Date.between(start_date, end_date)].reset_index(drop=True)

# --- Monthly aggregation ---
for df, col in [(df_f,"Followers"), (df_v,"Visites"), (df_w,"Vues")]:
    df["Mois"] = df.Date.dt.to_period("M").dt.to_timestamp()
agg_f = df_f.groupby("Mois")["Followers"].sum()
agg_v = df_v.groupby("Mois")["Visites"].sum()
agg_w = df_w.groupby("Mois")["Vues"].sum()
df_mon = pd.concat([agg_f, agg_v, agg_w], axis=1).reset_index()

# --- Display period ---
st.markdown(f"**Période affichée :** {start_date.date()} → {end_date.date()}")

# --- KPI Principaux ---
st.header("KPI principaux")
c1, c2, c3 = st.columns(3)
c1.metric("Total Followers", f"{int(agg_f.sum()):,}", help="Nouveaux abonnés total")
c2.metric("Total Visites",   f"{int(agg_v.sum()):,}", help="Visites total")
c3.metric("Total Vues",      f"{int(agg_w.sum()):,}", help="Impr. total")

# --- Consolidated monthly table ---
st.subheader("Données mensuelles consolidées")
disp = df_mon.copy()
disp["Mois"] = disp.Mois.dt.strftime("%b %Y")
st.dataframe(
    disp.style.format({
      "Followers":"{:,}",
      "Visites":"{:,}",
      "Vues":"{:,}"
    }),
    use_container_width=True
)

# --- List of animations in period ---
st.subheader("Animations programmées")
if df_anim.empty:
    st.write("_Aucune animation pour cette période._")
else:
    df_anim_disp = df_anim[["Date","Animation"]].copy()
    df_anim_disp["Date"] = df_anim_disp.Date.dt.strftime("%Y-%m-%d")
    st.dataframe(df_anim_disp, use_container_width=True)

# --- Monthly chart helper ---
def plot_month(x, y, title, ylabel, color):
    fig, ax = plt.subplots(figsize=(8,3))
    ax.plot(x, y, marker="o", color=color, lw=2)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.tight_layout()
    st.pyplot(fig)
    return fig

# --- Monthly Charts ---
st.subheader("Graphiques mensuels")
fig1 = plot_month(df_mon.Mois, df_mon.Followers, "Followers en plus", "Followers en plus", "tab:blue")
fig2 = plot_month(df_mon.Mois, df_mon.Visites,   "Visites profil", "Visites", "tab:orange")
fig3 = plot_month(df_mon.Mois, df_mon.Vues,      "Vues de contenu", "Vues", "tab:green")

# --- Courbe journalière + animations ---
st.subheader("4. Courbe journalière des Followers en plus & animations")
fig4, ax4 = plt.subplots(figsize=(12,4))

# Plot the daily followers line
ax4.plot(df_f.Date, df_f.Followers, color="tab:blue", lw=1.5)

# Red dots for each animation date
for _, r in df_anim.iterrows():
    d = r.Date
    y = df_f.iloc[(df_f.Date - d).abs().argsort()[:1]]["Followers"].iat[0]
    ax4.scatter(d, y, color="red", s=70, zorder=5)

# Compute one median-date per animation for labeling
lbls = (
    df_anim
      .groupby("Animation")["Date"]
      .apply(lambda d: d.sort_values().median())
      .reset_index(name="DateLabel")
)

# Expand y-axis by 50% on top so labels fit
ymin, ymax = df_f.Followers.min(), df_f.Followers.max()
ax4.set_ylim(ymin - 1, ymax * 1.5)

# Draw each label above its red dot, with clipping turned off
for _, r in lbls.iterrows():
    d0, label = r.DateLabel, r.Animation
    y0 = df_f.iloc[(df_f.Date - d0).abs().argsort()[:1]]["Followers"].iat[0]
    ax4.text(
        d0,
        y0 + (ymax * 0.05),       # small upward offset
        label,
        rotation=90,
        ha="center",
        va="bottom",
        color="red",
        fontsize=9,
        backgroundcolor="white",
        clip_on=False            # allow text outside axes bounds
    )

# Final formatting
ax4.set_xlabel("Date")
ax4.set_ylabel("Followers")
ax4.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig4.autofmt_xdate()
fig4.tight_layout()
st.pyplot(fig4)

# --- Export PDF ---
st.header("Export PDF")
if st.button("Générer rapport PDF"):
    pdf = FPDF('P','mm','A4')
    pdf.add_page()
    title_txt = f"Rapport JoueClub Nice ({start_date.date()}–{end_date.date()})"
    pdf.set_font('Arial','B',16)
    pdf.cell(0,10, title_txt.encode('latin-1','ignore').decode('latin-1'), ln=1, align='C')
    pdf.ln(4)

    # KPIs
    pdf.set_font('Arial','B',12)
    pdf.cell(0,6,"KPI principaux",ln=1)
    pdf.set_font('Arial','',10)
    pdf.cell(0,5,f"Total Followers : {int(agg_f.sum()):,}", ln=1)
    pdf.cell(0,5,f"Total Visites   : {int(agg_v.sum()):,}", ln=1)
    pdf.cell(0,5,f"Total Vues      : {int(agg_w.sum()):,}", ln=1)
    pdf.ln(4)

    # Monthly figures
    for title, fig in [
        ("Followers", fig1),
        ("Visites profil", fig2),
        ("Vues de contenu", fig3),
        ("Daily Followers & Animations", fig4),
    ]:
        pdf.set_font('Arial','B',11)
        pdf.cell(0,5,title.encode('latin-1','ignore').decode('latin-1'), ln=1)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight')
        pdf.image(tmp.name, x=15, w=180)
        tmp.close()
        pdf.ln(4)

    pdf_bytes = pdf.output(dest='S').encode('latin-1','ignore')
    fname = f"rapport_joueclub_nice_{start_date.date()}_{end_date.date()}.pdf"
    st.download_button("⬇️ Télécharger le PDF", pdf_bytes, file_name=fname, mime="application/pdf")
    st.success("✅ PDF généré !")
else:
    st.info("Clique pour générer le rapport PDF")

st.markdown("---")
st.markdown("**Développé par JoueClub Nice**")
