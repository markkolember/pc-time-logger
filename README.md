# PC ajalogija

Programm logib taustal, kui kaua sa töötad mis programmis ja mis failiga, kuupäeva ja kellaajaga. Jõudeaeg (5 min ilma hiire ja klaviatuurita), arvuti lukustus ja unerežiim arvatakse maha.

See on **etapp 1**: logimine ja lihtne aruanne. Objektidega sidumine, veebiliides, Google Drive'i koopia ja telefoni andmete import tulevad järgmistes etappides.

## Paigaldamine ja uuendamine (Windows)

1. Laadi alla uusim **PCTimeLogger.exe**: <https://github.com/markkolember/pc-time-logger/releases/latest/download/PCTimeLogger.exe>
2. Topeltklõpsa allalaaditud failil. Kui Windows hoiatab („Windows protected your PC“), vajuta **More info → Run anyway**.

Programm paigaldab end kausta `%LOCALAPPDATA%\Programs\PCTimeLogger`, lisab end automaatkäivitusse ja Start-menüüsse („PC ajalogija“) ning hakkab kohe logima. Uuendamiseks tee sama: uus exe peatab vana, kirjutab selle üle ja käivitub ise. Andmed ja seaded jäävad alles. Varasema `start.bat` lahenduse peatab ja eemaldab see samuti automaatkäivitusest.

Pythonit pole vaja paigaldada.

## Kasutamine

Tegumiriba paremas nurgas kellaaja kõrval on sinine kellaikoon. Klõps sellel avab tänase aruande. Paremklõpsuga avaneb menüü:

- **Tänane aruanne** ja **Selle nädala aruanne**: aeg programmide ja failide kaupa ning päeva ajajoon.
- **Ava andmete kaust**: andmebaas, seaded ja logi.
- **Käivita koos Windowsiga**: automaatkäivitus sisse või välja.
- **Välju**: lõpetab logimise.

Käsurealt (Pythoniga, arendajale):

```
python -m pctimelogger                   # sama mis exe: salve ikoon ja logimine
python -m pctimelogger run               # ainult logimine, ilma ikoonita
python -m pctimelogger report --week     # selle nädala aruanne
python -m pctimelogger report --start 2026-10-01 --end 2026-10-31
python -m pctimelogger timeline          # tänane ajajoon
python -m pctimelogger info              # kus asuvad andmebaas ja seaded
```

## Andmed ja seaded

Andmebaas ja seaded on kaustas `%LOCALAPPDATA%\PCTimeLogger`:

- `timelog.db` on SQLite andmebaas. Sinna kirjutab ka telefoniäpp (imporditakse arvutis).
- `config.json` sisaldab seadeid:
  - `idle_seconds`: mitu sekundit ilma tegevuseta loetakse jõudeajaks (vaikimisi 300).
  - `store_titles`: kas salvestada akende pealkirjad (vaikimisi `true`).
  - `objects_root`: kausta „AAA aktiivsed objektid“ asukoht (kasutatakse etapis 2).
  - `phone_inbox`: Google Drive'i kaust, kuhu telefoniäpp oma andmed saadab, näiteks `G:\\Minu draiv\\PC time logger\\phone-inbox`. Logimise ajal loetakse see iga 5 min järel. Käsitsi: `python -m pctimelogger import-phone`.
- `pctimelogger.log` on programmi enda logi vigade otsimiseks.

## Kuidas fail tuvastatakse

| Programm | Viis |
| --- | --- |
| Excel, Word, AutoCAD | Faili täistee küsitakse programmilt endalt (COM). Kui see ei õnnestu, loetakse see akna pealkirjast. |
| Cadmatic ja teised | Akna pealkiri ja programmi avatud failid. Cadmaticu täpne tuvastus kontrollitakse üle sinu arvutis. |

## Arendajale

```
pip install -r requirements.txt pytest
python -m pytest
```

GitHub Actions ehitab iga `main` muudatuse järel Windowsi masinas `PCTimeLogger.exe` (PyInstaller) ja avaldab selle uue väljalaskena.

Andmebaasi skeem on failis `pctimelogger/db.py`. Tabel `activity` on arvuti ja telefoni ühine: `source` on `pc` või `phone` ning ajad on ISO 8601 UTC kujul (`2026-10-30T05:53:53Z`).
