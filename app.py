import streamlit as st

st.set_page_config(
    page_title="Aktien-Schnäppchen-Agent",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Aktien-Schnäppchen-Agent")

st.write(
    "Der Agent sucht interessante Aktien und bewertet "
    "Chancen und Risiken."
)

st.divider()

bereich = st.radio(
    "Was möchtest du durchsuchen?",
    [
        "💰 Schnäppchen",
        "🧬 Biotech-Perlen",
        "🚀 Space / SpaceX"
    ]
)

if bereich == "💰 Schnäppchen":
    st.subheader("💰 Qualitäts-Schnäppchen")
    st.write(
        "Suche nach günstigen Aktien mit Gewinn, "
        "viel Cash und möglichst wenig Schulden."
    )

elif bereich == "🧬 Biotech-Perlen":
    st.subheader("🧬 Biotech-Perlen")
    st.write(
        "Suche nach kleinen Biotech-Unternehmen mit "
        "interessanter Pipeline und kommenden Katalysatoren."
    )
    st.write("📅 FDA / PDUFA-Termine werden später integriert.")

elif bereich == "🚀 Space / SpaceX":
    st.subheader("🚀 Space / SpaceX-Chancen")
    st.write(
        "Suche nach kleinen börsennotierten Unternehmen "
        "aus Raumfahrt, Satelliten und SpaceX-Zulieferern."
    )
