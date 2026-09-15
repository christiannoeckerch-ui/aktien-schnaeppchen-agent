import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Aktien-Schnäppchen-Agent",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Aktien-Schnäppchen-Agent")
st.write("Der Agent sucht interessante Aktien und bewertet Chancen und Risiken.")

bereich = st.radio(
    "Was möchtest du durchsuchen?",
    ["💰 Schnäppchen", "🧬 Biotech-Perlen", "🚀 Space / SpaceX"],
    horizontal=True
)

# ============================================================
# SCHNÄPPCHEN
# ============================================================

if bereich == "💰 Schnäppchen":

    st.header("💰 Qualitäts-Schnäppchen")

    st.write(
        "Gesucht werden günstige Aktien. Bevorzugt werden Firmen mit "
        "Gewinn, positivem Cashflow, viel Cash und geringer Verschuldung."
    )

    markt = st.radio(
        "Markt auswählen",
        ["🇺🇸 USA", "🇨🇭 Schweiz"],
        horizontal=True
    )

    waehrung = "$" if markt == "🇺🇸 USA" else "CHF"

    col1, col2, col3 = st.columns(3)

    with col1:
        max_preis = st.number_input(
            f"Maximaler Aktienkurs ({waehrung})",
            min_value=0.50,
            max_value=20.00,
            value=5.00,
            step=0.50
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
        max_treffer = st.slider(
            "Max. Treffer",
            5, 50, 20, 5
        )

    st.info(
        "🟢 Top-Kandidat = mindestens 75 Punkte | "
        "🟡 Beobachten = 50–74 Punkte"
    )

    if st.button("🔎 Schnäppchen suchen", type="primary"):

        kandidaten = []

        # --------------------------------------------------------
        # AUSGANGSLISTE
        # --------------------------------------------------------

        if markt == "🇺🇸 USA":

            try:
                query = yf.EquityQuery(
                    "and",
                    [
                        yf.EquityQuery(
                            "gte",
                            ["intradayprice", 0.50]
                        ),
                        yf.EquityQuery(
                            "lte",
                            ["intradayprice", max_preis]
                        ),
                        yf.EquityQuery(
                            "gte",
                            [
                                "intradaymarketcap",
                                min_marktkap * 1_000_000
                            ]
                        )
                    ]
                )

                response = yf.screen(
                    query,
                    size=250,
                    sortField="intradaymarketcap",
                    sortAsc=False
                )

                quotes = response.get("quotes", [])

            except Exception as e:
                st.error(f"Fehler bei der USA-Suche: {e}")
                quotes = []

        else:

            swiss_symbols = [
                "IDIA.SW",
                "AMS.SW",
                "ARYN.SW",
                "MBTN.SW",
                "MOLN.SW"
            ]

            quotes = [{"symbol": s} for s in swiss_symbols]

        # --------------------------------------------------------
        # ANALYSE
        # --------------------------------------------------------

        if not quotes:

            st.warning("Die Börsensuche hat keine Aktien geliefert.")

        else:

            progress = st.progress(0)

            for nummer, quote in enumerate(quotes):

                symbol = quote.get("symbol")

                try:

                    if not symbol:
                        continue

                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    preis = info.get("currentPrice")

                    if preis is None:
                        preis = info.get("regularMarketPrice")

                    marketcap = info.get("marketCap")

                    if preis is None or marketcap is None:
                        continue

                    if not (0.50 <= preis <= max_preis):
                        continue

                    if marketcap < min_marktkap * 1_000_000:
                        continue

                    exchange = str(
                        info.get("exchange", "")
                    ).upper()

                    # Nur reguläre US-Börsen
                    if markt == "🇺🇸 USA":

                        erlaubte_boersen = {
                            "NMS",
                            "NGM",
                            "NCM",
                            "NYQ",
                            "ASE",
                            "NAS"
                        }

                        if exchange not in erlaubte_boersen:
                            continue

                    # Fundamentaldaten
                    netto = info.get("netIncomeToCommon")
                    cash = info.get("totalCash")
                    schulden = info.get("totalDebt")
                    cashflow = info.get("operatingCashflow")
                    wachstum = info.get("revenueGrowth")
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
                            gruende.append("Mehr Cash als Schulden")

                        elif cash > schulden * 0.5:
                            score += 10
                            gruende.append("Solide Cash-Position")

                    # Umsatzwachstum
                    if wachstum is not None:

                        if wachstum > 0.10:
                            score += 15
                            gruende.append("Umsatzwachstum >10 %")

                        elif wachstum > 0:
                            score += 8
                            gruende.append("Umsatz wächst")

                    # KGV
                    if kgv is not None:

                        if 0 < kgv <= 15:
                            score += 10
                            gruende.append("Günstiges KGV")

                        elif 15 < kgv <= 25:
                            score += 5

                    # Liquidität
                    if volumen is not None and volumen >= 500000:
                        score += 5
                        gruende.append("Gute Liquidität")

                    score = min(score, 100)

                    # --------------------------------------------
                    # WICHTIG:
                    # Unter 50 Punkten kein Schnäppchen-Kandidat
                    # --------------------------------------------

                    if score < 50:
                        continue

                    if score >= 75:
                        bewertung = "🟢 Top-Kandidat"
                    else:
                        bewertung = "🟡 Beobachten"

                    kandidaten.append(
                        {
                            "Symbol": symbol,
                            "Firma": info.get("shortName", symbol),
                            f"Kurs {waehrung}": round(float(preis), 2),
                            "Marktkap. Mio.": round(
                                marketcap / 1_000_000, 1
                            ),
                            "Börse": exchange,
                            "KGV": (
                                round(float(kgv), 1)
                                if kgv is not None
                                else None
                            ),
                            "Gewinn": (
                                "✅"
                                if netto is not None and netto > 0
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
                            "Warum interessant?": ", ".join(gruende)
                        }
                    )

                except Exception:
                    pass

                finally:
                    progress.progress(
                        (nummer + 1) / len(quotes)
                    )

            progress.empty()

            # ----------------------------------------------------
            # ERGEBNIS
            # ----------------------------------------------------

            if kandidaten:

                df = pd.DataFrame(kandidaten)

                df = df.sort_values(
                    ["Score", "Marktkap. Mio."],
                    ascending=[False, False]
                )

                df = df.head(max_treffer)

                top = df[df["Score"] >= 75]
                beobachten = df[
                    (df["Score"] >= 50) &
                    (df["Score"] < 75)
                ]

                if not top.empty:

                    st.subheader("🟢 Top-Kandidaten")

                    st.dataframe(
                        top,
                        use_container_width=True,
                        hide_index=True
                    )

                if not beobachten.empty:

                    st.subheader("🟡 Beobachtungsliste")

                    st.dataframe(
                        beobachten,
                        use_container_width=True,
                        hide_index=True
                    )

                st.caption(
                    "Der Score ist unser eigener Filter und keine "
                    "Kaufempfehlung. Ein Treffer sollte anschließend "
                    "genauer analysiert werden."
                )

            else:

                st.warning(
                    "Keine Qualitäts-Schnäppchen mit mindestens "
                    "50 Punkten gefunden. Das ist ebenfalls ein "
                    "sinnvolles Ergebnis – wir lockern die Qualitätskriterien "
                    "nicht nur, um Treffer zu produzieren."
                )


# ============================================================
# BIOTECH
# ============================================================

elif bereich == "🧬 Biotech-Perlen":

    st.header("🧬 Biotech-Perlen")

    st.write(
        "Hier suchen wir später gezielt nach kleinen "
        "Biotech-Unternehmen mit interessanter Pipeline."
    )

    st.info(
        "📅 Geplant: FDA-/PDUFA-Termine, Studiendaten, "
        "Cash-Runway und Verschuldung."
    )


# ============================================================
# SPACE
# ============================================================

elif bereich == "🚀 Space / SpaceX":

    st.header("🚀 Space / SpaceX-Chancen")

    st.write(
        "Hier suchen wir später nach börsennotierten Unternehmen "
        "aus Raumfahrt, Satelliten und dem SpaceX-/Starlink-Umfeld."
    )

    st.info(
        "🚀 Geplant: SpaceX-Bezug, Aufträge, Umsatzwachstum, "
        "Gewinn, Cash und Verschuldung."
    )
