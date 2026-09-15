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

# ==========================================================
# SCHNÄPPCHEN
# ==========================================================

if bereich == "💰 Schnäppchen":

    st.header("💰 Qualitäts-Schnäppchen")

    st.write(
        "Wir suchen günstige Aktien und bevorzugen Unternehmen, "
        "die bereits Gewinne schreiben, positiven Cashflow haben "
        "und finanziell solide sind."
    )

    markt = st.radio(
        "Markt auswählen",
        ["🇺🇸 USA", "🇨🇭 Schweiz"],
        horizontal=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if markt == "🇺🇸 USA":
            max_preis = st.number_input(
                "Maximaler Aktienkurs ($)",
                min_value=0.5,
                max_value=20.0,
                value=5.0,
                step=0.5
            )
        else:
            max_preis = st.number_input(
                "Maximaler Aktienkurs (CHF)",
                min_value=0.5,
                max_value=20.0,
                value=5.0,
                step=0.5
            )

    with col2:
        min_marktkap = st.number_input(
            "Mindest-Marktkapitalisierung (Mio.)",
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
        "⭐ Punkte gibt es für Gewinn, positiven Cashflow, "
        "gute Cash-/Schulden-Situation, Wachstum und günstige Bewertung."
    )

    if st.button("🔎 Schnäppchen suchen", type="primary"):

        with st.spinner("Aktien werden analysiert ..."):

            kandidaten = []

            try:

                # --------------------------------------------------
                # USA
                # --------------------------------------------------

                if markt == "🇺🇸 USA":

                    query = yf.EquityQuery(
                        "and",
                        [
                            yf.EquityQuery(
                                "eq",
                                ["region", "us"]
                            ),
                            yf.EquityQuery(
                                "gte",
                                [
                                    "intradaymarketcap",
                                    min_marktkap * 1_000_000
                                ]
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
                        size=min(anzahl * 4, 100),
                        sortField="intradaymarketcap",
                        sortAsc=False
                    )

                    quotes = response.get("quotes", [])

                # --------------------------------------------------
                # SCHWEIZ
                # --------------------------------------------------

                else:

                    # Liste günstiger SIX-Titel als Ausgangsuniversum.
                    # Diese Liste können wir später automatisch erweitern.
                    swiss_symbols = [
                        "IDIA.SW",
                        "AMS.SW",
                        "ARYN.SW",
                        "MBTN.SW",
                        "RLF.SW",
                        "MOLN.SW",
                        "VTGN.SW"
                    ]

                    quotes = [
                        {"symbol": symbol}
                        for symbol in swiss_symbols
                    ]

                if not quotes:
                    st.warning("Keine passenden Aktien gefunden.")
                    st.stop()

                fortschritt = st.progress(0)

                for i, aktie in enumerate(quotes):

                    symbol = aktie.get("symbol")

                    if not symbol:
                        continue

                    # OTC in der US-Suche ausschliessen
                    if markt == "🇺🇸 USA":
                        if symbol.endswith("F") or symbol.endswith("Y"):
                            fortschritt.progress(
                                (i + 1) / len(quotes)
                            )
                            continue

                    try:

                        ticker = yf.Ticker(symbol)
                        info = ticker.info

                        preis = info.get(
                            "currentPrice",
                            info.get("regularMarketPrice")
                        )

                        if preis is None or preis > max_preis:
                            continue

                        marketcap = info.get("marketCap")

                        if (
                            marketcap is not None
                            and marketcap
                            < min_marktkap * 1_000_000
                        ):
                            continue

                        exchange = info.get("exchange", "")
                        country = info.get("country", "")

                        # Nur reguläre US-Börsen
                        if markt == "🇺🇸 USA":

                            erlaubte_boersen = [
                                "NMS",
                                "NYQ",
                                "ASE",
                                "NGM",
                                "NCM",
                                "NAS"
                            ]

                            if exchange not in erlaubte_boersen:
                                continue

                            if country not in [
                                "United States",
                                "USA"
                            ]:
                                continue

                        netto = info.get("netIncomeToCommon")
                        cash = info.get("totalCash")
                        schulden = info.get("totalDebt")
                        cashflow = info.get("operatingCashflow")
                        umsatzwachstum = info.get("revenueGrowth")
                        kgv = info.get("trailingPE")
                        volumen = info.get("averageVolume")

                        score = 0
                        gruende = []

                        # Gewinn
                        if netto is not None and netto > 0:
                            score += 25
                            gruende.append("Gewinn positiv")

                        # Cashflow
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
                                gruende.append(
                                    "Mehr Cash als Schulden"
                                )

                            elif cash > schulden * 0.5:
                                score += 10
                                gruende.append(
                                    "Solide Cash-Position"
                                )

                        # Wachstum
                        if umsatzwachstum is not None:

                            if umsatzwachstum > 0.10:
                                score += 15
                                gruende.append(
                                    "Umsatzwachstum >10 %"
                                )

                            elif umsatzwachstum > 0:
                                score += 8
                                gruende.append(
                                    "Umsatz wächst"
                                )

                        # KGV
                        if kgv is not None:

                            if 0 < kgv <= 15:
                                score += 10
                                gruende.append(
                                    "Günstiges KGV"
                                )

                            elif 15 < kgv <= 25:
                                score += 5

                        # Liquidität
                        if volumen is not None:

                            if volumen >= 500000:
                                score += 5
                                gruende.append(
                                    "Gute Handelsliquidität"
                                )

                        score = min(score, 100)

                        # Einfache Ampel
                        if score >= 75:
                            bewertung = "🟢 Interessant"

                        elif score >= 50:
                            bewertung = "🟡 Prüfen"

                        else:
                            bewertung = "🔴 Risiko"

                        waehrung = (
                            "CHF"
                            if markt == "🇨🇭 Schweiz"
                            else "$"
                        )

                        kandidaten.append(
                            {
                                "Symbol": symbol,
                                "Firma": info.get(
                                    "shortName",
                                    symbol
                                ),
                                f"Kurs {waehrung}": round(
                                    preis, 2
                                ),
                                "Marktkap. Mio.": round(
                                    marketcap / 1_000_000,
                                    1
                                )
                                if marketcap else None,
                                "KGV": round(kgv, 1)
                                if kgv else None,
                                "Gewinn": (
                                    "✅"
                                    if netto is not None
                                    and netto > 0
                                    else "❌"
                                ),
                                "Cash > Schulden": (
                                    "✅"
                                    if cash is not None
                                    and schulden is not None
                                    and cash > schulden
                                    else "❌"
                                ),
                                "Cashflow": (
                                    "✅"
                                    if cashflow is not None
                                    and cashflow > 0
                                    else "❌"
                                ),
                                "Score": score,
                                "Bewertung": bewertung,
                                "Warum interessant?":
                                    ", ".join(gruende)
                            }
                        )

                    except Exception:
                        pass

                    fortschritt.progress(
                        (i + 1) / len(quotes)
                    )

                fortschritt.empty()

                if kandidaten:

                    df = pd.DataFrame(kandidaten)

                    df = df.sort_values(
                        ["Score", "Marktkap. Mio."],
                        ascending=[False, False]
                    )

                    df = df.head(anzahl)

                    st.subheader("⭐ Gefundene Kandidaten")

                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.caption(
                        "🟢 = interessant | 🟡 = genauer prüfen | "
                        "🔴 = erhöhtes Risiko. "
                        "Der Score ist keine Kaufempfehlung."
                    )

                else:

                    st.warning(
                        "Mit diesen Kriterien wurden keine "
                        "geeigneten Kandidaten gefunden."
                    )

            except Exception as e:

                st.error(
                    "Beim Abrufen der Börsendaten ist "
                    "ein Fehler aufgetreten."
                )

                st.code(str(e))


# ==========================================================
# BIOTECH
# ==========================================================

elif bereich == "🧬 Biotech-Perlen":

    st.header("🧬 Biotech-Perlen")

    st.write(
        "Hier suchen wir nach kleinen Biotech-Unternehmen "
        "mit interessanter Pipeline und wichtigen Katalysatoren."
    )

    st.info(
        "📅 Als Nächstes integrieren wir FDA-/PDUFA-Termine, "
        "klinische Studiendaten, Cash-Runway und Verschuldung."
    )


# ==========================================================
# SPACE
# ==========================================================

elif bereich == "🚀 Space / SpaceX":

    st.header("🚀 Space / SpaceX-Chancen")

    st.write(
        "Hier suchen wir nach börsennotierten Unternehmen "
        "aus Raumfahrt, Satelliten und der SpaceX-/Starlink-"
        "Lieferkette."
    )

    st.info(
        "🚀 Geplant: SpaceX-Bezug, Aufträge, Umsatzwachstum, "
        "Cash und Verschuldung."
    )
