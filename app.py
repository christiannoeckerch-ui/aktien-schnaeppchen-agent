import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Aktien-Schnäppchen-Agent",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Aktien-Schnäppchen-Agent")
st.caption("Findet interessante Aktien – die endgültige Anlageentscheidung triffst du.")

bereich = st.radio(
    "Was möchtest du durchsuchen?",
    ["💰 Schnäppchen", "🧬 Biotech-Perlen", "🚀 Space / SpaceX"],
    horizontal=True
)

# --------------------------------------------------
# SCHNÄPPCHEN
# --------------------------------------------------

if bereich == "💰 Schnäppchen":

    st.header("💰 Qualitäts-Schnäppchen")

    st.write(
        "Wir suchen günstige US-Aktien und bevorzugen Unternehmen, "
        "die bereits Gewinne schreiben, viel Cash besitzen und wenig "
        "verschuldet sind."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        max_preis = st.number_input(
            "Maximaler Aktienkurs ($)",
            min_value=1.0,
            max_value=20.0,
            value=5.0,
            step=0.5
        )

    with col2:
        min_marktkap = st.number_input(
            "Mindest-Marktkapitalisierung (Mio. $)",
            min_value=10,
            max_value=5000,
            value=50,
            step=10
        )

    with col3:
        anzahl = st.slider(
            "Max. Treffer",
            min_value=5,
            max_value=50,
            value=20,
            step=5
        )

    st.info(
        "⭐ Besonders viele Punkte gibt es für Gewinn, positiven Cashflow, "
        "viel Cash und geringe Verschuldung."
    )

    if st.button("🔎 Schnäppchen suchen", type="primary"):

        with st.spinner("US-Aktien werden durchsucht ..."):

            try:
                query = yf.EquityQuery(
                    "and",
                    [
                        yf.EquityQuery(
                            "eq",
                            ["region", "us"]
                        ),
                        yf.EquityQuery(
                            "gte",
                            ["intradaymarketcap", min_marktkap * 1_000_000]
                        ),
                        yf.EquityQuery(
                            "lte",
                            ["intradayprice", max_preis]
                        ),
                        yf.EquityQuery(
                            "gte",
                            ["intradayprice", 0.50]
                        )
                    ]
                )

                response = yf.screen(
                    query,
                    size=anzahl,
                    sortField="intradaymarketcap",
                    sortAsc=False
                )

                quotes = response.get("quotes", [])

                if not quotes:
                    st.warning("Keine passenden Aktien gefunden.")
                    st.stop()

                kandidaten = []

                fortschritt = st.progress(0)

                for i, aktie in enumerate(quotes):

                    symbol = aktie.get("symbol")

                    if not symbol:
                        continue

                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info

                        preis = info.get(
                            "currentPrice",
                            aktie.get("regularMarketPrice")
                        )

                        marketcap = info.get(
                            "marketCap",
                            aktie.get("marketCap")
                        )

                        netto = info.get("netIncomeToCommon")
                        cash = info.get("totalCash")
                        schulden = info.get("totalDebt")
                        cashflow = info.get("operatingCashflow")
                        umsatzwachstum = info.get("revenueGrowth")
                        kgv = info.get("trailingPE")

                        score = 0
                        gruende = []

                        # Gewinn
                        if netto is not None and netto > 0:
                            score += 30
                            gruende.append("Gewinn positiv")

                        # Operativer Cashflow
                        if cashflow is not None and cashflow > 0:
                            score += 20
                            gruende.append("Cashflow positiv")

                        # Cash / Schulden
                        if cash is not None and schulden is not None:

                            if schulden == 0:
                                score += 25
                                gruende.append("Keine Schulden")

                            elif cash > schulden:
                                score += 25
                                gruende.append("Mehr Cash als Schulden")

                            elif cash > schulden * 0.5:
                                score += 12
                                gruende.append("Solide Cash-Position")

                        # Umsatzwachstum
                        if umsatzwachstum is not None:

                            if umsatzwachstum > 0.10:
                                score += 15
                                gruende.append("Umsatz wächst >10 %")

                            elif umsatzwachstum > 0:
                                score += 8
                                gruende.append("Umsatz wächst")

                        # KGV
                        if kgv is not None and 0 < kgv <= 15:
                            score += 10
                            gruende.append("Niedriges KGV")

                        kandidaten.append(
                            {
                                "Symbol": symbol,
                                "Firma": info.get(
                                    "shortName",
                                    aktie.get("shortName", "")
                                ),
                                "Kurs $": round(preis, 2)
                                if preis is not None else None,
                                "Marktkap. Mio. $": round(
                                    marketcap / 1_000_000, 1
                                )
                                if marketcap else None,
                                "KGV": round(kgv, 1)
                                if kgv else None,
                                "Gewinn": "✅"
                                if netto is not None and netto > 0
                                else "❌",
                                "Cash > Schulden": "✅"
                                if cash is not None
                                and schulden is not None
                                and cash > schulden
                                else "❌",
                                "Cashflow": "✅"
                                if cashflow is not None and cashflow > 0
                                else "❌",
                                "Score": score,
                                "Warum interessant?": ", ".join(gruende)
                            }
                        )

                    except Exception:
                        pass

                    fortschritt.progress((i + 1) / len(quotes))

                fortschritt.empty()

                if kandidaten:

                    df = pd.DataFrame(kandidaten)
                    df = df.sort_values(
                        "Score",
                        ascending=False
                    )

                    st.subheader("⭐ Gefundene Kandidaten")

                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.caption(
                        "Der Score ist unser eigener Suchfilter und keine "
                        "Kaufempfehlung. Kandidaten sollten anschließend "
                        "genauer analysiert werden."
                    )

                else:
                    st.warning(
                        "Die Finanzdaten der gefundenen Aktien konnten "
                        "nicht ausreichend ausgewertet werden."
                    )

            except Exception as e:

                st.error(
                    "Beim Abrufen der Börsendaten ist ein Fehler aufgetreten."
                )

                st.code(str(e))


# --------------------------------------------------
# BIOTECH
# --------------------------------------------------

elif bereich == "🧬 Biotech-Perlen":

    st.header("🧬 Biotech-Perlen")

    st.write(
        "Hier suchen wir später nach kleinen Biotech-Unternehmen "
        "mit guter Finanzierung, interessanter Pipeline und "
        "wichtigen kommenden Katalysatoren."
    )

    st.success(
        "📅 Geplant: FDA-/PDUFA-Termine, Studiendaten, "
        "Cash-Runway und Pipeline."
    )


# --------------------------------------------------
# SPACE
# --------------------------------------------------

elif bereich == "🚀 Space / SpaceX":

    st.header("🚀 Space / SpaceX-Chancen")

    st.write(
        "Hier suchen wir später nach kleinen börsennotierten "
        "Raumfahrtunternehmen, Satellitenfirmen sowie "
        "SpaceX- und Starlink-Zulieferern."
    )

    st.success(
        "🚀 Geplant: SpaceX-Bezug, Aufträge, Umsatzwachstum, "
        "Cash und Verschuldung."
    )
