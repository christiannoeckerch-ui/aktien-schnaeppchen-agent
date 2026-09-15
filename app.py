import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Aktien-Schnäppchen-Agent",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Aktien-Schnäppchen-Agent")
st.write(
    "Der Agent sucht günstige Aktien und bewertet Qualität, "
    "Bilanz, Wachstum, Bewertung und Verwässerung."
)

bereich = st.radio(
    "Was möchtest du durchsuchen?",
    ["💰 Schnäppchen", "🧬 Biotech-Perlen", "🚀 Space / SpaceX"],
    horizontal=True
)


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def prozent(wert):
    if wert is None:
        return None
    try:
        return round(float(wert) * 100, 1)
    except Exception:
        return None


def zahl(wert, stellen=1):
    if wert is None:
        return None
    try:
        return round(float(wert), stellen)
    except Exception:
        return None


def verwasserung_berechnen(ticker):
    """
    Vergleicht die jüngste verfügbare Aktienzahl ungefähr
    mit der Aktienzahl vor einem Jahr.

    Rückgabe:
    Prozentuale Veränderung oder None, wenn Yahoo
    keine ausreichenden Daten liefert.
    """

    try:
        shares = ticker.get_shares_full(
            start=(
                pd.Timestamp.today()
                - pd.DateOffset(years=2)
            ).strftime("%Y-%m-%d")
        )

        if shares is None or len(shares) < 2:
            return None

        shares = shares.dropna().sort_index()

        if len(shares) < 2:
            return None

        aktuell = float(shares.iloc[-1])
        aktuelles_datum = shares.index[-1]

        ziel_datum = aktuelles_datum - pd.DateOffset(years=1)

        alte_daten = shares[
            shares.index <= ziel_datum
        ]

        if alte_daten.empty:
            return None

        vorjahr = float(alte_daten.iloc[-1])

        if vorjahr <= 0:
            return None

        veraenderung = (
            (aktuell - vorjahr) / vorjahr
        ) * 100

        return round(veraenderung, 1)

    except Exception:
        return None


# ============================================================
# SCHNÄPPCHEN
# ============================================================

if bereich == "💰 Schnäppchen":

    st.header("💰 Qualitäts-Schnäppchen")

    st.write(
        "Gesucht werden günstige Aktien mit Profitabilität, "
        "gesundem Cashflow, vernünftiger Verschuldung, Wachstum "
        "und attraktiver Bewertung."
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
        # AKTIENUNIVERSUM
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
                st.error(
                    f"Fehler bei der USA-Suche: {e}"
                )
                quotes = []

        else:

            swiss_symbols = [
                "IDIA.SW",
                "AMS.SW",
                "ARYN.SW",
                "MBTN.SW",
                "MOLN.SW"
            ]

            quotes = [
                {"symbol": s}
                for s in swiss_symbols
            ]

        # --------------------------------------------------------
        # ANALYSE
        # --------------------------------------------------------

        if not quotes:

            st.warning(
                "Die Börsensuche hat keine Aktien geliefert."
            )

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
                        preis = info.get(
                            "regularMarketPrice"
                        )

                    marketcap = info.get("marketCap")

                    if preis is None or marketcap is None:
                        continue

                    if not (
                        0.50 <= preis <= max_preis
                    ):
                        continue

                    if (
                        marketcap
                        < min_marktkap * 1_000_000
                    ):
                        continue

                    exchange = str(
                        info.get("exchange", "")
                    ).upper()

                    if markt == "🇺🇸 USA":

                        erlaubte_boersen = {
                            "NMS",
                            "NGM",
                            "NCM",
                            "NYQ",
                            "ASE",
                            "NAS"
                        }

                        if (
                            exchange
                            not in erlaubte_boersen
                        ):
                            continue

                    # --------------------------------------------
                    # BRANCHE
                    # --------------------------------------------

                    sector = str(
                        info.get("sector", "")
                    ).lower()

                    industry = str(
                        info.get("industry", "")
                    ).lower()

                    finanzunternehmen = (
                        "financial" in sector
                        or "bank" in industry
                        or "insurance" in industry
                    )

                    # --------------------------------------------
                    # FUNDAMENTALDATEN
                    # --------------------------------------------

                    netto = info.get(
                        "netIncomeToCommon"
                    )

                    cash = info.get(
                        "totalCash"
                    )

                    schulden = info.get(
                        "totalDebt"
                    )

                    operativer_cashflow = info.get(
                        "operatingCashflow"
                    )

                    free_cashflow = info.get(
                        "freeCashflow"
                    )

                    umsatzwachstum = info.get(
                        "revenueGrowth"
                    )

                    gewinnwachstum = info.get(
                        "earningsGrowth"
                    )

                    gewinnmarge = info.get(
                        "profitMargins"
                    )

                    roe = info.get(
                        "returnOnEquity"
                    )

                    kgv = info.get(
                        "trailingPE"
                    )

                    kuv = info.get(
                        "priceToSalesTrailing12Months"
                    )

                    debt_equity = info.get(
                        "debtToEquity"
                    )

                    volumen = info.get(
                        "averageVolume"
                    )

                    score = 0
                    gruende = []
                    warnungen = []

                    # ============================================
                    # 1. PROFITABILITÄT
                    # ============================================

                    if (
                        netto is not None
                        and netto > 0
                    ):
                        score += 12
                        gruende.append(
                            "Gewinn positiv"
                        )

                    if gewinnmarge is not None:

                        if gewinnmarge >= 0.15:
                            score += 8
                            gruende.append(
                                "Starke Gewinnmarge"
                            )

                        elif gewinnmarge >= 0.05:
                            score += 5
                            gruende.append(
                                "Positive Gewinnmarge"
                            )

                        elif gewinnmarge < 0:
                            score -= 5
                            warnungen.append(
                                "Negative Marge"
                            )

                    if roe is not None:

                        if roe >= 0.15:
                            score += 7
                            gruende.append(
                                "ROE >15 %"
                            )

                        elif roe >= 0.08:
                            score += 4

                    # ============================================
                    # 2. CASHFLOW
                    # ============================================

                    if not finanzunternehmen:

                        if (
                            operativer_cashflow
                            is not None
                            and operativer_cashflow > 0
                        ):
                            score += 8
                            gruende.append(
                                "Operativer Cashflow positiv"
                            )

                        elif (
                            operativer_cashflow
                            is not None
                            and operativer_cashflow < 0
                        ):
                            score -= 4
                            warnungen.append(
                                "Negativer operativer Cashflow"
                            )

                        if (
                            free_cashflow is not None
                            and free_cashflow > 0
                        ):
                            score += 10
                            gruende.append(
                                "Free Cashflow positiv"
                            )

                        elif (
                            free_cashflow is not None
                            and free_cashflow < 0
                        ):
                            score -= 6
                            warnungen.append(
                                "Free Cashflow negativ"
                            )

                    # ============================================
                    # 3. BILANZ / SCHULDEN
                    # ============================================

                    if not finanzunternehmen:

                        if (
                            cash is not None
                            and schulden is not None
                        ):

                            if schulden == 0:
                                score += 12
                                gruende.append(
                                    "Keine Finanzschulden"
                                )

                            elif cash > schulden:
                                score += 12
                                gruende.append(
                                    "Mehr Cash als Schulden"
                                )

                            elif cash > schulden * 0.5:
                                score += 5
                                gruende.append(
                                    "Solide Cash-Position"
                                )

                        if debt_equity is not None:

                            if debt_equity <= 50:
                                score += 5
                                gruende.append(
                                    "Niedrige Verschuldung"
                                )

                            elif debt_equity > 150:
                                score -= 6
                                warnungen.append(
                                    "Hohe Verschuldung"
                                )

                    else:

                        warnungen.append(
                            "Finanzunternehmen: "
                            "Bilanz separat beurteilen"
                        )

                    # ============================================
                    # 4. WACHSTUM
                    # ============================================

                    if umsatzwachstum is not None:

                        if umsatzwachstum > 0.20:
                            score += 10
                            gruende.append(
                                "Umsatzwachstum >20 %"
                            )

                        elif umsatzwachstum > 0.10:
                            score += 7
                            gruende.append(
                                "Umsatzwachstum >10 %"
                            )

                        elif umsatzwachstum > 0:
                            score += 3

                        elif umsatzwachstum < -0.10:
                            score -= 5
                            warnungen.append(
                                "Umsatz deutlich rückläufig"
                            )

                    if gewinnwachstum is not None:

                        if gewinnwachstum > 0.20:
                            score += 10
                            gruende.append(
                                "Gewinnwachstum >20 %"
                            )

                        elif gewinnwachstum > 0.10:
                            score += 7
                            gruende.append(
                                "Gewinnwachstum >10 %"
                            )

                        elif gewinnwachstum > 0:
                            score += 3

                        elif gewinnwachstum < -0.10:
                            score -= 5
                            warnungen.append(
                                "Gewinn deutlich rückläufig"
                            )

                    # ============================================
                    # 5. BEWERTUNG
                    # ============================================

                    if kgv is not None:

                        if 0 < kgv <= 12:
                            score += 8
                            gruende.append(
                                "Niedriges KGV"
                            )

                        elif 12 < kgv <= 20:
                            score += 5
                            gruende.append(
                                "Moderates KGV"
                            )

                        elif kgv > 35:
                            score -= 3
                            warnungen.append(
                                "Hohes KGV"
                            )

                    if kuv is not None:

                        if 0 < kuv <= 1:
                            score += 7
                            gruende.append(
                                "KUV unter 1"
                            )

                        elif 1 < kuv <= 2:
                            score += 4
                            gruende.append(
                                "Moderates KUV"
                            )

                        elif kuv > 5:
                            score -= 3
                            warnungen.append(
                                "Hohes KUV"
                            )

                    # ============================================
                    # 6. HANDELSLIQUIDITÄT
                    # ============================================

                    if volumen is not None:

                        if volumen >= 500000:
                            score += 3

                        elif volumen < 50000:
                            score -= 3
                            warnungen.append(
                                "Geringes Handelsvolumen"
                            )

                    # ============================================
                    # 7. VERWÄSSERUNG
                    # ============================================
                    #
                    # Diese Abfrage machen wir nur bei Aktien,
                    # die bis hierhin grundsätzlich interessant
                    # aussehen. Dadurch wird die Suche schneller.
                    # ============================================

                    verwasserung = None

                    if score >= 40:

                        verwasserung = (
                            verwasserung_berechnen(
                                ticker
                            )
                        )

                        if verwasserung is not None:

                            if verwasserung <= -5:
                                score += 3
                                gruende.append(
                                    "Aktienzahl gesunken"
                                )

                            elif verwasserung <= 5:
                                gruende.append(
                                    "Aktienzahl stabil"
                                )

                            elif verwasserung <= 10:
                                score -= 2
                                warnungen.append(
                                    "Leichte Verwässerung"
                                )

                            elif verwasserung <= 25:
                                score -= 5
                                warnungen.append(
                                    "Deutliche Verwässerung"
                                )

                            else:
                                score -= 10
                                warnungen.append(
                                    "Sehr starke Verwässerung"
                                )

                    # ============================================
                    # SCORE BEGRENZEN
                    # ============================================

                    score = max(
                        0,
                        min(score, 100)
                    )

                    if score < 50:
                        continue

                    if score >= 75:
                        bewertung = (
                            "🟢 Top-Kandidat"
                        )
                    else:
                        bewertung = (
                            "🟡 Beobachten"
                        )

                    # --------------------------------------------
                    # VERWÄSSERUNGSANZEIGE
                    # --------------------------------------------

                    if verwasserung is None:
                        verwasserung_text = "k.A."

                    elif verwasserung > 0:
                        verwasserung_text = (
                            f"+{verwasserung:.1f} %"
                        )

                    else:
                        verwasserung_text = (
                            f"{verwasserung:.1f} %"
                        )

                    # ============================================
                    # AUSGABE
                    # ============================================

                    kandidaten.append(
                        {
                            "Symbol": symbol,

                            "Firma": info.get(
                                "shortName",
                                symbol
                            ),

                            f"Kurs {waehrung}": round(
                                float(preis),
                                2
                            ),

                            "Marktkap. Mio.": round(
                                marketcap
                                / 1_000_000,
                                1
                            ),

                            "Typ": (
                                "🏦 Finanz"
                                if finanzunternehmen
                                else "🏢 Normal"
                            ),

                            "KGV": zahl(kgv),

                            "KUV": zahl(
                                kuv,
                                2
                            ),

                            "Marge %": prozent(
                                gewinnmarge
                            ),

                            "ROE %": prozent(
                                roe
                            ),

                            "Umsatzwachstum %":
                                prozent(
                                    umsatzwachstum
                                ),

                            "Gewinnwachstum %":
                                prozent(
                                    gewinnwachstum
                                ),

                            "Free Cashflow": (
                                "➖"
                                if (
                                    finanzunternehmen
                                    or free_cashflow
                                    is None
                                )
                                else (
                                    "✅"
                                    if free_cashflow > 0
                                    else "❌"
                                )
                            ),

                            "Cash > Schulden": (
                                "➖"
                                if (
                                    finanzunternehmen
                                    or cash is None
                                    or schulden is None
                                )
                                else (
                                    "✅"
                                    if cash > schulden
                                    else "❌"
                                )
                            ),

                            "Debt/Equity": (
                                None
                                if finanzunternehmen
                                else zahl(
                                    debt_equity,
                                    1
                                )
                            ),

                            "Aktienzahl 1J":
                                verwasserung_text,

                            "Score": score,

                            "Bewertung":
                                bewertung,

                            "Stärken":
                                ", ".join(
                                    gruende
                                ),

                            "Risiken":
                                ", ".join(
                                    warnungen
                                )
                        }
                    )

                except Exception:
                    pass

                finally:

                    progress.progress(
                        (nummer + 1)
                        / len(quotes)
                    )

            progress.empty()

            # ====================================================
            # ERGEBNIS
            # ====================================================

            if kandidaten:

                df = pd.DataFrame(
                    kandidaten
                )

                df = df.sort_values(
                    [
                        "Score",
                        "Marktkap. Mio."
                    ],
                    ascending=[
                        False,
                        False
                    ]
                )

                df = df.head(
                    max_treffer
                )

                top = df[
                    df["Score"] >= 75
                ]

                beobachten = df[
                    (df["Score"] >= 50)
                    & (df["Score"] < 75)
                ]

                if not top.empty:

                    st.subheader(
                        "🟢 Top-Kandidaten"
                    )

                    st.dataframe(
                        top,
                        use_container_width=True,
                        hide_index=True
                    )

                if not beobachten.empty:

                    st.subheader(
                        "🟡 Beobachtungsliste"
                    )

                    st.dataframe(
                        beobachten,
                        use_container_width=True,
                        hide_index=True
                    )

                st.caption(
                    "Aktienzahl 1J zeigt die ungefähre "
                    "Veränderung der ausstehenden Aktien über "
                    "ein Jahr. Positive Werte bedeuten "
                    "Verwässerung. k.A. bedeutet, dass Yahoo "
                    "keine ausreichenden historischen Daten "
                    "geliefert hat."
                )

                st.caption(
                    "Der Score ist ein automatischer Vorfilter "
                    "und keine Kaufempfehlung. Yahoo-Finance-"
                    "Daten können fehlen oder fehlerhaft sein "
                    "und sollten überprüft werden."
                )

            else:

                st.warning(
                    "Keine Qualitäts-Schnäppchen mit "
                    "mindestens 50 Punkten gefunden."
                )


# ============================================================
# BIOTECH
# ============================================================

elif bereich == "🧬 Biotech-Perlen":

    st.header(
        "🧬 Biotech-Perlen"
    )

    st.write(
        "Biotech-Unternehmen erhalten einen eigenen "
        "Bewertungsansatz, weil Gewinn und KGV bei "
        "Entwicklungsfirmen häufig wenig aussagekräftig sind."
    )

    st.info(
        "📅 Nächster Ausbau: FDA-/PDUFA-Termine, "
        "klinische Studien, Pipeline, Cash-Runway, "
        "Partnerschaften und Verwässerungsrisiko."
    )


# ============================================================
# SPACE
# ============================================================

elif bereich == "🚀 Space / SpaceX":

    st.header(
        "🚀 Space / SpaceX-Chancen"
    )

    st.write(
        "Hier suchen wir nach börsennotierten "
        "Unternehmen aus Raumfahrt, Satelliten "
        "und dem SpaceX-/Starlink-Umfeld."
    )

    st.info(
        "🚀 Geplant: SpaceX-/Starlink-Bezug, "
        "Aufträge, Umsatzwachstum, Cash, "
        "Verschuldung und Bewertung."
    )
