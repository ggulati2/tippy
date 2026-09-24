# Datenschutz / Privacy

This file is shown in Tippy's parent area ("Datenschutz" tab). After editing it, run
`python scripts/sync_privacy.py` so the app shows the same text.

## Deutsch

### Kurz gesagt
Tippy speichert alles nur auf diesem Computer. Es gibt keine Konten, keine Werbung, keine Statistiken für uns und keine Verbindung ins Internet, solange Sie den Online-Helfer nicht selbst einschalten.

### Was gespeichert wird
- Pro Kind: der Vorname, ein Bild (Tier oder Symbol), das Lieblingswort, bis zu acht Familienwörter, Ihre eigene Wortliste, die Altersgruppe (5, 6, 7 oder 8+, nie ein Geburtsdatum), Interessen, Sprache, Tastatur und Ihre Zeit-Einstellungen.
- Pro Kind: welche Level geschafft sind, Sterne und Sticker, gespeicherte Karten aus dem freien Spiel (nur die getippten Wörter), Spielzeit pro Tag und wie oft welche Taste richtig oder falsch gedrückt wurde. Getippte Texte werden sonst nicht gespeichert.
- Für die Familie: Ihre PIN (nie lesbar, nur als Prüfwert), die Liste der Kinder und, falls eingeschaltet, wie viele Anfragen der Online-Helfer heute gestellt hat.
- Ein technisches Protokoll (Fehler, Start und Ende). Es enthält keine Namen und keine getippten Texte.

### Wo es gespeichert wird
In einem Ordner auf diesem Computer: beim Mac-Programm unter „Library/Application Support/Tippy“ in Ihrem Benutzerordner, unter Windows im Ordner „Tippy“ in „AppData/Roaming“, beim Start aus dem Quellcode im Tippy-Ordner selbst. Jedes Kind hat eine eigene Datei im Unterordner „data/profiles“.

### Was den Computer verlässt
- Standardmäßig: nichts. Tippy antwortet nur Programmen auf diesem Computer.
- Nur wenn Sie den Online-Helfer in der Datei „.env“ selbst einschalten, fragt Tippy bei OpenRouter nach neuen Übungswörtern und Sätzen. Dabei werden nur ein Thema (zum Beispiel „Tiere“) und die Sprache geschickt, nie ein Name, Familienwort, Alter, Ort oder etwas, das Ihr Kind getippt hat.
- Tippys Stimme ist fest eingebaut. Für Sätze ohne Aufnahme (zum Beispiel den Namen Ihres Kindes) nutzt Tippy nur die Stimmen, die auf diesem Computer installiert sind, nie eine Online-Stimme.

### Löschen
- Im Elternbereich unter „Daten“: den Fortschritt eines Kindes zurücksetzen, ein Kind entfernen (unter „Kinder“) oder alles löschen. Dafür wird jedes Mal die PIN noch einmal abgefragt.
- „Alles löschen“ entfernt alle Kinder, alle Sicherungskopien und die PIN. Danach startet Tippy wie neu installiert.
- Wenn Sie ein einzelnes Kind entfernen, legt Tippy dessen Datei zur Sicherheit beiseite (falls es ein Versehen war). „Alles löschen“ entfernt auch diese Dateien.
- Sie können auch einfach den oben genannten Ordner löschen.
- Eine Sicherung („Sicherung speichern“) ist eine Datei, die Sie selbst speichern. Tippy verschickt sie nirgendwohin.

## English

### In short
Tippy keeps everything on this computer. There are no accounts, no ads, no statistics for us and no connection to the internet unless you switch on the online helper yourself.

### What is stored
- For each child: the first name, a picture (an animal or symbol), the favourite word, up to eight family words, your own word list, the age group (5, 6, 7 or 8+, never a birthdate), interests, language, keyboard and your time settings.
- For each child: which levels are done, stars and stickers, saved Free Play cards (only the typed words), play time per day, and how often each key was pressed correctly or not. Nothing else your child types is kept.
- For the family: your PIN (only in scrambled form), the list of children and, if switched on, how many requests the online helper made today.
- A technical log (errors, start and stop). It contains no names and nothing your child typed.

### Where it is stored
In one folder on this computer: for the Mac app in "Library/Application Support/Tippy" in your user folder, on Windows in the "Tippy" folder in "AppData/Roaming", and when started from the source code in the Tippy folder itself. Each child has their own file in the "data/profiles" subfolder.

### What leaves this computer
- By default: nothing. Tippy only answers programs on this computer.
- Only if you switch on the online helper yourself in the ".env" file, Tippy asks OpenRouter for new practice words and sentences. It sends only a theme (for example "animals") and the language, never a name, family word, age, place or anything your child typed.
- Tippy's voice is built in. For sentences without a recording (such as your child's name) Tippy only uses voices installed on this computer, never an online voice.

### Deleting
- In the parent area under "Data": reset one child's progress, remove a child (under "Children"), or delete everything. Each of these asks for the PIN again.
- "Delete everything" removes all children, all safety copies and the PIN. Tippy then starts as if newly installed.
- When you remove a single child, Tippy keeps that child's file aside in case it was a mistake. "Delete everything" removes those files too.
- You can also simply delete the folder named above.
- A backup ("Save a backup") is a file you save yourself. Tippy never sends it anywhere.
