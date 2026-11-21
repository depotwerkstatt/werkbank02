"""Werkbank 02 als Web-App (Streamlit).

Oberfläche über dem Zitat-Prüfer werkbank02.py. Die Prüflogik steht nur dort;
diese Datei ruft sie auf und zeigt das Ergebnis an. Ohne KI, reine Textsuche.
Hochgeladene Dateien liegen nur während der Prüfung in einem temporären Ordner.
"""
import contextlib
import io
import pathlib
import tempfile

import streamlit as st

import werkbank02 as wb

st.set_page_config(page_title="Zitat-Prüfer (Werkbank 02)", page_icon="🔎", layout="wide")

URTEIL_FARBE = {"OK": "🟢", "LESEN": "🟡", "PRÜFEN": "🟠", "FEHLT": "🔴"}


def pruefen(antwort, dokumente):
    """dokumente: Liste von (Name, Dateiname, Bytes). Gibt (Meldungen, Ergebnisse, Protokoll) zurück."""
    meldungen = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(meldungen):
        docs, infos = {}, []
        for i, (label, dateiname, inhalt) in enumerate(dokumente):
            endung = pathlib.Path(dateiname).suffix.lower() or ".txt"
            pfad = pathlib.Path(tmp) / f"dok{i}{endung}"
            pfad.write_bytes(inhalt)
            docs[label] = wb.lade_dokument(pfad)
            infos.append((label, dateiname, len(docs[label])))
        zitate = wb.finde_zitate(antwort, list(docs))
        ergebnisse = [wb.pruefe(q, docs) for q in zitate]
    hinweise = []
    for zeile in meldungen.getvalue().splitlines():
        for i, (_, dateiname, _) in enumerate(dokumente):
            endung = pathlib.Path(dateiname).suffix.lower() or ".txt"
            zeile = zeile.replace(f"dok{i}{endung}", dateiname)
        if zeile.strip():
            hinweise.append(zeile)
    protokoll = wb.protokoll("KI-Antwort", infos, ergebnisse) if ergebnisse else ""
    return hinweise, ergebnisse, protokoll


def zeige(hinweise, ergebnisse, protokoll):
    for h in hinweise:
        st.warning(h)
    if not ergebnisse:
        st.error("Keine Zitate gefunden. Erwartet werden Zeilen „Dokument | Seite | Zitat“ oder Text in Anführungszeichen.")
        return
    zaehl = {}
    for e in ergebnisse:
        u = wb.gesamturteil(e)
        zaehl[u] = zaehl.get(u, 0) + 1
    st.subheader(f"{len(ergebnisse)} Zitate geprüft")
    st.write(" · ".join(f"{URTEIL_FARBE[k]} {k} {zaehl[k]}" for k in URTEIL_FARBE if k in zaehl))
    zeilen = []
    for i, e in enumerate(ergebnisse, 1):
        q = e["zitat"]
        u = wb.gesamturteil(e)
        zeilen.append({
            "Nr.": i,
            "Urteil": f"{URTEIL_FARBE.get(u, '')} {u}",
            "Befund": e["befund"],
            "Seite laut KI": q["seite"] or "keine Angabe",
            "Gefunden auf": wb.seite_label(e["fundstelle"][1]) if e["fundstelle"] else "–",
            "Zitat (Anfang)": q["text"][:60] + ("…" if len(q["text"]) > 60 else ""),
        })
    st.dataframe(zeilen, hide_index=True, width="stretch")
    st.download_button("Prüfprotokoll herunterladen (.md)", protokoll.encode("utf-8"),
                       file_name="pruefprotokoll.md", mime="text/markdown")
    with st.expander("Vollständiges Prüfprotokoll mit Details zu jedem Zitat", expanded=False):
        st.markdown(protokoll)


st.title("Zitat-Prüfer (Werkbank 02)")
st.write("Prüft ohne KI, ob die Zitate einer KI-Antwort wörtlich im Originaldokument stehen. Reine Textsuche.")
st.info("Füge nichts Persönliches ein (keine Depotdaten, Namen, Kontonummern). Es wird nichts gespeichert.")

with st.expander("So geht's"):
    st.markdown(
        "1. Frag die KI nach Belegen im Format **Dokument | Seite | Zitat** "
        "(oder sie zitiert in Anführungszeichen mit Seitenangabe).\n"
        "2. Kopiere die ganze Antwort unten ins Textfeld.\n"
        "3. Lade das Originaldokument hoch (PDF mit Textebene, z. B. Geschäftsbericht oder 10-K).\n"
        "4. Gib dem Dokument den Namen, den auch die KI verwendet, und klicke auf **Prüfen**.\n\n"
        "**Urteile:** 🟢 OK = wörtlich, Seite stimmt · 🟡 LESEN = wörtlich, aber gekürzt oder der Satz geht weiter · "
        "🟠 PRÜFEN = falsche Seite oder fast wörtlich mit Abweichung (oft eine Zahl) · 🔴 FEHLT = steht so nicht im Dokument"
    )

antwort = st.text_area("KI-Antwort hier einfügen", height=220,
                       placeholder="10-K | 29 | „Net sales increased 6% …“")
dateien = st.file_uploader("Originaldokumente (.pdf oder .txt)", type=["pdf", "txt"], accept_multiple_files=True)
namen = []
for f in dateien or []:
    namen.append(st.text_input(f"Name für {f.name} (so, wie die KI das Dokument nennt)",
                               value=wb.bezeichnung(f.name), key=f"name_{f.name}"))

links, rechts, _ = st.columns([1, 2, 5])
if links.button("Prüfen", type="primary"):
    if not antwort.strip():
        st.error("Bitte zuerst die KI-Antwort einfügen.")
    elif not dateien:
        st.error("Bitte mindestens ein Originaldokument hochladen.")
    else:
        dokumente = [(n.strip() or wb.bezeichnung(f.name), f.name, f.getvalue()) for f, n in zip(dateien, namen)]
        with st.spinner("Prüfe …"):
            st.session_state["ergebnis"] = pruefen(antwort, dokumente)
        st.session_state["beispiel"] = False
if rechts.button("Beispiel ausprobieren"):
    beispiel = [("GB", "demo_geschaeftsbericht.txt", "\f".join(wb.DEMO_DOK).encode("utf-8"))]
    st.session_state["ergebnis"] = pruefen(wb.DEMO_ANTWORT, beispiel)
    st.session_state["beispiel"] = True

if "ergebnis" in st.session_state:
    if st.session_state.get("beispiel"):
        st.caption("Beispiel mit erfundenem Geschäftsbericht der „Muster AG“ und einer KI-Antwort mit eingebauten Fehlern.")
    zeige(*st.session_state["ergebnis"])

st.divider()
st.caption("Grenzen: Der Prüfer zeigt, ob ein Zitat existiert, nicht, ob es die Aussage stützt. Jedes LESEN ganz lesen. "
           f"Eingescannte PDFs ohne Textebene gehen nicht. Werkbank 02 v{wb.VERSION}, Open Source (MIT).")
st.markdown("[Entstanden im Newsletter Depotwerkstatt](https://depotwerkstatt.substack.com/?utm_source=webapp)")
