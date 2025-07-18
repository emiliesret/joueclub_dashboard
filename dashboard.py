import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from fpdf import FPDF
import tempfile

# --- Page Configuration ---
st.set_page_config(page_title="Dashboard JoueClub Nice", layout="wide")
st.title("Dashboard Communication & Animations — JoueClub Nice")

# --- Sidebar: Data Uploads ---
st.sidebar.header("Importer tes données")
followers_file = st.sidebar.file_uploader("CSV « Followers en plus »", type=["csv"])
visites_file   = st.sidebar.file_uploader("CSV « Visites »",        type=["csv"])
vues_file      = st.sidebar.file_uploader("CSV « Vues »",           type=["csv"])
if not (followers_file and visites_file and vues_file):
    st.sidebar.info("Upload tes 3 fichiers : followers, visites, vues")
    st.stop()

# --- CSV Loader & Cleaner ---
@st.cache_data
def load_and_clean_csv(file, col_name):
    df = pd.read_csv(
        file, encoding='utf-16', sep=',', skiprows=2,
        names=["Date", col_name], dtype=str, na_filter=False
    )
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df[col_name] = df[col_name].str.extract(r"(\d+)").astype(int)
    df["Mois"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    return df

# --- Load All Data ---
df_followers = load_and_clean_csv(followers_file, "Followers")
df_visites   = load_and_clean_csv(visites_file,   "Visites")
df_vues      = load_and_clean_csv(vues_file,      "Vues")

# --- Monthly Aggregation ---
agg_f = df_followers.groupby("Mois")["Followers"].sum()
agg_v = df_visites.groupby("Mois")["Visites"].sum()
agg_w = df_vues.groupby("Mois")["Vues"].sum()
df_monthly = pd.concat([agg_f, agg_v, agg_w], axis=1).reset_index()

# --- Period of Study ---
start = df_monthly["Mois"].min().strftime("%b %Y")
end   = df_monthly["Mois"].max().strftime("%b %Y")
st.markdown(f"**Période d’étude :** {start} – {end}")

# --- KPI Principaux ---
st.header("KPI principaux")
c1, c2, c3 = st.columns(3)
c1.metric(
    "Total Followers",
    f"{int(agg_f.sum()):,}",
    help="Total des nouveaux abonnés sur la période."
)
c2.metric(
    "Total Visites",
    f"{int(agg_v.sum()):,}",
    help="Total des visites de profil générées."
)
c3.metric(
    "Total Vues",
    f"{int(agg_w.sum()):,}",
    help="Total des impressions de contenu."
)

# --- KPI Additionnels ---
st.markdown("### KPI additionnels")
total_f    = agg_f.sum()
total_v    = agg_v.sum()
total_w    = agg_w.sum()
conv_f     = (total_f/total_w*100) if total_w else 0
conv_v     = (total_v/total_w*100) if total_w else 0
growth     = df_monthly["Followers"].diff().fillna(0)
avg_growth = growth.mean()
idx_peak   = growth.idxmax()
peak_month = df_monthly.loc[idx_peak,"Mois"].strftime("%b %Y") if not growth.empty else "-"
c4, c5, c6 = st.columns(3)
c4.metric(
    "Conv. Followers/Vues",
    f"{conv_f:.2f}%",
    help="Pourcentage de vues menant à un nouvel abonné."
)
c5.metric(
    "Conv. Visites/Vues",
    f"{conv_v:.2f}%",
    help="Pourcentage de vues menant à une visite de profil."
)
c6.metric(
    "Croissance mensuelle",
    f"{avg_growth:.0f} foll/mois",
    help="Gain moyen de nouveaux abonnés par mois."
)
c7, _ = st.columns([1,2])
c7.metric(
    "Mois de pic growth",
    peak_month,
    help="Mois avec le plus fort gain d’abonnés."
)

# --- Data Table ---
st.subheader("Données consolidées")
df_disp = df_monthly.copy()
df_disp["Mois"] = df_disp["Mois"].dt.strftime("%b %Y")
st.dataframe(df_disp.style.format({
    "Followers":"{:,}", "Visites":"{:,}", "Vues":"{:,}"
}), use_container_width=True)

# --- Plot helper & Figures ---
def plot_series(x, y, title, ylabel, color):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x, y, marker="o", color=color)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    st.subheader(title)
    return fig

# --- Figures & Display ---
fig1 = plot_series(
    df_monthly["Mois"], df_monthly["Followers"],
    "Followers", "Followers", "tab:blue"
)

fig2 = plot_series(
    df_monthly["Mois"], df_monthly["Visites"],
    "Visites profil", "Visites", "tab:orange"
)

fig3 = plot_series(
    df_monthly["Mois"], df_monthly["Vues"],
    "Vues contenu", "Vues", "tab:green"
)

st.pyplot(fig1)
st.pyplot(fig2)
st.pyplot(fig3)

# --- Export PDF ---
st.header("Export PDF")
if st.button("Générer le rapport PDF"):
    pdf = FPDF('P','mm','A4')
    pdf.add_page()

    # Titre
    pdf.set_font('Arial','B',16)
    pdf.cell(0, 10, f"Rapport JoueClub Nice ({start} – {end})", ln=True, align='C')
    pdf.ln(5)

    # KPI Principaux
    pdf.set_font('Arial','B',14)
    pdf.cell(0,8,"KPI principaux", ln=True)
    pdf.set_font('Arial','',11)
    pdf.cell(0,6,f"Total Followers : {int(agg_f.sum()):,}", ln=True)
    pdf.cell(0,6,f"Total Visites   : {int(agg_v.sum()):,}", ln=True)
    pdf.cell(0,6,f"Total Vues      : {int(agg_w.sum()):,}", ln=True)
    pdf.ln(5)

    # KPI Additionnels
    pdf.set_font('Arial','B',14)
    pdf.cell(0,8,"KPI additionnels", ln=True)
    pdf.set_font('Arial','',11)
    pdf.cell(0,6,f"Conv. Foll./Vues : {conv_f:.2f} %", ln=True)
    pdf.cell(0,6,f"Conv. Vis./Vues : {conv_v:.2f} %", ln=True)
    pdf.cell(0,6,f"Croiss. mensuelle: {avg_growth:.0f} foll/mois", ln=True)
    pdf.cell(0,6,f"Mois de pic growth: {peak_month}", ln=True)
    pdf.ln(5)

    # Figures helper
    def add_figure(title, fig):
        pdf.set_font('Arial','B',12)
        pdf.cell(0,6, title, ln=True)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight')
        pdf.image(tmp.name, x=15, w=180)
        pdf.ln(5)
        tmp.close()

    add_figure("Followers", fig1)
    add_figure("Visites profil", fig2)
    add_figure("Vues contenu", fig3)

    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    fname = f"rapport_joueclub_nice_{start.replace(' ','_')}_{end.replace(' ','_')}.pdf"
    st.download_button("Télécharger le rapport PDF", pdf_bytes, file_name=fname, mime="application/pdf")
    st.success("Rapport PDF généré !")
else:
    st.info("Clique sur le bouton pour générer le rapport PDF.")

# --- Footer ---
st.markdown("---")
st.markdown("**Développé par JoueClub Nice**")
