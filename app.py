import streamlit as st
import yfinance as yf
import pandas as pd
import math

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
    ["💰 Schnäppchen", "🧬 Biotech-Perlen", "🚀 Space / Rechenzentren"],
    horizontal=True
)


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def kursauswahl(waehrung, key):
    auswahl = st.radio(
        "Kursgrenze",
        [f"Bis 5 {waehrung}", f"Bis 10 {waehrung}", "Eigene Grenze"],
        key=f"{key}_preset",
    )
    if auswahl == f"Bis 5 {waehrung}":
        grenze = 5.0
    elif auswahl == f"Bis 10 {waehrung}":
        grenze = 10.0
    else:
        grenze = st.number_input(
            f"Maximaler Aktienkurs ({waehrung})", min_value=0.5,
            max_value=1000.0, value=10.0, step=0.5, key=f"{key}_custom",
        )
    st.caption(f"0,50 bis einschließlich {grenze:g} {waehrung}")
    return grenze


def finanz_einstufung(years, cash, debt, dilution):
    """Transparenter Finanzvorfilter, kein Gesamturteil über das Unternehmen."""
    hinweise = []
    if years is None or not math.isfinite(years):
        hinweise.append("Cash-Reichweite nicht berechenbar")
    elif years < 2:
        hinweise.append("Cash-Reichweite unter 2 Jahren")
    if (cash is None or debt is None or not math.isfinite(cash)
            or not math.isfinite(debt) or cash <= 0 or debt < 0):
        hinweise.append("Cash-/Schuldendaten fehlen oder sind nicht ausreichend")
    elif debt > cash:
        hinweise.append("Schulden über Cash")
    if dilution is None or not math.isfinite(dilution):
        hinweise.append("Aktienzahlvergleich fehlt")
    elif dilution > 5:
        hinweise.append("Aktienzahlzuwachs über 5 %")
    if hinweise:
        return "Beobachten", "; ".join(hinweise)
    return "Top-Kandidat", "Runway ≥2 Jahre; Schulden ≤Cash; Aktienzahlzuwachs ≤5 %"


def themen_ergebnisse(ergebnisse, kurswaehrung, max_treffer):
    st.caption("Vorläufiger Finanzvorfilter: Top-Kandidat nur bei berechenbarer Cash-Reichweite ab 2 Jahren, positivem Cash, Schulden höchstens Cash und Aktienzahlzuwachs höchstens 5 %. Sonst Beobachten, auch bei fehlenden Daten oder nicht negativem FCF. Kein Gesamturteil: Schuldenfälligkeiten, Bewertung und Geschäftsrisiken sind nicht geprüft.")
    frame = pd.DataFrame(ergebnisse)
    frame["_rang"] = frame["Einstufung"].map({"Top-Kandidat": 0, "Beobachten": 1})
    frame = frame.sort_values(["_rang", f"Marktkap. Mio. {kurswaehrung}"], ascending=[True, False]).head(max_treffer).drop(columns="_rang")
    for einstufung, titel in [("Top-Kandidat", "Top-Kandidaten · Finanzvorfilter"), ("Beobachten", "Beobachten")]:
        teil = frame[frame["Einstufung"] == einstufung]
        st.subheader(f"{titel} ({len(teil)})")
        if teil.empty:
            st.write("Keine Treffer in dieser Gruppe.")
        else:
            st.dataframe(teil, use_container_width=True, hide_index=True)


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

        shares = pd.to_numeric(shares, errors="coerce").dropna().sort_index()
        shares = shares[~shares.index.duplicated(keep="last")]
        shares = shares[shares.map(lambda value: math.isfinite(value) and value > 0)]

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

        # Avoid labelling stale or widely spaced observations as a 1-year change.
        heute = pd.Timestamp.now(tz=aktuelles_datum.tz)
        if (heute - aktuelles_datum).days > 120:
            return None
        if (ziel_datum - alte_daten.index[-1]).days > 90:
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
        max_preis = kursauswahl("USD" if markt == "🇺🇸 USA" else "CHF", "schnaeppchen")

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

    st.caption("USA: maximal 250 Kandidaten nach Marktkapitalisierung; Schweiz: feste Auswahlliste aus 5 Titeln, kein vollständiger Marktscan. Finanzunternehmen erhalten keine Cashflow- oder Bilanzpunkte; ihre Scores sind daher nur eingeschränkt vergleichbar.")
    if st.button("🔎 Schnäppchen suchen", type="primary"):

        kandidaten = []
        analyse_fehler = []

        # --------------------------------------------------------
        # AKTIENUNIVERSUM
        # --------------------------------------------------------

        if markt == "🇺🇸 USA":

            try:
                query = yf.EquityQuery(
                    "and",
                    [
                        yf.EquityQuery("is-in", ["exchange", "NMS", "NGM", "NCM", "NYQ", "ASE"]),
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

                            if 0 <= debt_equity <= 50:
                                score += 5
                                gruende.append(
                                    "Niedrige Verschuldung"
                                )

                            elif debt_equity < 0 or debt_equity > 150:
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

                except Exception as fehler:
                    analyse_fehler.append(f"{symbol}: {fehler}")

                finally:

                    progress.progress(
                        (nummer + 1)
                        / len(quotes)
                    )

            progress.empty()
            if analyse_fehler:
                st.warning(f"{len(analyse_fehler)} Aktien konnten nicht vollständig analysiert werden.")
                with st.expander("Datenfehler anzeigen"):
                    st.write(analyse_fehler)

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
    st.header("🧬 Biotech-Perlen")
    st.write("Biotech-Unternehmen mit Cash, Schulden, grobem Cash-Runway und Veränderung der Aktienzahl.")
    biotech_markt = st.radio("Markt auswählen", ["🇺🇸 USA", "🇨🇭 Schweiz"], horizontal=True, key="biotech_markt")
    biotech_ch = biotech_markt == "🇨🇭 Schweiz"
    kurswaehrung = "CHF" if biotech_ch else "USD"
    col1, col2, col3 = st.columns(3)
    with col1:
        max_preis = kursauswahl(kurswaehrung, "biotech")
    with col2:
        min_mcap = st.number_input(f"Mindest-Marktkapitalisierung (Mio. {kurswaehrung})", min_value=1, max_value=10000, value=50, step=10)
    with col3:
        max_treffer = st.slider("Max. Treffer", 5, 50, 20, 5)
    if biotech_ch:
        st.caption("Schweiz: feste Auswahl aus Idorsia, Molecular Partners, Addex und Basilea; kein vollständiger Marktscan. Kurs und Marktkapitalisierung in CHF. Auch hier gilt der Mindestkurs von 0,50 CHF.")
    else:
        st.caption("USA: Kurs ab 0,50 USD; maximal 250 Suchkandidaten nach Marktkapitalisierung. US-Notierung bedeutet nicht zwingend US-Firmensitz.")
    st.info("Runway = Cash / Betrag des negativen jährlichen Free Cashflows. Grobe Schätzung bei gleichbleibendem Verbrauch; Schuldenfälligkeiten und künftige Studienkosten sind nicht berücksichtigt. Pipeline und klinische Termine sind noch nicht bewertet.")

    def finite_number(value):
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except (ValueError, TypeError):
            return None

    def runway_ampel(years):
        if years is None or not math.isfinite(years) or years < 0:
            return "⚪ Nicht berechenbar"
        if years >= 2:
            return "🟢 Ab 2 Jahren"
        if years >= 1:
            return "🟡 1 bis unter 2 Jahre"
        return "🔴 Unter 1 Jahr"

    st.caption("Cash-Runway-Ampel: 🟢 ab 2 Jahren · 🟡 1 bis unter 2 Jahre · 🔴 unter 1 Jahr · ⚪ Daten fehlen oder FCF nicht negativ. Die Ampel bewertet nur die geschätzte Liquiditätsreichweite, nicht die Aktie insgesamt.")

    def schulden_ampel(cash, debt):
        """App-eigene Schwellen, kein Kreditrating oder Gesamturteil."""
        cash, debt = finite_number(cash), finite_number(debt)
        if cash is None or debt is None or cash < 0 or debt < 0:
            return "⚪ Daten fehlen / ungültig", None
        if debt == 0:
            return "🟢 Keine gemeldeten Schulden", 0.0 if cash > 0 else None
        if cash == 0:
            return "🔴 Schulden bei Cash = 0", None
        ratio = debt / cash
        if ratio <= 1:
            return "🟢 Schulden höchstens Cash", ratio
        if ratio <= 2:
            return "🟡 Schulden >1–2× Cash", ratio
        return "🔴 Schulden über 2× Cash", ratio

    st.caption("Schuldenampel (eigene, grobe Schwellen): 🟢 Schulden höchstens Cash · 🟡 über 1 bis 2× Cash · 🔴 über 2× Cash oder Schulden bei Cash = 0 · ⚪ Daten fehlen/ungültig. Keine gemeldeten Schulden werden separat grün markiert.")
    st.info("Beide Ampeln bewerten einzelne Kennzahlen. Schuldenfälligkeiten werden nicht abgerufen; es gibt daher keine grüne Gesamtbewertung. Eine grüne Schuldenampel bedeutet nicht, dass das Unternehmen ausreichend Cash für den Betrieb hat.")

    def runway(cash, fcf):
        if fcf is None:
            return None, "FCF fehlt"
        if fcf >= 0:
            return None, "FCF nicht negativ; keine Runway ableitbar"
        if cash is None or cash < 0:
            return None, "Cash fehlt / ungültig"
        years = cash / abs(fcf)
        return years, "Unter 1 Jahr" if years < 1 else "Aus negativem FCF geschätzt"

    if st.button("🔎 Biotech-Perlen suchen", type="primary"):
        ergebnisse, fehler_liste = [], []
        try:
            with st.spinner("Biotech-Unternehmen werden gesucht und analysiert …"):
                if biotech_ch:
                    quotes = [{"symbol": symbol} for symbol in ["IDIA.SW", "MOLN.SW", "ADXN.SW", "BSLN.SW"]]
                else:
                    query = yf.EquityQuery("and", [
                        yf.EquityQuery("eq", ["industry", "Biotechnology"]),
                        yf.EquityQuery("is-in", ["exchange", "NMS", "NGM", "NCM", "NYQ", "ASE"]),
                        yf.EquityQuery("gte", ["intradayprice", 0.5]),
                        yf.EquityQuery("lte", ["intradayprice", max_preis]),
                        yf.EquityQuery("gte", ["intradaymarketcap", min_mcap * 1_000_000]),
                    ])
                    response = yf.screen(query, size=250, sortField="intradaymarketcap", sortAsc=False)
                    quotes = response.get("quotes", [])
                for quote in quotes:
                    symbol = quote.get("symbol")
                    if not symbol:
                        continue
                    ticker = yf.Ticker(symbol)
                    try:
                        info = ticker.info or {}
                    except Exception as error:
                        info = {}
                        fehler_liste.append(f"{symbol}: {error}")
                    price = finite_number(quote.get("regularMarketPrice", quote.get("intradayprice")))
                    mcap = finite_number(quote.get("marketCap", quote.get("intradaymarketcap")))
                    if biotech_ch:
                        price = finite_number(info.get("currentPrice"))
                        if price is None:
                            price = finite_number(info.get("regularMarketPrice"))
                        mcap = finite_number(info.get("marketCap"))
                        if info.get("currency") != "CHF":
                            fehler_liste.append(f"{symbol}: CHF-Kurswährung nicht bestätigt")
                            continue
                    if price is None or mcap is None:
                        fehler_liste.append(f"{symbol}: Kurs oder Marktkapitalisierung fehlt")
                        continue
                    if not (0.5 <= price <= max_preis) or mcap < min_mcap * 1_000_000:
                        continue
                    cash = finite_number(info.get("totalCash"))
                    debt = finite_number(info.get("totalDebt"))
                    fcf = finite_number(info.get("freeCashflow"))
                    years, status = runway(cash, fcf)
                    debt_light, debt_ratio = schulden_ampel(cash, debt)
                    dilution = verwasserung_berechnen(ticker)
                    einstufung, grund = finanz_einstufung(years, cash, debt, dilution)
                    ergebnisse.append({
                        "Einstufung": einstufung,
                        "Einstufungsgrund": grund,
                        "Runway-Ampel": runway_ampel(years),
                        "Schulden-Ampel": debt_light,
                        "Symbol": symbol,
                        "Firma": info.get("shortName") or quote.get("shortName") or symbol,
                        f"Kurs {kurswaehrung}": round(price, 2),
                        f"Marktkap. Mio. {kurswaehrung}": round(mcap / 1_000_000, 1),
                        "Bilanzwährung": info.get("financialCurrency") or "k.A.",
                        "Cash Mio.": zahl(cash / 1_000_000) if cash is not None else None,
                        "Schulden Mio.": zahl(debt / 1_000_000) if debt is not None else None,
                        "Schulden / Cash (×)": zahl(debt_ratio, 2),
                        "Free Cashflow Mio.": zahl(fcf / 1_000_000) if fcf is not None else None,
                        "Cash-Runway Jahre": zahl(years, 2),
                        "Runway-Hinweis": status,
                        "Aktienzahl 1J %": dilution,
                        "Börse": info.get("exchange") or quote.get("exchange", "k.A."),
                    })
            if ergebnisse:
                themen_ergebnisse(ergebnisse, kurswaehrung, max_treffer)
            else:
                st.warning("Mit diesen Einstellungen wurden keine Biotech-Unternehmen gefunden.")
            if fehler_liste:
                st.warning("Bei einigen Titeln fehlen Daten. Leere Werte bedeuten unbekannt, nicht null.")
                with st.expander("Datenfehler anzeigen"):
                    st.write(fehler_liste)
        except Exception as error:
            st.error(f"Biotech-Suche derzeit nicht verfügbar: {error}")
    st.caption("Cash, Schulden und FCF sind in der jeweiligen Bilanzwährung angegeben. Cash-Runway verwendet dieselbe Währung für Zähler und Nenner. Yahoo kann unterschiedliche Berichtsstände liefern; FCF ist die von Yahoo gelieferte jährliche Kennzahl, keine Prognose.")
    st.caption("Aktienzahl 1J: ungefähre Veränderung ausstehenden Kapitals anhand historischer Aktienzahlen. Positive Werte zeigen mehr Aktien; Splits, ADR-Änderungen und Datenfehler können den Vergleich verzerren. Fehlende oder zu alte Daten bleiben leer. Kein Biotech-Score und keine Kaufempfehlung.")

elif bereich == "🚀 Space / Rechenzentren":
    st.header("🚀 Space & Rechenzentren")
    st.write("Raumfahrtunternehmen und Zulieferer für Raumfahrt oder Rechenzentren mit zwei Finanzampeln.")
    markt = st.radio("Markt auswählen", ["🇺🇸 USA", "🇨🇭 Schweiz"], horizontal=True, key="space_markt")
    thema = st.radio("Thema auswählen", ["Beides", "Raumfahrt", "Rechenzentren"], horizontal=True, key="space_thema")
    kurswaehrung = "CHF" if markt == "🇨🇭 Schweiz" else "USD"
    # Manuell recherchierte Themenliste; keine Aussage über Umsatzanteile.
    universum = [
        ("RKLB", "Rocket Lab", "USD", ["Raumfahrt"], "Raketen und Raumfahrtsysteme", "https://investors.rocketlabcorp.com/resources/investor-faqs"),
        ("RDW", "Redwire", "USD", ["Raumfahrt"], "Raumfahrt- und Verteidigungstechnik", "https://ir.rdw.com/"),
        ("LUNR", "Intuitive Machines", "USD", ["Raumfahrt"], "Mondmissionen und Raumfahrtinfrastruktur", "https://investors.intuitivemachines.com/shareholder-services/investor-faqs"),
        ("PL", "Planet Labs", "USD", ["Raumfahrt"], "Erdbeobachtung mit Satelliten", "https://investors.planet.com/"),
        ("VRT", "Vertiv", "USD", ["Rechenzentren"], "Stromversorgung und Kühlung", "https://www.vertiv.com/"),
        ("CNTL.SW", "Centiel", "CHF", ["Rechenzentren"], "Unterbrechungsfreie Stromversorgung (USV)", "https://www.centiel.com/investors-media/share-details/"),
        ("HUBN.SW", "HUBER+SUHNER", "CHF", ["Raumfahrt", "Rechenzentren"], "Verbindungen für Satelliten und Rechenzentren", "https://www.hubersuhner.com/en/markets/communication/data-center/hyperscale"),
        ("ABBN.SW", "ABB", "CHF", ["Rechenzentren"], "Elektrifizierung und Energieverteilung", "https://new.abb.com/data-centers"),
    ]
    auswahl = [row for row in universum if row[2] == kurswaehrung and (thema == "Beides" or thema in row[3])]
    st.caption("Feste Themenliste, kein vollständiger Marktscan. Auch diversifizierte Zulieferer sind enthalten; die Aufnahme belegt keinen SpaceX-/Starlink-Bezug.")
    with st.expander("Enthaltene Unternehmen und Quellen"):
        for row in auswahl:
            st.markdown(f"- **{row[1]} ({row[0]})**: {row[4]} · [Quelle]({row[5]})")
    st.caption("Centiel: SIX-Symbol CNTL, Yahoo-Abfrage CNTL.SW. Falls Yahoo noch keine Daten bereitstellt, wird dies als Datenfehler angezeigt. Wegen der Fusion mit HT5 wird kein Aktienzahlvergleich 1J berechnet.")
    col1, col2, col3 = st.columns(3)
    with col1:
        max_preis = kursauswahl(kurswaehrung, "space")
    with col2:
        min_mcap = st.number_input(f"Mindest-Marktkapitalisierung (Mio. {kurswaehrung})", min_value=1, max_value=10000, value=50, step=10)
    with col3:
        max_treffer = st.slider("Max. Treffer", 5, 50, 20, 5)
    st.caption(f"Kurs ab 0,50 {kurswaehrung} bis einschließlich Obergrenze. Für günstige Titel die Obergrenze senken. Unternehmen außerhalb der Filter erscheinen nicht in der Ergebnistabelle.")
    st.info("Runway = Cash / Betrag des negativen jährlichen Free Cashflows. Grobe Schätzung bei gleichbleibendem Verbrauch; Schuldenfälligkeiten und künftige Projektkosten sind nicht berücksichtigt. Auftragsbestand, Starttermine und Projektrisiken sind noch nicht bewertet.")

    def finite_number(value):
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except (ValueError, TypeError):
            return None

    def runway_ampel(years):
        if years is None or not math.isfinite(years) or years < 0:
            return "⚪ Nicht berechenbar"
        if years >= 2:
            return "🟢 Ab 2 Jahren"
        if years >= 1:
            return "🟡 1 bis unter 2 Jahre"
        return "🔴 Unter 1 Jahr"

    st.caption("Cash-Runway-Ampel: 🟢 ab 2 Jahren · 🟡 1 bis unter 2 Jahre · 🔴 unter 1 Jahr · ⚪ Daten fehlen oder FCF nicht negativ. Die Ampel bewertet nur die geschätzte Liquiditätsreichweite, nicht die Aktie insgesamt.")

    def schulden_ampel(cash, debt):
        """App-eigene Schwellen, kein Kreditrating oder Gesamturteil."""
        cash, debt = finite_number(cash), finite_number(debt)
        if cash is None or debt is None or cash < 0 or debt < 0:
            return "⚪ Daten fehlen / ungültig", None
        if debt == 0:
            return "🟢 Keine gemeldeten Schulden", 0.0 if cash > 0 else None
        if cash == 0:
            return "🔴 Schulden bei Cash = 0", None
        ratio = debt / cash
        if ratio <= 1:
            return "🟢 Schulden höchstens Cash", ratio
        if ratio <= 2:
            return "🟡 Schulden >1–2× Cash", ratio
        return "🔴 Schulden über 2× Cash", ratio

    st.caption("Schuldenampel (eigene, grobe Schwellen): 🟢 Schulden höchstens Cash · 🟡 über 1 bis 2× Cash · 🔴 über 2× Cash oder Schulden bei Cash = 0 · ⚪ Daten fehlen/ungültig. Keine gemeldeten Schulden werden separat grün markiert.")
    st.info("Beide Ampeln bewerten einzelne Kennzahlen. Schuldenfälligkeiten werden nicht abgerufen; es gibt daher keine grüne Gesamtbewertung. Eine grüne Schuldenampel bedeutet nicht, dass das Unternehmen ausreichend Cash für den Betrieb hat.")

    def runway(cash, fcf):
        if fcf is None:
            return None, "FCF fehlt"
        if fcf >= 0:
            return None, "FCF nicht negativ; keine Runway ableitbar"
        if cash is None or cash < 0:
            return None, "Cash fehlt / ungültig"
        years = cash / abs(fcf)
        return years, "Unter 1 Jahr" if years < 1 else "Aus negativem FCF geschätzt"

    if st.button("🔎 Space-/Rechenzentren-Unternehmen suchen", type="primary"):
        ergebnisse, fehler_liste = [], []
        try:
            with st.spinner("Space-/Rechenzentren-Unternehmen werden gesucht und analysiert …"):
                quotes = [{"symbol": row[0], "shortName": row[1], "thema": ", ".join(row[3]), "bezug": row[4]} for row in auswahl]
                for quote in quotes:
                    symbol = quote.get("symbol")
                    if not symbol:
                        continue
                    ticker = yf.Ticker(symbol)
                    try:
                        info = ticker.info or {}
                    except Exception as error:
                        info = {}
                        fehler_liste.append(f"{symbol}: {error}")
                    price = finite_number(info.get("currentPrice"))
                    if price is None:
                        price = finite_number(info.get("regularMarketPrice"))
                    mcap = finite_number(info.get("marketCap"))
                    if info.get("currency") != kurswaehrung:
                        fehler_liste.append(f"{symbol}: {kurswaehrung}-Kurswährung nicht bestätigt / Yahoo-Daten fehlen")
                        continue
                    if price is None or mcap is None:
                        fehler_liste.append(f"{symbol}: Kurs oder Marktkapitalisierung fehlt")
                        continue
                    if not (0.5 <= price <= max_preis) or mcap < min_mcap * 1_000_000:
                        continue
                    cash = finite_number(info.get("totalCash"))
                    debt = finite_number(info.get("totalDebt"))
                    fcf = finite_number(info.get("freeCashflow"))
                    years, status = runway(cash, fcf)
                    debt_light, debt_ratio = schulden_ampel(cash, debt)
                    dilution = None if symbol == "CNTL.SW" else verwasserung_berechnen(ticker)
                    einstufung, grund = finanz_einstufung(years, cash, debt, dilution)
                    ergebnisse.append({
                        "Einstufung": einstufung,
                        "Einstufungsgrund": grund,
                        "Runway-Ampel": runway_ampel(years),
                        "Schulden-Ampel": debt_light,
                        "Symbol": symbol,
                        "Thema": quote["thema"],
                        "Geschäftsbezug": quote["bezug"],
                        "Firma": info.get("shortName") or quote.get("shortName") or symbol,
                        f"Kurs {kurswaehrung}": round(price, 2),
                        f"Marktkap. Mio. {kurswaehrung}": round(mcap / 1_000_000, 1),
                        "Bilanzwährung": info.get("financialCurrency") or "k.A.",
                        "Cash Mio.": zahl(cash / 1_000_000) if cash is not None else None,
                        "Schulden Mio.": zahl(debt / 1_000_000) if debt is not None else None,
                        "Schulden / Cash (×)": zahl(debt_ratio, 2),
                        "Free Cashflow Mio.": zahl(fcf / 1_000_000) if fcf is not None else None,
                        "Cash-Runway Jahre": zahl(years, 2),
                        "Runway-Hinweis": status,
                        "Aktienzahl 1J %": dilution,
                        "Aktienzahl-Hinweis": "Fusion mit HT5: nicht vergleichbar" if symbol == "CNTL.SW" else "",
                        "Börse": info.get("exchange") or quote.get("exchange", "k.A."),
                    })
            if ergebnisse:
                themen_ergebnisse(ergebnisse, kurswaehrung, max_treffer)
            else:
                st.warning("Kein Treffer in der festen Auswahl. Prüfe die Kursobergrenze und Mindest-Marktkapitalisierung. Mit diesen Einstellungen wurden keine Space-/Rechenzentren-Unternehmen gefunden.")
            if fehler_liste:
                st.warning("Bei einigen Titeln fehlen Daten. Leere Werte bedeuten unbekannt, nicht null.")
                with st.expander("Datenfehler anzeigen"):
                    st.write(fehler_liste)
        except Exception as error:
            st.error(f"Space-Suche derzeit nicht verfügbar: {error}")
    st.caption("Cash, Schulden und FCF sind in der jeweiligen Bilanzwährung angegeben. Cash-Runway verwendet dieselbe Währung für Zähler und Nenner. Yahoo kann unterschiedliche Berichtsstände liefern; FCF ist die von Yahoo gelieferte jährliche Kennzahl, keine Prognose.")
    st.caption("Aktienzahl 1J: ungefähre Veränderung ausstehenden Kapitals anhand historischer Aktienzahlen. Positive Werte zeigen mehr Aktien; Splits, ADR-Änderungen und Datenfehler können den Vergleich verzerren. Fehlende oder zu alte Daten bleiben leer. Kein Space-Score und keine Kaufempfehlung.")

