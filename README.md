# Werkbank 02 – Zitat-Prüfer, ohne KI (v1.0)

Baustein 2 der Depotwerkstatt. Prüft die Zitate in einer KI-Antwort gegen die Originaldokumente: PDF und KI-Antwort rein, Prüfprotokoll raus.

Warum ohne KI: Wer eine KI fragt, ob ihre Zitate stimmen, lässt den Prüfling sich selbst prüfen. Der Zitat-Prüfer ist reine Textsuche. Er kann nichts erfinden.

## Was er prüft

Für jedes Zitat in der KI-Antwort:

1. **Steht es wörtlich im Dokument?** Kleine Unterschiede bei Leerzeichen, Anführungszeichen, Strichen und Dollarzeichen werden ignoriert, Wörter und Zahlen nicht.
2. **Auf welcher Seite?** Verglichen wird mit der gedruckten Seitenzahl (z. B. „Form 10-K | 29“), nicht mit der Seitenzahl im PDF-Programm.
3. **Wurde mit „…“ gekürzt?** Dann zeigt er, was weggelassen wurde.
4. **Geht der Satz nach dem Zitat weiter?** Dann zeigt er den Rest des Satzes. Stehen darin Wörter wie „except“, „not“, „primarily“ oder „sofern“, gibt es eine Warnung.
5. **Nicht gefunden?** Dann sucht er die ähnlichste Stelle und zeigt, welche Zahlen abweichen. Ohne ähnliche Stelle ist das Zitat vermutlich erfunden.

## Urteile

| Urteil | Bedeutung |
|---|---|
| **OK** | Wörtlich, Seite stimmt |
| **LESEN** | Wörtlich, aber gekürzt oder der Satz geht weiter. Ganz lesen: Ändert der fehlende Teil die Aussage? |
| **PRÜFEN** | Falsche Seite, oder fast wörtlich mit Abweichung (oft eine Zahl) |
| **FEHLT** | Steht so nicht im Dokument |

## Installation (Windows, einmalig)

1. Python installieren, falls noch nicht da (siehe Werkbank 01): https://www.python.org/downloads/windows/ → Haken bei „Add python.exe to PATH“.
2. Ordner `werkbank02` entpacken, z. B. nach `C:\Depotwerkstatt\werkbank02`.
3. `start.bat` doppelklicken. Sie installiert `pypdf`, läuft den Offline-Test und fragt dann nach deinen Dateien. Dateien kannst du einfach ins Fenster ziehen.

Im Cursor-Terminal:
```
py -m pip install pypdf
py werkbank02.py --demo
py werkbank02.py antwort.txt 10K-2025.pdf 10Q-Q3-2026.pdf
```

Mac/Linux: `pip3 install pypdf`, dann `python3 werkbank02.py …`.

## So benutzt du ihn

1. Die KI-Antwort aus dem Chat kopieren und als `antwort.txt` speichern (Editor → Speichern unter → Codierung UTF-8).
2. Am besten hast du die KI mit dem Prompt aus Ausgabe 2 gefragt. Dann stehen die Belege als Zeilen „Dokument | Seite | Zitat“ da. Der Prüfer erkennt aber auch Zitate in Anführungszeichen im Fliesstext.
3. Heissen die Dateien nicht „10-K“ oder „10-Q“, gib ihnen einen Namen, den auch die KI verwendet: `--doc "Geschäftsbericht=gb2025.pdf"`.
4. Ergebnis: `output\antwort_pruefprotokoll.md` mit Übersichtstabelle und Details zu jedem Zitat.

## Grenzen (ehrlich)

- **Er prüft, ob ein Zitat existiert, nicht, ob es die Aussage stützt.** Die fünfte Prüfung bleibt bei dir: Jedes LESEN ganz lesen.
- Eingescannte PDFs ohne Textebene gehen nicht. Der Prüfer warnt, wenn ein PDF kaum Text enthält.
- Tabellenzeilen („Net income 112,010 93,736“) erkennt er auch, wenn die KI nur einzelne Spalten zitiert. Dann zeigt er die ganze Zeile, damit du prüfen kannst, ob es die richtige Spalte (der richtige Zeitraum) ist. Bei verschachtelten Layouts kann die Textextraktion eine Zeile aber auseinanderreissen; dann landet ein echtes Zitat bei PRÜFEN statt OK. Im Zweifel im PDF nachsehen.
- Übersetzte Zitate (die KI zitiert auf Deutsch aus einem englischen Bericht) gelten als nicht gefunden. Das ist Absicht: Der Prompt verlangt Zitate in Originalsprache.
- Die gedruckte Seitenzahl erkennt er an der Fusszeile. Bei ungewöhnlichen Layouts fehlt sie, dann vergleicht er mit der PDF-Seite und sagt das dazu.

## Änderungen

- v1.0 (7.10.2026): erste Version. Getestet mit der Originalantwort von ChatGPT aus Ausgabe 2 auf Apples 10-K und 10-Q (PDF).

## Lizenz

MIT – nutzen, ändern, weitergeben erlaubt.
