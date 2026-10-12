# prova_citta_1 — Borgo delle Querce

![Veduta del Borgo delle Querce](anteprima.png)

Una **città italiana in miniatura**, impostata come diorama urbano: centro
civico, isolati commerciali e residenziali, strade alberate, quartieri di case
e una corona di campagna collinare. È costruita riutilizzando i modelli Blender
già presenti nel repository e aggiungendo geometria procedurale per collegarli
in un unico contesto.

## Cosa contiene

- municipio con portico, torre dell'orologio, tetto in coppi e ingresso su
  **Piazza delle Querce**, animata dal **mercato settimanale**: dieci
  bancarelle a righe, ombrelloni, carretto con cassette e lavagna;
- **pieve romanica** con navata, abside, rosone, campanile in mattoni con
  orologio e sagrato in basolato con cipressi e panche;
- fontana a due vasche, pavimentazione in lastre, caffè all'aperto, panchine,
  lampioni, aiuole, festoni colorati e due **rotatorie fiorite** con fontana;
- **sei palazzi** residenziali/commerciali con vetrine, balconi, tende,
  insegne, marcapiani, corpo scala vetrato e pannelli solari;
- **trentasette case** istanziate dai modelli esistenti (casale, villa
  contemporanea, chalet alpino) con giardini privati, siepi, orti e frutteti;
- viali, incroci rialzati, marciapiedi, attraversamenti pedonali, segnaletica,
  automobili, autobus, furgone del mercato, scooter, biciclette e pensilina;
- **vita di strada**: pedoni, ciclisti, persone sedute, piccioni in piazza e
  uccelli in volo, panni stesi sui balconi, cassonetti, edicola e tombini;
- **Parco delle Rose** con laghetto, anatre, ninfee, canne e pontile in legno,
  e **Giardino del Borgo** con parco giochi: altalene, scivolo, sabbiera;
- ciliegi fioriti ripresi dal modello `albero_2`, alberature urbane
  procedurali e cipressi;
- **campagna circostante**: colline dolci, campi di grano e uliveti a filari,
  cipressi isolati e un borgo con campanile sul colle a nord-ovest.

La scena ha dimensioni di circa **214 × 214 metri** per l'abitato, inseriti in
una piana di campagna che si estende fino all'orizzonte collinare, ed è
organizzata in collezioni Blender distinte per edifici, strada, verde, arredo
e mobilità. Il file finale incorpora i modelli importati, quindi può essere
aperto da solo una volta generato.

## Illuminazione e camera

Il cielo è un modello fisico a **scattering multiplo** (Nishita nelle versioni
4.x) con sole basso da sud-ovest: ombre lunghe e luce dorata sulle facciate.
La camera inquadra la piazza a tre quarti da sud-est, con pieve, mercato e
colline sullo sfondo; il render finale è in Cycles a 2000 × 1500 con
denoising OpenImageDenoise e view transform AgX.

## File

| File | Contenuto |
|---|---|
| `citta.blend` | Scena 3D completa, camera e impostazioni Cycles |
| `anteprima.png` | Render panoramico del borgo |
| `genera_citta.py` | Script procedurale e importazione dei modelli esistenti |

## Rigenerazione

Serve **Blender 5.0 o successivo** e le cartelle originali `casa_1`, `casa_2`,
`casa_3` e `albero_2` nella cartella superiore del repository. Dalla cartella
del progetto:

```bash
python3 genera_citta.py                 # genera citta.blend
python3 genera_citta.py --quick          # genera anche un'anteprima rapida
python3 genera_citta.py --render         # render Cycles a qualità alta
```

Il file `.blend` è salvato con le impostazioni di render finali; `--quick`
riduce temporaneamente campioni e risoluzione solo per il PNG di controllo.
