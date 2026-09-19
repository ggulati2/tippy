# Tippy: things to check by hand

The automated tests (`python -m pytest`, and `python -m pytest -m browser` which plays the app in headless Chrome) and the scripted play-throughs cannot hear, feel or watch a child.
These checks need a person. Tick them off on the computer Tippy will really be used on.

## Sound and voice (2 minutes)
- [ ] Sounds are pleasant, not too loud, not crackly (tap a balloon, press a key in Letter Land).
- [ ] The voice reads the instruction at the top of a game. Tap the 🔊 bubble to hear it again.
- [ ] German: switch the language in the parent area and check a German voice speaks. If it sounds English, install a German voice (macOS: System Settings, Accessibility, Spoken Content, System Voice, Manage Voices).
- [ ] The 🔊 button next to the gear silences everything and shows 🔇; tapping again brings sound back.

## Real keyboard and mouse (5 minutes)
- [ ] Letter Land: type the big letter on the real keyboard. Caps Lock on or off makes no difference.
- [ ] A wrong key only wiggles and points at the right key. No red, no buzzer.
- [ ] Space, Enter, Backspace and Shift games react to the real keys.
- [ ] Mouse Meadow with your trackpad or mouse: pop balloons, drag shapes, double-click an egg (is the speed forgiving?), scroll to the treasure with two fingers or the wheel.
- [ ] Word Woods and Sentence Sky: type a whole sentence. The keys feel instant.
- [ ] Free Play: type `cat`, press Enter. Try a word that is not known: the letters dance.

## Spanish (5 minutes, ideally with a Spanish speaker)
- [ ] Parent area, Settings: choose Español. The screens, the spoken instructions and the mascot speak Spanish. If the voice sounds English, install a Spanish voice (macOS: Spoken Content, Manage Voices, Mónica or Jorge).
- [ ] Word Woods and Sentence Sky: words and sentences are correct, natural Spanish for a 6-year-old. Note anything that sounds odd or unfriendly.
- [ ] The Ñ key sits next to L. Words with accents (león, camión) are typed with the plain vowel key.
- [ ] Free Play: type "leon", "avion", "piña": the pictures appear.

## Number Land (3 minutes)
- [ ] Play Number Land with the row of digits above the letters: it works.
- [ ] On a computer with a real number pad: switch on *This computer has a number pad* in Settings. The digit row now gets a hint and the pad keys count. Try all six games (count the animals, add up, the rocket countdown).
- [ ] The numbers are read aloud one digit at a time ("one two three").

## Fullscreen and accidental exits (3 minutes)
- [ ] Double-click the start file: Tippy opens fullscreen with no address bar.
- [ ] Try Cmd+W (Ctrl+W), Cmd+R (F5), Esc, Tab, Alt+F4 while playing. Tippy stays open. (Cmd+Q and Alt+F4 may still close the window on some systems; if so, double-click the start file again: progress and the daily limit are kept.)
- [ ] The gear opens the parent area only with the PIN. Exit Tippy needs the PIN too.
- [ ] Closing from the parent area also closes the Terminal window's server (the window says the server stopped).

## First start on a clean computer (10 minutes)
- [ ] Unzip, double-click the start file. First start installs (needs internet once), then the setup screens appear: language, PIN twice, name, daily limit.
- [ ] Quit, switch off Wi-Fi, start again. Tippy still opens and plays.
- [ ] Double-click the start file a second time while Tippy runs: it just opens the window again.
- [ ] Windows: `start.bat`. Linux: `./start.sh`. (Only macOS was run during development.)

## Limits (3 minutes)
- [ ] In Settings choose "Suggest a break after 5 min" and a daily limit of 30 min. After play, Tippy suggests a break; "keep playing" gives 5 more minutes.
- [ ] Reach the daily limit (use a very short limit to try it). The goodnight screen cannot be closed by clicking or by keys. The PIN opens the parent area, where the limit can be lifted.

## Several children (5 minutes)
- [ ] Parent area, Children tab: add a second child with a picture. Start Tippy again: the big "Who is playing?" pictures appear.
- [ ] Each child sees only their own stars, stickers and settings. Language and limits can differ.
- [ ] Set one child's daily limit very low and reach it: the goodnight screen has a 👥 button and the other child can still play.
- [ ] Removing a child asks first, and cannot remove the last one.

## Backup and restore (3 minutes)
- [ ] Data tab: save a backup, then reset a child's progress, then restore the file. Stars, stickers and settings come back.
- [ ] Restore the same file as a new child on the Children tab: a second child appears with the same progress.
- [ ] Try restoring some other JSON file (for example a photo's name changed to .json): Tippy says it is not a Tippy backup and changes nothing.

## With your child (15 minutes, most important)
- [ ] He starts and finishes a game without help and without reading.
- [ ] He is not frustrated by a wrong key. He understands what to do next.
- [ ] Nothing is too fast, too loud or too scary. Note what he asks for or clicks that does nothing.
- [ ] The sounds and animations feel fun, not overwhelming. If they do, turn animations off in Settings.
- [ ] Are the letters and text big enough from where he sits? Use *Text size* in Settings.

Write down anything odd (a screenshot helps) and send it to the developer.
