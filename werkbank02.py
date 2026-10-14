#!/usr/bin/env python3
r"""
Werkbank 02 (v1.0) – Zitat-Prüfer. Ohne KI.

Prüft die Zitate in einer KI-Antwort gegen die Originaldokumente:
  1. Steht das Zitat wörtlich im Dokument?
  2. Auf welcher Seite? Stimmt die Seitenangabe der KI?
  3. Wurde mit „…" gekürzt? Wenn ja: Was wurde weggelassen?
  4. Geht der Satz nach dem Zitat weiter? Wenn ja: Wie?
  5. Nicht gefunden: Was ist die ähnlichste Stelle, welche Zahlen weichen ab?

Aufruf (Windows, im Cursor-Terminal):
    py werkbank02.py --demo
    py werkbank02.py antwort.txt 10-K.pdf 10-Q.pdf
    py werkbank02.py antwort.txt --doc "10-K=Apple_10K_2025.pdf" --doc "10-Q=Apple_10Q.pdf"

Die KI-Antwort einfach aus dem Chat kopieren und als .txt speichern.
Ergebnis: output\<Name der Antwortdatei>_pruefprotokoll.md
"""
import argparse
import datetime as dt
import difflib
import pathlib
import re
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

VERSION = "1.0"

# Wörter, die eine Aussage einschränken. Stehen sie im weggelassenen Teil, unbedingt lesen.
EINSCHRAENKER = [
    "however", "except", "excluding", "exclude", "not", "no", "unless", "although", "but",
    "partially", "partly", "primarily", "only", "including", "subject to", "offset", "net of",
    "jedoch", "ausser", "ausgenommen", "nicht", "kein", "teilweise", "hauptsächlich", "nur",
    "einschliesslich", "abzüglich", "sofern",
]

ELLIPSE = re.compile(r"\s*(?:\[\s*(?:\.\.\.|…)\s*\]|\(\s*(?:\.\.\.|…)\s*\)|\.\.\.|…)\s*")
SEITE = re.compile(r"(?:\bS\.|\bSeite|\bpage|\bp\.|\bpp\.|\bpg\.)\s*(\d{1,4})", re.IGNORECASE)
ZAHL = re.compile(r"\d[\d,.'’]*\d|\d")

# Zitate in Anführungszeichen: „…“ “…” "…" «…» ‚…‘ (mindestens 3 Wörter)
ZITAT_MUSTER = [
    re.compile(r"„([^“”\"]{12,}?)[“”\"]"),
    re.compile(r"“([^”]{12,}?)”"),
    re.compile(r"«([^»]{12,}?)»"),
    re.compile(r"\"([^\"]{12,}?)\""),
]


# ---------------------------------------------------------------- Text aufbereiten

def anzeige(s):
    """Wie norm(), aber mit Gross-/Kleinschreibung – für die Ausgabe im Protokoll."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("­", "")  # weiches Trennzeichen
    for a, b in [("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("„", '"'), ("«", '"'), ("»", '"'),
                 ("—", "-"), ("–", "-"), ("−", "-"), (" ", " ")]:
        s = s.replace(a, b)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)  # Trennung am Zeilenende
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def norm(s):
    """Für den Vergleich: Ligaturen auflösen, Anführungszeichen und Striche vereinheitlichen,
    Trennstriche am Zeilenende entfernen, Leerraum zusammenziehen, Kleinschreibung."""
    return anzeige(s).lower()


def schluessel(s):
    """Grober Vergleich: nur Buchstaben und Ziffern. Liefert (Schlüssel, Positionsliste ins Original)."""
    zeichen, pos = [], []
    for i, c in enumerate(s):
        if c.isalnum():
            zeichen.append(c)
            pos.append(i)
    return "".join(zeichen), pos


def woerter(s):
    return re.findall(r"[0-9a-zäöüß]+", s)


# ---------------------------------------------------------------- Dokumente laden

GEDRUCKTE_SEITE = [
    re.compile(r"\|\s*(\d{1,4})\s*$"),                 # „Apple Inc. | 2025 Form 10-K | 29"
    re.compile(r"^\s*-?\s*(\d{1,4})\s*-?\s*$"),          # „29" oder „- 29 -"
    re.compile(r"(?:Seite|Page)\s+(\d{1,4})\b", re.I),   # „Seite 29", „Page 29 of 120"
]


def gedruckte_seitenzahl(text):
    zeilen = [z for z in text.splitlines() if z.strip()]
    for z in reversed(zeilen[-3:]):
        for m in GEDRUCKTE_SEITE:
            t = m.search(z)
            if t:
                return t.group(1)
    for z in zeilen[:2]:  # manche Berichte drucken die Zahl oben
        t = GEDRUCKTE_SEITE[1].search(z)
        if t:
            return t.group(1)
    return None


def lade_dokument(pfad):
    pfad = pathlib.Path(pfad)
    if pfad.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            sys.exit("Für PDF-Dateien fehlt das Paket 'pypdf'. Installieren mit:  py -m pip install pypdf")
        seiten = [(p.extract_text() or "") for p in PdfReader(str(pfad)).pages]
    else:  # Textdatei, Seiten durch Seitenvorschub getrennt (z. B. aus pdftotext)
        seiten = pfad.read_text(encoding="utf-8", errors="replace").split("\f")
    out = []
    for i, roh in enumerate(seiten):
        a = anzeige(roh)
        n = a.lower()
        if len(n) != len(a):  # sehr seltene Sonderzeichen ändern die Länge
            a = n
        k, pos = schluessel(n)
        zeilen = [anzeige(z) for z in roh.splitlines() if z.strip()]
        out.append({"pdf": i + 1, "gedruckt": gedruckte_seitenzahl(roh), "norm": n, "anzeige": a, "key": k, "pos": pos,
                    "zeilen": zeilen})
    leer = sum(1 for s in out if len(s["key"]) < 20)
    if leer > len(out) / 2:
        print(f"WARNUNG: {pfad.name} enthält kaum Text. Ist es ein eingescanntes PDF? Dann braucht es zuerst eine Texterkennung (OCR).")
    return out


def bezeichnung(pfad):
    m = re.search(r"10-?[KQ]|20-F|40-F|8-K", pathlib.Path(pfad).name, re.I)
    if m:
        return m.group(0).upper().replace("10K", "10-K").replace("10Q", "10-Q")
    return pathlib.Path(pfad).stem


# ---------------------------------------------------------------- Zitate aus der KI-Antwort holen

def finde_zitate(antwort, labels):
    """Zwei Formate: Tabellen-/Listenzeilen „Dokument | Seite | Zitat" und Text in Anführungszeichen."""
    zitate, gesehen = [], set()

    def doc_in(z):
        for l in labels:
            if l.lower() in z.lower():
                return l
        return labels[0] if len(labels) == 1 else None

    for nr, zeile in enumerate(antwort.splitlines(), 1):
        roh = zeile.strip()
        if not roh:
            continue
        kandidaten = []
        zellen = [c.strip() for c in roh.strip("|").split("|")]
        if len(zellen) >= 3 and any(re.fullmatch(r"(?:S\.\s*|p\.\s*)?\d{1,4}", c) for c in zellen):
            text = max(zellen, key=len)
            if len(woerter(norm(text))) >= 3 and not set(text) <= set("-: "):
                seite = next(re.sub(r"\D", "", c) for c in zellen if re.fullmatch(r"(?:S\.\s*|p\.\s*)?\d{1,4}", c))
                kandidaten.append((text.strip(" \"„“”«»'"), seite))
        if not kandidaten:
            for muster in ZITAT_MUSTER:
                for m in muster.finditer(roh):
                    if len(woerter(norm(m.group(1)))) >= 3:
                        s = SEITE.search(roh)
                        kandidaten.append((m.group(1).strip(), s.group(1) if s else None))
                if kandidaten:
                    break
        for text, seite in kandidaten:
            if seite is None and doc_in(roh) is None:
                continue  # Text in Anführungszeichen ohne Quellenangabe ist kein Beleg
            k = norm(text)
            if k in gesehen:
                continue
            gesehen.add(k)
            zitate.append({"zeile": nr, "text": text, "seite": seite, "dok": doc_in(roh)})
    return zitate


# ---------------------------------------------------------------- Prüfen

def satzrest(seite, start, ende):
    """Was vor und nach dem Fundstück im selben Satz steht."""
    t = seite["anzeige"]
    vor = t[max(0, start - 300):start]
    m = list(re.finditer(r"[.!?;]\s", vor))
    vor = vor[m[-1].end():] if m else ""
    nach = t[ende:ende + 300]
    if re.search(r"[.!?;:]\s*$", t[max(0, start):ende]):  # Zitat endet mit Satzende
        nach = ""
    nach = nach.split(" | ")[0]  # Fusszeile abschneiden
    m = re.search(r"(?<!\bMio)(?<!\bMrd)(?<!\bca)(?<!\bNr)[.!?;](\s|$)", nach)
    nach = nach[:m.end()] if m else nach
    vor = vor.split(" | ")[-1]
    return vor.strip(), nach.strip()


def label_und_rest(text):
    """Teilt „Retained earnings/(Accumulated deficit) 11,326 (14,264)" in Beschriftung und Zahlenteil."""
    tokens = text.split()
    i = 0
    while i < len(tokens) and re.search(r"[A-Za-zÄÖÜäöü]", tokens[i]):
        i += 1
    if i == 0:
        return None
    return " ".join(tokens[:i]), " ".join(tokens[i:])


def tabellenzeile(text):
    """Zeile aus einer Zahlentabelle (z. B. „Net income $ 112,010 $ 93,736")? Beschriftung, danach nur noch Zahlen."""
    lr = label_und_rest(text)
    if not lr:
        return False
    rest = lr[1]
    return len(ZAHL.findall(rest)) >= 2 and re.fullmatch(r"[\s\d,.'’$()\-—–%]+", rest) is not None


def zahlenliste(text):
    return [re.sub(r"[,'’]", "", z).rstrip(".") for z in ZAHL.findall(text)]


def ist_teilfolge(kurz, lang):
    it = iter(lang)
    return all(x in it for x in kurz)


def suche_tabellenzeile(dok, text):
    """Zeilenbeschriftung finden und prüfen, ob alle Zahlen des Zitats in dieser Zeile stehen, in derselben Reihenfolge.
    Liefert (seite, zeile, alle_spalten) oder None."""
    lr = label_und_rest(text)
    if not lr:
        return None
    label_text, rest_q = lr
    label = schluessel(norm(label_text))[0]
    zahlen_q = zahlenliste(rest_q)
    if len(label) < 4 or not zahlen_q:
        return None
    treffer = []
    for streng in (True, False):  # zuerst Zeilen, die mit der Beschriftung beginnen
        for s in dok:
            zeilen = s["zeilen"]
            for i, z in enumerate(zeilen):
                zk = schluessel(norm(z))[0]
                if not (zk.startswith(label) if streng else label in zk):
                    continue
                kandidaten = [z]
                if not zahlenliste(z) and i + 1 < len(zeilen):  # Beschriftung bricht um
                    kandidaten.append(z + " " + zeilen[i + 1])
                for kz in kandidaten:
                    lz = label_und_rest(anzeige(kz))
                    zahlen_z = zahlenliste(lz[1]) if lz else zahlenliste(kz)
                    if ist_teilfolge(zahlen_q, zahlen_z):
                        treffer.append((s, kz, len(zahlen_q) == len(zahlen_z)))
                        break
        if treffer:
            break
    return treffer or None


def einschraenker_in(text):
    w = " " + re.sub(r"[^\w ]", " ", text) + " "
    return [e for e in EINSCHRAENKER if f" {e} " in w]


def seite_label(s):
    return f"S. {s['gedruckt']}" if s["gedruckt"] else f"PDF-S. {s['pdf']}"


def seite_stimmt(behauptet, seiten):
    if behauptet is None:
        return None
    if any(s["gedruckt"] == behauptet for s in seiten):
        return "ja"
    if any(str(s["pdf"]) == behauptet for s in seiten):
        return "nur PDF-Seite"
    return "nein"


def suche_wortlich(dok, text):
    """Exakt (normalisiert) und auf Buchstaben/Ziffern reduziert. Liefert Liste (seite, start, ende, stufe)."""
    n = norm(text)
    k, _ = schluessel(n)
    treffer = []
    for s in dok:
        i = s["norm"].find(n)
        if i >= 0:
            treffer.append((s, i, i + len(n), "exakt"))
            continue
        if len(k) >= 10:
            j = s["key"].find(k)
            if j >= 0:
                treffer.append((s, s["pos"][j], s["pos"][j + len(k) - 1] + 1, "bis auf Satzzeichen"))
    return treffer


def suche_mit_auslassung(dok, teile):
    """Alle Teile in Reihenfolge auf derselben Seite? Liefert (seite, [spans]) oder None."""
    keys = [schluessel(norm(t))[0] for t in teile]
    if any(len(k) < 4 for k in keys):
        keys = [k for k in keys if len(k) >= 4]
    if len(keys) < 2:
        return None
    for s in dok:
        spans, ab = [], 0
        for k in keys:
            i = s["key"].find(k, ab)
            if i < 0:
                break
            spans.append((s["pos"][i], s["pos"][i + len(k) - 1] + 1))
            ab = i + len(k)
        else:
            return s, spans
    return None


def aehnlichste_stelle(dok, text):
    q = woerter(norm(text))
    if not q:
        return None
    qset, L = set(q), len(q)
    qstr = " ".join(q)
    kandidaten = []
    for s in dok:
        spans = [(m.start(), m.end()) for m in re.finditer(r"[0-9a-zäöüß]+", s["norm"])]
        w = [s["norm"][a:e] for a, e in spans]
        if len(w) < 3:
            continue
        hit = [1 if x in qset else 0 for x in w]
        summe = sum(hit[:L])
        best = [(summe, 0)]
        for i in range(1, max(1, len(w) - L + 1)):
            summe += hit[i + L - 1] - hit[i - 1] if i + L - 1 < len(w) else -hit[i - 1]
            best.append((summe, i))
        best.sort(reverse=True)
        for sc, i in best[:3]:
            kandidaten.append((sc, s, i, w, spans))
    kandidaten.sort(key=lambda x: -x[0])
    bester = None
    for sc, s, i, w, spans in kandidaten[:25]:
        for delta in (0, -2, 2):
            j = max(0, i + delta)
            fenster = " ".join(w[j:j + L])
            r = difflib.SequenceMatcher(None, qstr, fenster).ratio()
            if not bester or r > bester[0]:
                ende = spans[min(j + L, len(spans)) - 1][1]
                bester = (r, s, s["anzeige"][spans[j][0]:ende])
    return bester


def zahlen(text):
    return {re.sub(r"[,'’]", "", z).rstrip(".") for z in ZAHL.findall(text)}


def pruefe(zitat, docs):
    text = zitat["text"]
    kandidaten_docs = [zitat["dok"]] if zitat["dok"] in docs else list(docs)
    erg = {"zitat": zitat, "befund": None, "hinweise": [], "fundstelle": None}

    teile = [t for t in ELLIPSE.split(text) if t.strip()]

    # 0) Tabellenauszug: eine oder mehrere Zahlenzeilen, ggf. mit „…“ dazwischen
    if teile and all(tabellenzeile(t) for t in teile):
        for d in kandidaten_docs:
            je_teil = [suche_tabellenzeile(docs[d], t) for t in teile]
            if all(je_teil):
                # Seite wählen, auf der alle Zeilen stehen, bevorzugt die von der KI genannte
                gemeinsam = set.intersection(*[{t[0]["pdf"] for t in tt} for tt in je_teil])
                if not gemeinsam:
                    continue
                seiten = [s for s in docs[d] if s["pdf"] in gemeinsam]
                s = next((x for x in seiten if x["gedruckt"] == zitat["seite"]), seiten[0])
                erg["fundstelle"] = (d, s)
                erg["befund"] = "TABELLE"
                erg["seite"] = seite_stimmt(zitat["seite"], seiten)
                if erg["seite"] == "nein":
                    erg["hinweise"].append(f"Seitenangabe der KI falsch: Die Zeilen stehen auf {', '.join(seite_label(x) for x in seiten)}, nicht auf S. {zitat['seite']}.")
                for teil, tt in zip(teile, je_teil):
                    zeile = next((t for t in tt if t[0]["pdf"] == s["pdf"]), tt[0])
                    if not zeile[2]:
                        erg["hinweise"].append(f"Nur ein Teil der Spalten zitiert. Zeile im Original: „{zeile[1][:200]}“ – prüfen, ob die KI die richtigen Spalten (Zeitraum) gewählt hat.")
                if len(teile) > 1:
                    erg["hinweise"].append(f"{len(teile)} Tabellenzeilen, alle gefunden; Zeilen dazwischen ausgelassen (bei Tabellen normal).")
                return erg

    # 1) mit Auslassung?
    if ELLIPSE.search(text) and len(teile) >= 2:
        for d in kandidaten_docs:
            r = suche_mit_auslassung(docs[d], teile)
            if r:
                s, spans = r
                erg["fundstelle"] = (d, s)
                weg = []
                for (a, e), (a2, _) in zip(spans, spans[1:]):
                    weg.append(s["anzeige"][e:a2].strip())
                gesamt = sum(len(x) for x in weg)
                erg["befund"] = "MIT AUSLASSUNG"
                for x in weg:
                    if x:
                        erg["hinweise"].append(f"Weggelassen: „{x[:400]}{' …' if len(x) > 400 else ''}“")
                        e = einschraenker_in(x)
                        if e:
                            erg["hinweise"].append("ACHTUNG: Im weggelassenen Teil stehen einschränkende Wörter: " + ", ".join(e) + ". Lesen, ob das die Aussage ändert.")
                if gesamt > 800:
                    erg["hinweise"].append("Die Teile liegen weit auseinander. Das „Zitat“ ist aus entfernten Stellen zusammengesetzt.")
                _, nach = satzrest(s, spans[-1][1], spans[-1][1])
                if nach and len(nach) > 2:
                    erg["hinweise"].append(f"Der Satz geht nach dem Zitat weiter: „{nach[:300]}“")
                erg["seite"] = seite_stimmt(zitat["seite"], [s])
                return erg

    # 2) wörtlich?
    for d in kandidaten_docs:
        treffer = suche_wortlich(docs[d], ELLIPSE.sub(" ", text))
        if treffer:
            seiten = [t[0] for t in treffer]
            s, a, e, stufe = treffer[0]
            for t in treffer:
                if zitat["seite"] and t[0]["gedruckt"] == zitat["seite"]:
                    s, a, e, stufe = t
            erg["fundstelle"] = (d, s)
            erg["befund"] = "WÖRTLICH" if stufe == "exakt" else "WÖRTLICH (bis auf Satzzeichen)"
            erg["seite"] = seite_stimmt(zitat["seite"], seiten)
            if erg["seite"] == "nein":
                erg["hinweise"].append(f"Seitenangabe der KI falsch: Das Zitat steht auf {', '.join(seite_label(x) for x in seiten)}, nicht auf S. {zitat['seite']}.")
            elif erg["seite"] == "nur PDF-Seite":
                erg["hinweise"].append("Die KI hat die Seitenzahl des PDF-Programms genannt, nicht die gedruckte Seitenzahl.")
            if len(treffer) > 1:
                erg["hinweise"].append("Steht mehrfach im Dokument: " + ", ".join(seite_label(t[0]) for t in treffer))
            vor, nach = satzrest(s, a, e)
            if tabellenzeile(text):
                vor = nach = ""
            if nach and len(woerter(nach)) >= 2:
                erg["hinweise"].append(f"Der Satz geht nach dem Zitat weiter: „{nach[:300]}“")
                ein = einschraenker_in(nach)
                if ein:
                    erg["hinweise"].append("ACHTUNG: Im Rest des Satzes stehen einschränkende Wörter: " + ", ".join(ein) + ".")
            if vor and len(woerter(vor)) >= 2:
                erg["hinweise"].append(f"Der Satz beginnt vor dem Zitat: „{vor[-200:]}“")
            return erg

    # 3) nicht wörtlich: ähnlichste Stelle
    bester = None
    for d in kandidaten_docs:
        r = aehnlichste_stelle(docs[d], ELLIPSE.sub(" ", text))
        if r and (not bester or r[0] > bester[0][0]):
            bester = (r, d)
    if bester:
        (r, s, fenster), d = bester
        erg["aehnlichkeit"] = r
        erg["fundstelle"] = (d, s)
        if r >= 0.9:
            erg["befund"] = "FAST WÖRTLICH"
        elif r >= 0.6:
            erg["befund"] = "UMFORMULIERT"
        else:
            erg["befund"] = "NICHT GEFUNDEN"
        if r >= 0.6:
            erg["hinweise"].append(f"Ähnlichste Stelle ({round(r * 100)} % gleich, {seite_label(s)}): „{fenster[:400]}“")
            fehlt = sorted(zahlen(text) - zahlen(fenster))
            if fehlt:
                erg["hinweise"].append("Zahlen im Zitat, die an dieser Stelle nicht stehen: " + ", ".join(fehlt))
        else:
            erg["hinweise"].append(f"Keine ähnliche Stelle im Dokument (beste Übereinstimmung {round(r * 100)} %). Vermutlich erfunden oder übersetzt.")
            erg["fundstelle"] = None
        erg["seite"] = None
    else:
        erg["befund"] = "NICHT GEFUNDEN"
        erg["seite"] = None
    return erg


# ---------------------------------------------------------------- Protokoll

AMPEL = {"TABELLE": "OK", "WÖRTLICH": "OK", "WÖRTLICH (bis auf Satzzeichen)": "OK", "MIT AUSLASSUNG": "LESEN",
         "FAST WÖRTLICH": "PRÜFEN", "UMFORMULIERT": "PRÜFEN", "NICHT GEFUNDEN": "FEHLT"}


def gesamturteil(e):
    b = e["befund"]
    if b == "TABELLE":
        if e.get("seite") == "nein":
            return "PRÜFEN"
        if any(h.startswith("Nur ein Teil") for h in e["hinweise"]):
            return "LESEN"
        return "OK"
    if b in ("WÖRTLICH", "WÖRTLICH (bis auf Satzzeichen)"):
        if e.get("seite") == "nein":
            return "PRÜFEN"
        if any(h.startswith("ACHTUNG") or (h.startswith("Der Satz geht") and len(woerter(h)) >= 9)
               for h in e["hinweise"]):
            return "LESEN"
        return "OK"
    return AMPEL[b]


def protokoll(antwort_name, doc_infos, ergebnisse):
    z = [f"# Prüfprotokoll: {antwort_name}", "",
         f"Werkbank 02 v{VERSION} · erstellt {dt.datetime.now():%d.%m.%Y %H:%M} · ohne KI, reine Textsuche", ""]
    z.append("Dokumente: " + "; ".join(f"**{l}** ({p}, {n} Seiten)" for l, p, n in doc_infos))
    z.append("")
    zaehl = {}
    for e in ergebnisse:
        zaehl[gesamturteil(e)] = zaehl.get(gesamturteil(e), 0) + 1
    z.append(f"**{len(ergebnisse)} Zitate geprüft:** " + " · ".join(f"{k} {v}" for k, v in sorted(zaehl.items())))
    z.append("")
    z.append("OK = wörtlich und Seite stimmt · LESEN = wörtlich, aber gekürzt oder Satz geht mit Einschränkung weiter · PRÜFEN = abweichend oder falsche Seite · FEHLT = steht so nicht im Dokument")
    z.append("")
    z.append("| Nr. | Urteil | Befund | Dokument | Seite laut KI | Gefunden auf | Zitat (Anfang) |")
    z.append("|---|---|---|---|---|---|---|")
    for i, e in enumerate(ergebnisse, 1):
        q = e["zitat"]
        fund = f"{e['fundstelle'][0]}, {seite_label(e['fundstelle'][1])}" if e["fundstelle"] else "–"
        seite = q["seite"] or "keine Angabe"
        if e.get("seite") == "nein":
            seite += " (falsch)"
        elif e.get("seite") == "nur PDF-Seite":
            seite += " (PDF-Seite, nicht gedruckte)"
        anfang = q["text"][:60].replace("|", "/") + ("…" if len(q["text"]) > 60 else "")
        z.append(f"| {i} | **{gesamturteil(e)}** | {e['befund']} | {q['dok'] or '?'} | {seite} | {fund} | {anfang} |")
    z.append("")
    z.append("## Details")
    for i, e in enumerate(ergebnisse, 1):
        q = e["zitat"]
        z.append("")
        z.append(f"**{i}. {gesamturteil(e)} – {e['befund']}** (Zeile {q['zeile']} der KI-Antwort)")
        z.append("")
        z.append(f"> {q['text']}")
        z.append("")
        for h in e["hinweise"]:
            z.append(f"- {h}")
        if not e["hinweise"]:
            z.append("- Keine Auffälligkeiten.")
    z.append("")
    z.append("## Was dieses Protokoll nicht prüft")
    z.append("")
    z.append("Ob das Zitat die Aussage stützt, für die die KI es verwendet. Das ist die fünfte Prüfung, und die bleibt bei dir: "
             "Jedes Zitat mit Urteil LESEN ganz lesen, samt weggelassenem Teil und Satzrest.")
    return "\n".join(z)


# ---------------------------------------------------------------- Demo (offline, fiktive Daten)

DEMO_DOK = [
    "Muster AG Geschäftsbericht 2025\n\nUmsatz und Ergebnis\nDer Umsatz stieg im Geschäftsjahr 2025 um 8 % auf 1'240 Mio. CHF. "
    "Das Betriebsergebnis betrug 186 Mio. CHF.\n\nMuster AG | Geschäftsbericht 2025 | 12",
    "Ausblick\nDie Muster AG erwartet für 2026 ein Umsatzwachstum von 5 bis 7 %, sofern sich die Rohstoffpreise nicht "
    "weiter erhöhen. Die Investitionen werden 2026 auf rund 90 Mio. CHF steigen, hauptsächlich für das neue Werk in Polen "
    "und nicht für die Erweiterung in der Schweiz.\n\nMuster AG | Geschäftsbericht 2025 | 13",
    "Risiken\nDie Abhängigkeit von zwei Grosskunden bleibt hoch. Auf sie entfielen 2025 zusammen 41 % des Umsatzes."
    "\n\nMuster AG | Geschäftsbericht 2025 | 14",
]

DEMO_ANTWORT = """Kurzantwort: Die Muster AG wächst solide und investiert stark.

| Dokument | Seite | Zitat |
|---|---|---|
| GB | 12 | Der Umsatz stieg im Geschäftsjahr 2025 um 8 % auf 1'240 Mio. CHF. |
| GB | 14 | Das Betriebsergebnis betrug 186 Mio. CHF. |
| GB | 13 | Die Muster AG erwartet für 2026 ein Umsatzwachstum von 5 bis 7 % |
| GB | 13 | Die Investitionen werden 2026 auf rund 90 Mio. CHF steigen, hauptsächlich für das neue Werk in Polen … in der Schweiz. |
| GB | 14 | Auf sie entfielen 2025 zusammen 14 % des Umsatzes. |
| GB | 13 | Das Management rechnet mit stabilen Margen und weiteren Marktanteilsgewinnen. |
"""


def demo():
    print("=== Werkbank 02, Offline-Test mit fiktiven Daten ===\n")
    tmp = pathlib.Path(__file__).with_name("output")
    tmp.mkdir(exist_ok=True)
    dok_pfad = tmp / "demo_geschaeftsbericht.txt"
    dok_pfad.write_text("\f".join(DEMO_DOK), encoding="utf-8")
    ant_pfad = tmp / "demo_antwort.txt"
    ant_pfad.write_text(DEMO_ANTWORT, encoding="utf-8")
    return lauf(ant_pfad, [("GB", dok_pfad)])


# ---------------------------------------------------------------- Ablauf

def lauf(antwort_pfad, dokumente):
    docs, infos = {}, []
    for label, pfad in dokumente:
        docs[label] = lade_dokument(pfad)
        infos.append((label, pathlib.Path(pfad).name, len(docs[label])))
        ohne = sum(1 for s in docs[label] if not s["gedruckt"])
        print(f"Dokument {label}: {len(docs[label])} Seiten geladen" +
              (f", bei {ohne} ohne erkennbare gedruckte Seitenzahl" if ohne else ""))
    antwort = pathlib.Path(antwort_pfad).read_text(encoding="utf-8", errors="replace")
    zitate = finde_zitate(antwort, list(docs))
    if not zitate:
        print("Keine Zitate gefunden. Erwartet werden Zeilen „Dokument | Seite | Zitat“ oder Text in Anführungszeichen.")
        return 1
    print(f"{len(zitate)} Zitate in der KI-Antwort gefunden.\n")
    ergebnisse = [pruefe(q, docs) for q in zitate]
    for i, e in enumerate(ergebnisse, 1):
        q = e["zitat"]
        fund = seite_label(e["fundstelle"][1]) if e["fundstelle"] else "–"
        print(f"{i:>2}. {gesamturteil(e):<6} {e['befund']:<31} KI: S. {q['seite'] or '?':<4} gefunden: {fund:<10} {q['text'][:55]}")
    out = pathlib.Path(__file__).with_name("output")
    out.mkdir(exist_ok=True)
    ziel = out / (pathlib.Path(antwort_pfad).stem + "_pruefprotokoll.md")
    ziel.write_text(protokoll(pathlib.Path(antwort_pfad).name, infos, ergebnisse), encoding="utf-8")
    print(f"\nProtokoll mit allen Details: {ziel}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Werkbank 02 – prüft Zitate einer KI-Antwort gegen die Originaldokumente.")
    ap.add_argument("antwort", nargs="?", help="KI-Antwort als .txt")
    ap.add_argument("dokumente", nargs="*", help="Originaldokumente (.pdf oder .txt)")
    ap.add_argument("--doc", action="append", default=[], help='Dokument mit eigenem Namen: "10-K=datei.pdf"')
    ap.add_argument("--demo", action="store_true", help="Offline-Test mit fiktiven Daten")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not a.antwort or not (a.dokumente or a.doc):
        ap.print_help()
        return 1
    dokumente = [(bezeichnung(p), p) for p in a.dokumente]
    for d in a.doc:
        label, _, pfad = d.partition("=")
        dokumente.append((label.strip(), pfad.strip()))
    return lauf(a.antwort, dokumente)


if __name__ == "__main__":
    sys.exit(main())
