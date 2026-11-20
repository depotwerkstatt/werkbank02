---
name: zitat-pruefer
description: Prüft, ob Zitate und Seitenangaben in einer KI-Antwort zu einem Geschäftsbericht (PDF) wirklich im Original stehen. Verwenden, wenn eine KI Fragen zu einem Bericht beantwortet hat und die Belege nachgeprüft werden sollen.
---

# Zitat-Prüfer (Werkbank 02)

Dieser Skill lässt eine KI eine Antwort zu einem Geschäftsbericht so vorbereiten, dass das Skript `werkbank02.py` sie prüfen kann. **Das Prüfen selbst macht das Skript, ohne KI**: reine Textsuche im PDF. Die KI bereitet nur vor und erklärt danach, was der Mensch noch lesen muss.

## Wann verwenden
- Eine KI hat Fragen zu einem PDF-Bericht beantwortet, mit Zitaten und Seitenzahlen.
- Oder: Fragen sollen erst noch beantwortet werden, mit überprüfbaren Belegen.

## Ablauf

### 1. Antwort im richtigen Format
Falls die Fragen noch nicht beantwortet sind, beantworte sie nur aus dem PDF und gib jeden Beleg als eigene Zeile aus:

```
Dokument | Seite | "wörtliches Zitat in Originalsprache"
```

- Seite = die auf der Seite **gedruckte** Seitenzahl, nicht die PDF-Seite.
- Zitate wörtlich, höchstens zwei Sätze, keine Übersetzung, keine eingefügten Zeichen wie `|`, `[2026]` oder `:` in Tabellenzeilen.
- Steht etwas nicht im Dokument: „Steht nicht in den Dokumenten.“

Speichere die Antwort als `antwort.txt` (UTF-8) im selben Ordner wie das Skript.

### 2. Skript starten
```
python werkbank02.py antwort.txt --doc "10-K=bericht.pdf"
```
- Der Name vor dem `=` muss so heissen, wie die Antwort das Dokument nennt.
- Mehrere Dokumente: `--doc` mehrfach angeben.
- Benötigt Python 3 und `pypdf` (`pip install pypdf`).

### 3. Protokoll lesen und erklären
Das Skript schreibt `output/antwort_pruefprotokoll.md`. Für jedes Zitat gibt es ein Urteil:

| Urteil | Bedeutung |
|---|---|
| OK | wörtlich gefunden, Seite stimmt |
| LESEN | wörtlich, aber gekürzt oder der Satz geht weiter; oder „ZAHLEN AUF DER SEITE“ (umgebaute Tabellenzeile, alle Zahlen stehen an der Stelle) |
| PRÜFEN | abweichend oder falsche Seite |
| FEHLT | steht so nicht im Dokument |

Für jedes LESEN, PRÜFEN und FEHLT: Schau dir die im Protokoll gezeigte Originalstelle an und erkläre in einem Satz, was nicht passt (andere Seite, anderes Jahr, Satz geht mit „allerdings“ weiter, Zitat nicht vorhanden).

**Wichtig: Ändere nie ein Urteil des Skripts.** Wenn du anderer Meinung bist, schreib es als Hinweis dazu, das Urteil bleibt stehen.

### 4. Abschluss für den Menschen
Gib am Schluss eine kurze Liste aus:
- Was der Mensch selbst im PDF lesen muss (alle LESEN, PRÜFEN, FEHLT, mit Seite).
- Ob eine Aussage der ursprünglichen Antwort ohne gültigen Beleg dasteht.

## Grenzen
- Das Skript prüft, ob ein Zitat existiert, nicht, ob es die Aussage stützt. Das bleibt beim Menschen.
- Eingescannte PDFs ohne Text gehen nicht.
- Übersetzte Zitate gelten als nicht gefunden.

Idee für diesen Skill: Flex Finance (November 2026). Werkzeug und Tests: depotwerkstatt.substack.com
