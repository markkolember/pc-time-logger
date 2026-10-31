# PC ajalogija

Programm logib taustal, kui kaua sa töötad mis programmis ja mis failiga, kuupäeva ja kellaajaga. Jõudeaeg (5 min ilma hiire ja klaviatuurita), arvuti lukustus ja unerežiim arvatakse maha.

See on **etapp 1**: logimine ja lihtne aruanne. Objektidega sidumine, veebiliides, Google Drive'i koopia ja telefoni andmete import tulevad järgmistes etappides.

## Paigaldamine (Windows)

1. Paigalda Python 3.11 või uuem: <https://www.python.org/downloads/>. Paigaldamisel märgi linnuke **Add python.exe to PATH**.
2. Laadi see repo alla (roheline nupp **Code → Download ZIP**) ja paki lahti, näiteks kausta `C:\PCTimeLogger`.
3. Topeltklõpsa failil `install.bat`. See paigaldab vajalikud lisad.

## Kasutamine

- **Logimise käivitamine:** topeltklõpsa `start.bat`. Logimine töötab taustal ilma aknata.
- **Automaatne käivitus koos Windowsiga:** vajuta `Win + R`, kirjuta `shell:startup` ja vajuta Enter. Kopeeri avanevasse kausta `start.bat` otsetee.
- **Logimise peatamine:** Task Manageris lõpeta protsess `pythonw.exe`.
- **Tänane aruanne:** topeltklõpsa `aruanne.bat`.

Käsurealt (kaustas, kus see repo on):

```
python -m pctimelogger report            # tänane aruanne
python -m pctimelogger report --week     # see nädal
python -m pctimelogger report --month    # see kuu
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

Andmebaasi skeem on failis `pctimelogger/db.py`. Tabel `activity` on arvuti ja telefoni ühine: `source` on `pc` või `phone` ning ajad on ISO 8601 UTC kujul (`2026-10-30T05:53:53Z`).
