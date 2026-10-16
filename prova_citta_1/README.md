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
  orologio, basamento in pietra e sagrato in basolato con cipressi e panche;
- fontana a due vasche, pavimentazione in lastre, caffè all'aperto con
  tavolini, sedie da bistro e avventori seduti, panchine,
  lampioni, aiuole, festoni colorati e due **rotatorie fiorite** con fontana;
- **otto palazzi** residenziali/commerciali su basamento in pietra, con
  vetrine, balconi, tende, insegne, marcapiani, corpo scala vetrato e
  **coperture calpestabili**:
  pergolato, tavolo e sedie, lettini, ombrellone, fioriere, stendino, comignoli,
  due lucernari, corpo scala con ringhiera e fotovoltaico inclinato;
- **trentatré case** istanziate dai modelli esistenti (casale, villa
  contemporanea, chalet alpino) con giardini privati, siepi, orti e frutteti;
- viali, incroci rialzati, marciapiedi correttamente interrotti ai nodi,
  attraversamenti pedonali con **rampe e piastre tattili**, semafori con
  richiamo pedonale agli incroci principali, lampioni stradali, due
  **piazzali di testata** di Viale Roma, due parcheggi
  di quartiere con auto in sosta, automobili, autobus, scooter, biciclette,
  **furgone del mercato rifinito** e pensilina;
- **prati curati**: undici isolati con manto erboso tagliato a bande alternate,
  cordolo di chiusura e bordura di fiori, e piazzole di ghiaia con corona di
  fiori ai ventisei alberi da viale e da parco, legate da siepi basse;
- **vita di strada**: pedoni, ciclisti, persone sedute, piccioni in piazza e
  uccelli in volo, panni stesi sui balconi, cassonetti carrellati per la
  raccolta differenziata, edicola vetrata e tombini;
- **Parco delle Rose** con laghetto, anatre, ninfee, canne e pontile in legno,
  e **Giardino del Borgo** con parco giochi: altalene, scivolo, sabbiera;
- ciliegi fioriti ripresi dal modello `albero_2`, alberature urbane
  procedurali e cipressi;
- **campagna circostante**: colline dolci che si chiudono sull'orizzonte senza
  gradini, boschi di macchia mediterranea sui pendii, campi di grano, vigne e
  uliveti a filari, cipressi isolati e il borgo sul
  colle a nord-ovest — pieve con abside e rosone, campanile a vela, sei case a
  capanna su zoccoli quotati, muro di cinta, uliveto e una
  **strada bianca a tornanti** che scende fino all'anello stradale della
  città — e oltre le colline tre **dorsali lontane in foschia** che chiudono
  l'orizzonte, con **cumuli** nel cielo.

## Miglioramenti della trentesima versione

**Esattamente tre interventi nel generatore**:

1. **Becchi delle anatre orientati e innestati** — `Batch.cone` poteva
   orientare il becco solo sugli assi globali, mentre le tre anatre hanno yaw
   diversi: due becchi risultavano di traverso e quello di una papera non
   arrivava al muso. `add_oriented_cone` costruisce ora il cono tra due punti
   nel piano della direzione dell'anatra; la base entra nella testa e la punta
   segue il collo.
2. **Ruote dei cassonetti visibili e collegate** — gli assi a `y = ±0,20 m`
   stavano dentro il corpo, largo 0,62 m, e le ruote quasi scomparivano dietro
   le fiancate. Ora i battistrada sono in gomma a `y = ±0,34 m`, sporgono
   10,5 cm dal contenitore e quattro staffe metalliche li collegano al
   basamento. Il punto più basso resta a contatto con `ground_z` del
   marciapiede.
3. **Lampioni sui marciapiedi e rivolti correttamente** — otto dei dodici
   lampioni della piazza erano sul bordo o al centro delle carreggiate: quelli
   a `x = ±19 m` sfioravano via `x = ±23 m`, gli altri cadevano in via
   `y = ±32 m` a `y = ±31 m`. Ora sono sui marciapiedi (`x = ±17,75 m` e
   `y = ±37,25 m`), con il braccio rivolto verso la strada; quelli interni
   guardano la piazza. `add_lamp` inoltra lo yaw anche ai lampioni del
   municipio e delle testate di Viale Roma.

Verifica mirata, senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_migliorie_v30.py' -v
```

I **6 test** controllano l'orientamento e l'innesto dei becchi, il contatto,
la sporgenza e le staffe delle ruote, la quota e la direzione dei dodici
lampioni, oltre all'orientamento dei lampioni d'ingresso del municipio e delle
testate. Sono passati anche i test di regressione per laghetto, parchi,
viabilità, contatto delle ruote e dettagli della piazza.

**Stato degli artefatti:** la revisione aggiorna generatore e test, ma non
`citta.blend` e `anteprima.png`; Blender non è disponibile in questo ambiente.
Per rigenerarli, eseguire `python3 genera_citta.py --quick` dalla cartella
`prova_citta_1` in un ambiente con Blender e i modelli originali installati.

## Miglioramenti della ventinovesima versione

**Esattamente tre interventi nel generatore**, senza modificare edifici,
viabilità, posizione dei palazzi, camera o illuminazione della scena:

1. **Auto e autobus appoggiati alla superficie** — le ruote di `build_car` e
   `build_bus` erano centrate a quota fissa (0,46 m e 0,53 m): il battistrada
   scendeva a 3 cm sopra lo zero, quindi affondava di 2 cm nella carreggiata e
   di 2,5 cm nell'asfalto dei due piazzali di sosta. Ora i mezzi ricevono
   `ground_z`: il punto più basso dei pneumatici coincide con la quota della
   carreggiata (0,05 m) o con quella dell'asfalto dei piazzali (0,055 m), e il
   bus alla fermata di via -70 usa la stessa quota della strada sotto di lui.
   Posizione, carrozzeria e vetri restano invariati.
2. **Furgone del mercato a contatto con la carreggiata** — il furgone aveva
   il battistrada a 4,5 cm dall'asfalto e sembrava sospeso sulla strada. Ora
   `add_van` riceve `ground_z` e il suo asse è calcolato a partire dal
   raggio del pneumatico e dal canale di 5,5 cm, così il punto più basso
   della ruota tocca la carreggiata. Gli anelli restano a 0,905 m dal
   mezzeria, dentro le fiancate.
3. **Cassonetti sul marciapiede** — i due cassonetti di ponente stavano a
   x = -20 m, cioè sull'asfalto dell'incrocio con via -23, che arriva fino a
   x = -19 m; quelli di levante erano speculari. Ora sono a x = ±12,8 e
   ±13,6 m, sul marciapiede di via -32 e di via 32 verso il centro, fuori
   dalla carreggiata delle vie di quartiere. Le ruote, prima a 4,5 cm da
   terra, poggiano su `ground_z`, cioè sulla quota del marciapiede (0,11 m),
   e l'intero contenitore scende di conseguenza.

Verifica mirata, senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_contatto_ruote_cassonetti.py' -v
```

I **12 test** verificano che il battistrada di auto, autobus e furgone tocchi
la superficie indicata, che le auto dei piazzali poggino sulla lastra
d'asfalto e che la quota non dipenda dall'orientamento del mezzo. Per i
cassonetti controllano il contatto delle ruote con il marciapiede, il
basamento che non affonda e il fatto che le quattro collocazioni siano fuori
da ogni carreggiata. Sono stati aggiornati di conseguenza i controlli di
`test_furgone_cassonetti_edicola`, `test_espositori_tappeto_ruote` e
`test_urbanistica`, che fissavano le vecchie quote; `test_fermata_bandiera_viali`
e `test_fermata_rotatoria_pieve` ricevono la costante `ROAD_TOP` nel loro
caricamento parziale.

**Stato degli artefatti:** questa revisione aggiorna il generatore e i test,
non `citta.blend` e `anteprima.png`. La rigenerazione richiede un ambiente
Blender funzionante: in quello di modifica l'importazione di `bpy` è bloccata
dall'assenza di librerie di sistema, a partire da `libXrender.so.1`.
Per applicare queste tre migliorie anche agli artefatti, eseguire
`python3 genera_citta.py --quick` dalla cartella `prova_citta_1` in tale ambiente.

## Miglioramenti della ventottesima versione

**Esattamente tre interventi nel generatore**, senza modificare edifici,
viabilità, posizione degli arredi, camera o illuminazione della scena:

1. **Sagrato della pieve in `surface_z`** — il basolato del sagrato non
   compariva tra le superfici calpestabili: la griglia di 17,5 × 11,6 m
   centrata a 14,4 m dalla facciata della navata (0,21 m di quota) mancava
   dalla classificazione, quindi le due figure in piedi davanti alla facciata
   affondavano di 27 cm, la bicicletta parcheggiata stava 27 cm sotto il
   lastricato e i vasi fioriti della fila d'ingresso restavano seminterrati,
   con 27 cm di coccio sotto il basolato. La regola precede quelle della viabilità perché il basolato
   copre il marciapiede di via -23 nel tratto in cui i due si sovrappongono;
   la quota dei vasi è inoltre campionata vaso per vaso e non una volta per
   fila, così il vaso che sta di là dal ciglio scende con la superficie che
   ha sotto.
2. **Scooter quotati sulla superficie** — `add_scooter` riceve ora `ground_z`,
   come `add_person` e `add_bicycle`: i tre mezzi erano costruiti con il
   battistrada a quota zero, quindi affondavano di 11 cm nei marciapiedi di
   Viale Roma e di 21 cm nel basolato del sagrato, mentre sul rilievo della
   campagna restavano sospesi 6 cm nel vuoto. Posizione, misure e ciclistica
   restano quelle di prima.
3. **Siepe meridionale del centro civico** — la siepe di mezzogiorno
   (`y = -15,6 m`) partiva da 0,20 m e galleggiava 26 cm sopra il prato,
   davanti al lato sud della piazza: ora è piantata nel terreno come le due
   laterali, con poco più di un metro fuori terra. Il lato nord resta libero
   perché il volume del municipio comincia a `y = 14 m`.

Verifica mirata, senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_sagrato_scooter_siepe.py' -v
```

I **10 test** verificano la quota del basolato e il suo ciglio, compresa la
sovrapposizione con il marciapiede di via -23 e l'invarianza delle altre
superfici urbane; l'appoggio delle figure in piedi, della bicicletta e dei
vasi sul sagrato; il battistrada dei sei pneumatici degli scooter, con la
geometria che resta invariata quando `ground_z` non è indicata; la messa a
dimora della siepe meridionale e il lato nord lasciato libero per il
municipio.

**Stato degli artefatti:** questa revisione aggiorna il generatore e i test,
non `citta.blend` e `anteprima.png`. La rigenerazione richiede un ambiente
Blender funzionante: in quello di modifica l'importazione di `bpy` è bloccata
dall'assenza di librerie di sistema, a partire da `libXrender.so.1`.
Per applicare queste tre migliorie anche agli artefatti, eseguire
`python3 genera_citta.py --quick` dalla cartella `prova_citta_1` in tale ambiente.

## Miglioramenti della ventisettesima versione

**Esattamente tre interventi nel generatore**, senza modificare edifici,
viabilità, camera o illuminazione:

1. **Tavolini del caffè** — i quattro piedini verticali isolati sono sostituiti
   da una base a croce appoggiata al pavimento e collegata al fusto centrale.
   Restano invariati posizione, piano circolare e altezza dei tavolini.
2. **Festoni della piazza** — un tubo continuo segue la discesa e la risalita
   della fune, al posto di segmenti orizzontali separati in quota. Le 24
   bandierine hanno entrambi gli estremi dell'orlo superiore sulla fune,
   orientati secondo ciascun tratto, anziché sempre a 45° rispetto alla piazza.
3. **Piccioni sulla piazza** — gli otto piccioni ricevono zampe e piedi alla
   quota della pavimentazione, con il ventre sollevato dalle lastre; il becco
   si collega alla testa e punta lungo il suo asse, non trasversalmente.
   Gli uccelli in volo restano invariati.

Verifica mirata, senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_tavolini_festoni_piccioni.py' -v
```

I **9 test** verificano appoggio e collegamenti della base dei tavolini,
continuità del tracciato dei festoni, attacco e dimensioni delle bandierine,
quota dei piccioni, collegamento delle zampe e orientamento dei becchi.

**Stato degli artefatti:** questa revisione aggiorna il generatore e i test,
non `citta.blend` e `anteprima.png`. La rigenerazione richiede un ambiente
Blender funzionante: in quello di modifica l'importazione di `bpy` è bloccata
dall'assenza di librerie di sistema, a partire da `libXrender.so.1`.
Per applicare queste tre migliorie anche agli artefatti, eseguire
`python3 genera_citta.py --quick` dalla cartella `prova_citta_1` in tale ambiente.

## Miglioramenti della ventiseiesima versione

**Esattamente tre interventi nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Cipressi della campagna quotati sul rilievo (`build_countryside`)** — gli
   otto cipressi isolati sulla piana e sui primi pendii avevano la quota
   fissata a una costante (`z = 3,0·s`) che ignorava il profilo del terreno:
   sul pendio collinare a nord-ovest (`x -95, y 118 m`, quota suolo `+1,26 m`)
   il fusto affondava per oltre un metro (`1,08 m`) nella terra; al margine
   della piana (`x 118, y 20 m`, `x -20, y 116 m`, quota suolo `-0,06 m`)
   galleggiava invece da `24` a `27 cm` nel vuoto. Ora la quota del fusto e
   del cono di chioma è campionata punto per punto su `relief_height(x, y)`:
   la base di ogni fusto appoggia esattamente sulla quota del terreno, sia
   sui dossi sia nella piana.
2. **Paletti perimetrali e catena di Piazza delle Querce (`build_town_square`)** —
   i paletti a protezione del perimetro della piazza avevano il cilindro
   metallico centrato a `z = 0,50 m` con altezza `0,68 m`, quindi con la base
   a `0,16 m`: il basamento in pietra della piazza si trova a quota `0,06 m`,
   lasciando ogni paletto sospeso per dieci centimetri nel vuoto. Inoltre, a
   nord (`y = 13,7 m`), un paletto a `x = 0` era piantato dentro il gradino
   superiore della scalinata monumentale del municipio (`z = 0,73 m`),
   ostruendo l'accesso al portale centrale, mentre i paletti sui lati est e
   ovest erano sprovvisti della sfera dorata di coronamento e mancava la catena
   descritta nel progetto. Ora tutti i paletti poggiano sul basamento in pietra
   (`0,06 m`), il varco centrale verso la scalinata del municipio è libero
   (`abs(x) < 4,0 m`), tutti i lati hanno il coronamento dorato e una catena
   bassa a festone raccorda i paletti contigui.
3. **Tombini e caditoie stradali sulla carreggiata (`build_street_life`)** —
   i chiusini e le griglie di scolo occupavano posizioni scorrette: un tombino
   era collocato a `x = 0, y = -40 m`, cioè esattamente nel mezzo dello
   spartitraffico fiorito di Viale Roma, sepolto nella siepe continua; un
   secondo stava in mezzo al prato sfalciato di un isolato urbano
   (`surface_z = 0,02 m`) e gli altri tre galleggiavano di `10,5 cm` nel
   rilievo della campagna (`surface_z = -0,06 m`); le quattro caditoie
   metalliche erano posizionate sul marciapiede (`x = ±27,4 m`, quota marciapiede
   `0,11 m`) e a quota `0,06 m`, risultando affondate di `2,5 cm` sotto il
   calpestio. Ora tutti e cinque i tombini alloggiano nelle corsie carrabili
   delle strade (`z = 0,05 m`), all'esterno dello spartitraffico centrale, e
   le quattro caditoie sono allineate nella canaletta di scolo a bordo
   carreggiata (`x = ±26,75 m`), a filo asfalto contro il cordolo del
   marciapiede.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_cipressi_paletti_tombini.py' -v
```

I quindici test controllano che tutti gli otto cipressi abbiano la base del fusto
coincidente con la quota del terreno calcolata da `relief_height`, controllando
in particolare la correzione sul dosso collinare e sulla piana; che tutti i
paletti della piazza poggino a quota `0,06 m` sul basamento in pietra, che il
varco centrale verso il municipio sia sgombro, che tutti i paletti abbiano la
sfera dorata e che la catena perimetrale abbia l'andamento a festone; che tutti
i cinque tombini e le quattro caditoie risiedano sulla carreggiata a quota
`0,05 m`, senza intrusioni nello spartitraffico, nei prati o nei marciapiedi.

## Miglioramenti della venticinquesima versione

**Esattamente tre interventi nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Figure e biciclette sull'appoggio giusto (`add_person`, `add_bicycle`,
   nuova `surface_z`)** — le figure in piedi avevano i piedi sull'origine
   zero del generatore, non sulla superficie che avevano sotto: le gambe
   affondavano di `21,25 cm` nel lastricato della piazza (`0,2125 m`), di
   `19 cm` nel tappeto di gomma del parco giochi (`0,19 m`), di `11 cm` nel
   marciapiede (`0,11 m`), di `5 cm` nella carreggiata (`0,05 m`) e di `8 cm`
   nel prato dei parchi (`0,08 m`), mentre sul rilievo della campagna
   (`-0,06 m`) galleggiavano di `6 cm`. Le biciclette avevano lo stesso
   difetto: i coprimani appoggiavano a quota zero, quindi le sei in sosta
   affondavano fino a `11 cm` nel cemento o galleggiavano di `6 cm` sulla
   campagna. Ora `add_person` e `add_bicycle` ricevono la quota del piano
   su cui poggiano (`ground_z`) e la nuova funzione `surface_z(x, y)`
   restituisce quella quota leggendo le stesse misure con cui sono
   costruite strade, marciapiedi, prati, piazza e tappeto del parco giochi:
   i ventiquattro pedoni della folla, il bimbo e l'adulto al parco giochi,
   i tre ciclisti e le sei biciclette in sosta poggiano ognuno sulla
   superficie che ha sotto, e il ciclista siede sulla sella della propria
   bicicletta, con i piedi ai pedali.
2. **Panchina del parco giochi (`build_playground`)** — la panchina era
   piantata sul bordo ovest della sabbiera: la gamba destra
   (`x 52,57–52,69 m`) e il montante dello schienale (`x 52,58–52,68 m`)
   passavano dentro il traverso del telaio di legno (`x 52,59–52,81 m`,
   `z 0,19–0,37 m`), cioè la panchina era infilata nella sabbiera. Ora sta
   lungo il bordo ovest del tappeto di gomma, girata verso il gioco: non
   tocca più la sabbiera né la cavalcavallo e non invade il passaggio
   dell'altalena.
3. **Arredo dei parchi e vasi fioriti (`build_trees_and_park`,
   `build_gardens`)** — l'arredo minore galleggiava sopra il terreno. Le
   otto aiuole dei due parchi avevano il cordolo (`0,25 m` di spessore)
   sospeso `6,5 cm` sopra il prato (`0,08 m`) e gli arbusti appoggiati su
   un bordo che non esisteva; gli otto paletti luminosi partivano da
   quota `0,18 m` e restavano sospesi `10 cm`; la fontanella del Parco
   delle Rose galleggiava `2 cm`. I sei gruppi di vasi fioriti avevano il
   fondo a quota fissa: uno affondava di `2 cm` nel marciapiede, uno
   galleggiava `15 cm` sul rilievo della campagna e uno era piantato **in
   mezzo alla carreggiata** di Viale Roma. Ora le aiuole sono piantate nel prato
   (`0,08–0,33 m`), gli arbusti appoggiano sul cordolo, i paletti sono
   piantati nel tappeto erboso, la fontanella poggia sul prato e i vasi
   seguono la superficie che hanno sotto: quello della carreggiata è
   tornato all'ingresso del giardino privato, sul lato aperto della siepe.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_figure_panchina_arredo.py' -v
```

I quindici test controllano che `surface_z` restituisca la quota giusta su
lastre, cornice della piazza, tappeto del parco giochi, carreggiata,
marciapiede, prati urbani, prato dei parchi, prato dei giardini privati e
rilievo della campagna, e che il viale abbia dieci metri di carreggiata con
i marciapiedi a `7,375 m` dal centro; che i piedi di ogni figura in piedi e
i coprimani di ogni bicicletta poggino sulla quota passata dal generatore,
che la folla passi `ground_z` corretto e che i ciclisti siano seduti sulla
sella; che la panchina del parco giochi non si incroci con la sabbiera né
con la cavalcavallo e resti sul tappeto; e che aiuole, arbusti, paletti,
fontanella e vasi poggino sulla superficie che hanno sotto, senza vasi in
mezzo alla carreggiata. Sono regressioni vere: sul generatore precedente
**dodici dei quindici test falliscono** (gli altri tre riguardano la
cavalcavallo, il tappeto di gomma e la permanenza della panchina sul
tappeto, cose che la venticinquesima versione non tocca).

Sono state aggiornate anche quattro verifiche esistenti, rese obsolete dai
primi interventi: `test_parchi_caffe_pontile.py` controlla le quote nuove
del cordolo delle aiuole (`0,205 m` invece di `0,27 m`), degli arbusti
(`0,61 m` invece di `0,68 m`) e della fontanella (`0,38 m` invece di
`0,40 m`, con l'acqua a `0,70 m`), e `test_fermata_bandiera_viali.py`
controlla i paletti luminosi piantati nel prato (`0,44 m` invece di
`0,54 m`). Con queste correzioni **l'intera suite della città passa**,
**centocinquantatre test**.

**Stato degli artefatti:** `citta.blend` e `anteprima.png` sono rigenerati
con Blender 5.0.0 e comprendono queste tre migliorie.

## Miglioramenti della ventiquattresima versione

**Esattamente tre interventi nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Percorso tattile della fermata autobus (`build_bus_stop`)** — la
   pavimentazione tattile che collega l'uscita della pensilina al bordo di
   salita non era incassata nel marciapiede: la guida in pavé
   (`0,42 × 1,35 m`, spessore `3,5 cm`) aveva il piano a `0,1425 m`, cioè
   `3,25 cm` sopra il marciapiede (`0,11 m`); la fascia gialla di
   avvertimento (`5,80 × 0,42 m`) sporgeva `5,75 cm`; i tredici bolli,
   cilindri di `5,5 cm` di raggio e `5,5 cm` di altezza, arrivavano a
   `0,2105 m`, dieci centimetri sopra il piano — un gradino continuo da
   scavalcare per tutta la lunghezza del percorso. La guida attraversava
   inoltre il passaggio libero della fermata, che il controllo
   dell'undicesima versione chiede libero per `1,775 m`: la pista tattile
   è una pavimentazione, non un arredo, ma il generatore la trattava come
   un mobile. Ora guida e fascia sono incassate nel marciapiede (`2 mm` di
   rialzo, sotto la soglia di `5 mm`), i bolli sono alti `12 mm` e sporgono
   `6 mm` dal piano, e pensilina, panca, cestino, bacheca e portabiciclette
   lasciano di nuovo libero tutto il passaggio.
2. **Isola centrale delle rotatorie (`build_roundabout`)** — il cordolo
   dell'isola era un cilindro pieno: `Batch.cylinder` chiude le due basi,
   quindi la calotta superiore (`0,21 m`) copriva l'intero disco e restava
   sotto il manto erboso (`0,25 m`): l'erba debordava dal bordo di `4 cm` e
   l'aiuola si leggeva come una zolla di prato con un labbro basso, non come
   un'aiuola contenuta. La fontanella era un tamburo di calcestruzzo
   (`r = 1,15 m`, da `0,17` a `0,67 m`) con la lamina d'acqua stesa sopra
   come un coperchio (`0,64–0,68 m`): il pelo dell'acqua era più alto della
   calotta e copriva un bacino che non esisteva. Ora il cordolo è un anello
   con parete (`add_annulus`), alto fino a `0,31 m`, che contiene il prato
   con `6 cm` di pietra a vista; la fontana ha fondo, bordo e acqua distinti
   — l'acqua sta dentro la vasca, `16 cm` sotto il filo, e il getto centrale
   spicca dal fondo. Anello carrabile, marciapiede anulare, isole salvagente
   e attraversamenti restano come prima.
3. **Edicola votiva della pieve (`build_church`)** — la nicchia di marmo con
   la porticina dorata era piantata nel fianco nord della navata, dentro il
   basamento in pietra: il corpo (`0,50 × 0,90 × 1,90 m`) partiva da
   `z = 0,55 m`, cioè `12 cm` sotto la quota del basamento (`0,67 m`), e
   affondava nel calcestruzzo; la porticina restava a `58 cm` dalla quota
   del basamento e la nicchia guardava verso la campagna, fuori dal
   sagrato. Ora è appoggiata al basolato del sagrato, nell'angolo fra la
   facciata e il fianco nord della navata: il fondo coincide con la quota
   del basolato (`0,21 m`), il corpo è a `1,05 m` dalla facciata e a
   `55 cm` dalla parete nord della navata, e la porticina dorata, alla
   stessa altezza relativa del corpo, è fra `70 cm` e `1,40 m` dal piano,
   cioè a portata di mano.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_fermata_rotatoria_pieve.py' -v
```

I tredici test controllano che la guida tattile e la fascia gialla siano
incassate nel marciapiede (fondo sotto il piano, rialzo di `2 mm`), che i
tredici bolli sporgano `6 mm` e siano in fila regolare lungo il ciglio,
che il percorso colleghi la pensilina al bordo di salita restando dentro la
piattaforma; che il cordolo dell'isola sia un anello con parete — nessuna
faccia copre il centro dell'aiuola — con il filo a `0,31 m` e il prato
`6 cm` sotto, che la fontana abbia una vera vasca con l'acqua `16 cm` sotto
il filo e il getto che spicca dal fondo; e che l'edicola votiva sia
appoggiata al basolato del sagrato, dentro il suo ingombro, fuori dalla
pianta del basamento in pietra della pieve e a `1,05 m` dalla facciata.
Nove dei tredici test falliscono sul generatore precedente: sono
regressioni vere, non descrizioni.

Sono state aggiornate anche due verifiche esistenti, rese obsolete dai
primi interventi: `test_fermata_bandiera_viali.py` controlla i bolli con
il nuovo raggio (`3,5 cm` invece di `5,5 cm`), e `test_urbanistica.py` non
conta più la pista tattile fra gli arredi che devono lasciare libero il
passaggio di `1,775 m`, verificando invece che sia a filo del marciapiede.
Con queste correzioni **torna verde anche il controllo dell'undicesima
versione**, che era rosso dalla ventiduesima: l'intera suite della città
passa, **centotrentotto test**.

**Stato degli artefatti:** `citta.blend` e `anteprima.png` sono rigenerati
con Blender 5.0.0 e comprendono queste tre migliorie (il file del
repository era fermo alla ventiduesima versione).

## Miglioramenti della ventitreesima versione

**Esattamente tre interventi nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Camminamenti dei due parchi (`build_trees_and_park`)** — le quattro
   aiuole di ogni parco erano piantate sui due assi della croce pedonale.
   Quelle a `dx = ±10 m` correvano per cinque metri dentro la fascia
   orizzontale (larga `2,40 m`, piano a `0,18 m`) occupandone `1,45 m` e
   lasciando due passaggi da `47 cm`; quelle a `dy = ±10 m` la
   attraversavano da parte a parte, perché lunghe `5 m` contro `2,40 m` di
   luce. Tutte partivano `3,5 cm` dentro il lastricato e arrivavano a
   `0,395 m`, cioè `21 cm` sopra il piano di cammino. Ora ogni aiuola è
   girata sul lato lungo e spostata nel quadrante libero — `(±10, ∓2,30)`
   e `(∓2,30, ±10)` — con il bordo a `0,375 m` dal ciglio, lo sviluppo di
   `5 × 1,45 m` invariato e la lavanda che segue l'asse lungo di ciascuna.
   La fontanella del Parco delle Rose stava nel punto esatto
   dell'incrocio: `2,30 m` di diametro su `2,40 m` di luce, con il
   basamento `8 cm` dentro il lastricato e `52 cm` di vasca sul piano di
   cammino, chiudeva tutti e quattro i bracci. È accostata al braccio
   settentrionale, a `3,20 m` dall'asse: `85 cm` fra il bordo della vasca e
   il ciglio del vialetto, `40 cm` dai paletti luminosi e `17 m` dal centro
   del laghetto.
2. **Platea del chiosco del caffè (`build_town_square`)** — il pavimento
   del gazebo era una lastra spessa `20 cm` con il fondo a `0,35 m`, cioè
   quasi quattordici centimetri sopra il lastricato della piazza
   (`0,2125 m`): con il sole a 19° si leggeva la fessura sotto tutto il
   perimetro, come uno zoccolo sospeso. Ora lo spessore sale a `40 cm` e la
   base scende a `0,15 m`, dentro la pavimentazione; il calpestio resta a
   `0,55 m` (`CAFFE_FLOOR_Z`), così tavolini, sedie da bistro e i due
   avventori seduti conservano le loro quote e i quattro montanti restano
   piantati nella platea.
3. **Pali del pontile sul laghetto (`build_pond`)** — i quattro fusti che
   reggono le quattro tavole del pontile partivano da `z = -0,25 m` e
   salivano fino a `0,45 m`, mentre il piano di calpestio sta fra `0,20` e
   `0,28 m`: ogni palo spuntava così `17 cm` sopra le tavole, come un ceppo
   in mezzo alla passerella. Ora il fusto si ferma a `0,22 m` — due
   centimetri dentro lo spessore del tavolato — e scende a `-0,30 m`, sotto
   il fondo del bacino. Il pontile, il pelo dell'acqua (`0,20 m`) e il
   cordolo ad anello (`raggio 4,25 m`, cresta `0,25 m`) non cambiano.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_parchi_caffe_pontile.py' -v
```

I tredici test controllano che in entrambi i parchi le quattro aiuole
mantengano l'ingombro di prima ma stiano fuori da tutte e due le fasce dei
camminamenti, con almeno `35 cm` dal ciglio e il bordo dentro il cordolo di
perimetro; che non tocchino panchine, paletti luminosi e laghetto e che la
lavanda resti dentro il proprio bordo; che la fontanella sia fuori dalla
croce con almeno `60 cm` di margine e conservi le quote di vasca, acqua e
colonnina; che la platea del chiosco scenda sotto il lastricato senza
cambiare posizione, ingombro o calpestio, con i piani dei tavolini ancora a
`1,31 m`; e che i quattro pali del pontile finiscano dentro lo spessore del
tavolato, infissi oltre `-0,25 m`, con acqua e cordolo invariati. Il file
`citta.blend` e l'anteprima non sono stati rigenerati in questo ambiente,
perché Blender 5.0 non è installato; rigenerarli con `python3 genera_citta.py
--quick` aggiornerebbe entrambi gli artefatti.

## Miglioramenti della ventiduesima versione

**Esattamente tre interventi nel generatore**, senza cambiare viabilità,
posizione degli edifici o camera:

1. **Accessibilità della fermata autobus (`build_bus_stop`)** — un percorso
   tattile collega l'uscita della pensilina al bordo di salita: guida
   longitudinale in pavé e fascia gialla a bolli, allineata al ciglio e
   contenuta nel marciapiede. Il bordo è così riconoscibile senza confondere
   la segnaletica gialla della corsia bus.
2. **Illuminazione dei parchi (`build_trees_and_park`)** — otto paletti bassi
   con diffusore caldo, quattro per parco, illuminano i margini dei sentieri
   centrali; sono fuori dalla larghezza utile dei percorsi e lontani dalle
   panchine.
3. **Canneti del laghetto (`build_pond`)** — i sedici fusti del gruppo
   nord-occidentale sono ora radicati appena sotto il pelo dell'acqua e
   distribuiti in una fascia compatta fra bacino e cordolo, senza invadere il
   pontile; dimensioni e variazione lieve di quota rendono il bordo più
   naturale.

Verifiche geometriche mirate, eseguibili senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_fermata_bandiera_viali.py' -v
python3 -m unittest discover -s prova_citta_1 -p 'test_pieve_palazzi_laghetto.py' -v
```

I due moduli eseguono **25 test verdi** sui tre interventi e sui controlli
preesistenti di fermata, parchi, pieve, palazzi e laghetto. Il file
`citta.blend` e l'anteprima non sono stati rigenerati in questo ambiente,
perché Blender 5.0 non è installato; rigenerarli con `python3 genera_citta.py
--quick` aggiornerebbe entrambi gli artefatti.

## Miglioramenti della ventunesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Lesene della navata (`build_church`)** — le quattro lesene per lato
   (`0,22 × 1,10 m`, alte `9,60 m`) cadevano in asse con le finestre laterali:
   a `ly = ±2,60 m` contro finestre a `ly = ±2,30 m` la compenetrazione
   arrivava a `1,00 m` lungo l'imbotte, per tutti i `12 cm` di spessore e su
   tutta l'altezza della vetrata (`z = 4,30–6,90 m`); a `ly = ±8,00 m` contro
   finestre a `ly = ±7,00 m` ne restavano altri `30 cm`, perché il davanzale
   (`1,80 m`) supera la vetrata (`1,50 m`). Otto compenetrazioni in tutto,
   quattro per fiancata, mozzavano le finestre contro i pilastri. Ora le
   lesene stanno nelle campate
   libere fra le finestre, a `ly = ±4,65 m` e `±8,85 m`: `90 cm` dalle mostre
   interne, `40 cm` da quelle esterne e `60 cm` dallo spigolo della navata, con
   le finestre che restano quattro per lato come prima.
2. **Corpo scala vetrato dei palazzi (`_apartment_elevator_shaft`,
   `_apartment_side_windows`)** — la fascia vetrata del vano era arretrata di
   `-0,02 × profondità` (`28 cm` sui palazzi da `14 m`, `30 cm` su quelli da
   `15 m`): le due colonne centrali di finestre di ogni fianco finivano sotto
   il vetro illuminato, da `5 cm` a `91 cm` di compenetrazione secondo la
   profondità, su tutta l'altezza della finestra (`1,62 m`) e per tutti i piani
   — ottanta compenetrazioni in tutto: sedici su ciascuno dei due palazzi da
   `14 m` affacciati sulla piazza e otto su ciascuno degli altri sei edifici.
   Ora il vano è in asse sul fianco e le quattro colonne per lato stanno a
   `ly = ±2,30 m` e `±0,33 × profondità`: `12 cm` fra traverso di piano
   (`2,90 m`) e cornice della finestra e `25 cm` fra traverso e vetrata, con
   le quattro colonne per piano che restano quattro.
3. **Laghetto del Parco delle Rose (`build_pond`)** — il cordolo era un
   cilindro troncoconico **pieno** (`raggio 4,40 → 4,10 m`, alto `0,22 m` con
   l'asse a `z = 0,10 m`) e `Batch.cylinder` chiude le due basi: la calotta
   superiore copriva l'intero bacino a `z = 0,21 m`, un centimetro sopra il
   pelo dell'acqua (`z = 0,20 m`, raggio `3,85 m`), quindi il laghetto si
   leggeva come un disco di granito e acqua, ninfee (`z = 0,195–0,225 m`) e
   anatre restavano sotto il coperchio. Ora il cordolo è un anello a sezione
   tonda, come la vasca della fontana in piazza — `ring((cx, cy, 0,10), 4,25,
   0,15 m)` — con lo stesso ingombro esterno (`4,40 m`), foro da `4,10 m` e
   cresta a `0,25 m`; bacino, fondo e sponde restano invariati.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_pieve_palazzi_laghetto.py' -v
```

I dodici test verificano che le otto lesene della pieve siano nelle campate
libere, senza compenetrazioni con vetrate e davanzali e con almeno 39 cm di
pietra libera su ogni lato; che il corpo scala dei palazzi sia in asse e che
nessuna delle quattro colonne di finestre per lato cada dentro il traverso o
sotto il vetro, con almeno `12 cm` fra cornici e traverso e `25 cm` fra
traverso e vetrata per tutte e tre le profondità in uso (`11`, `14` e `15 m`); e
che il cordolo del laghetto non copra il centro del bacino ad alcuna quota,
sia un anello con foro `4,10 m` e cresta `0,25 m`, e che acqua (`3,85 m`) e
fondo restino quelli di prima. L'intera suite della città resta verde:
centonove test con Blender 5.0.1.

**Stato degli artefatti:** `citta.blend` e `anteprima.png` sono rigenerati con
Blender 5.0.1 e comprendono queste tre migliorie.

## Miglioramenti della ventesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Pieve romanica e campanile (`build_church`)** — il rosone della facciata
   era centrato a quota `z = 4,35 m`, cioè esattamente dentro l'architrave in
   pietra del portale (`z = 4,10–4,60 m`), ed era generato con
   `cylinder(..., axis="Y")`, quindi risultava ruotato di 90° di taglio rispetto
   alla facciata orientata a est (`yaw = π/2`); le cinque monofore dell'abside
   avevano l'orientamento fisso dei muri della navata e uscivano di taglio fino
   a 36 cm fuori dal cilindro absidale (`r = 4,40 m`); la guglia del campanile
   (`cone(..., 4)`) aveva i quattro vertici di base sugli assi a 45° a quota
   `20,70 m` (13 cm sopra la cornice sommitale a `20,57 m`), lasciando scoperti
   i quattro spigoli della canna; inoltre le due panche del sagrato stavano in
   asse davanti alla porta senza gambe e la targa dell'edicola votiva era
   immersa nel pilastro. Ora il rosone (`r = 1,30 m`) sta nel registro
   superiore della facciata a `z = 7,80 m` (ben sopra il portale e sotto il
   cornicione, con cornice lapidea, vetrata, mozzo centrale, otto colonnine
   radiali e otto borchie perimetrali nel riferimento locale), le cinque
   monofore con davanzale seguono la tangente locale `yaw + a` dell'abside, il
   campanile ha guglia piramidale a base quadrata poggiata sulla cornice
   (`20,55–23,70 m`) e orologio con cornice e doppia lancetta, le panche con
   gambe in pietra fiancheggiano il portale sul basolato e l'intera pieve è
   parametrizzata in `(cx, cy, yaw)`.
2. **Bancarelle e carretto del mercato (`build_market_stall`, `build_market_cart`)**
   — i quattro montanti delle dieci bancarelle partivano da `z = 0,00 m` (21 cm
   sotto il lastricato della piazza a `z = 0,21 m`) e salivano tutti a
   `z = 2,50 m`, bucando di 36 cm la falda anteriore inclinata della tenda
   (`z = 2,14 m`), mentre gambe del banco e casse a terra affondavano di 20 cm
   nel basolato; il carretto del mercato aveva entrambe le ruote sullo stesso
   fianco (`ly = -0,60`) e create con `axis="Y"`, quindi perpendicolari al
   cassone (`yaw = π/2`), piene, affondate fino a `z = 0,00 m` e compenetrate
   dalla lavagna dei prezzi, senza cassette di ortaggi sul pianale. Ora i
   montanti poggiano sul lastricato (`z = 0,21 m`), si arrestano sotto la falda
   inclinata (`2,12 m` sul fronte e `2,43 m` sul retro) collegati da traverse e
   puntoni laterali, e `build_market_cart` costruisce un carretto agricolo a
   due ruote a raggi sui fianchi opposti (`ly = ±0,60`, `z ≥ 0,21 m`) con
   assale, sponde, piedini anteriori, stanghe posteriori, tre cassette di
   ortaggi sul pianale e lavagna su cavalletto staccata dalle ruote.
3. **Semafori e richiami pedonali agli incroci (`build_crosswalk_signal`, `build_crosswalk_signals`)**
   — i sei pali semaforici agli incroci principali sorgevano a
   `(x + 4,70, y + 4,70)`, cioè dentro la rampa ribassata per disabili
   (`1,05 m`) e proprio sopra la piastra tattile gialla (`[x + 4,605, x + 5,065]`),
   mentre il mini-segnale pedonale (`px + 0,50`) e la scatola del pulsante di
   chiamata (`px + 0,32`) fluttuavano nel vuoto a 25,5 e 11,5 cm a est del
   fusto (`r = 0,065 m`). Ora i pali poggiano sulla parte piana del
   marciapiede a `(x + 5,40, y + 5,40)`, lasciando interamente libere rampe e
   piastre tattili anche con la basetta in ottone (`r = 0,18 m`), il pulsante
   di chiamata è fissato direttamente sul fronte del palo e due staffe
   metalliche orizzontali collegano il segnale pedonale al fusto.

Verifica mirata, con il Python di Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_pieve_mercato_semafori.py' -v
```

I nove test verificano che sulla pieve il rosone stia nel registro superiore
della facciata sopra il portale e sotto il cornicione, le cinque monofore siano
tangenti al cilindro absidale, la guglia piramidale poggi sulla cornice del
campanile con orologio a doppia lancetta e le panche con gambe lascino libero
il portale con invarianza rotazionale; che nelle bancarelle i montanti partano
da `z = 0,21 m` restando sotto la falda inclinata e nel carretto del mercato le
due ruote a raggi stiano su fianchi opposti con cassette di ortaggi e lavagna
separata; e che i sei semafori stiano fuori da rampe e piastre tattili, con
pulsante aderente al palo e doppia staffa per il segnale pedonale. L'intera
suite della città resta verde: novantasette test con Blender 5.0.1.

**Stato degli artefatti:** `citta.blend` e `anteprima.png` sono rigenerati con
Blender 5.0.1 e comprendono queste tre migliorie.

## Miglioramenti della diciannovesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Arredi inclinati delle coperture nei propri alloggiamenti** — sui tetti
   degli otto palazzi, i sei richiami a `lbox_tilt` (tre pannelli fotovoltaici
   con relativo vetro, due lucernari con vetro caldo e due lettini con
   materassino rosso e blu) passavano scostamenti locali `(x, y)` che
   `lbox_tilt` ignorava, accumulando tutti e quattordici i volumi inclinati in
   un unico groviglio al centro della copertura `(0, 0)` — proprio in mezzo
   allo stendino — mentre i tre telai metallici sul retro (`depth * 0,30`) e i
   quattro sostegni dei lettini sul fronte restavano vuoti sulla soletta;
   inoltre alle quote originarie il bordo basso scendeva di 8–13 cm sotto il
   piano di calpestio (`roof_z + 0,03 m`). Ora una funzione locale porta i
   centri nel mondo prima dell'inclinazione, scosta gli strati superiori lungo
   la normale al piano inclinato e alza le quote sul filo dei rispettivi
   sostegni: i tre pannelli fotovoltaici poggiano sui telai metallici, i due
   lucernari affiancano il corpo scala e i due lettini poggiano sui pattini a
   prua della terrazza, lasciando libero lo stendino.
2. **Rami degli alberi urbani innestati sul tronco** — nel prototipo di albero
   urbano (istanziato 31 volte fra parchi e filari dei viali), i quattro rami
   secondari calcolavano la radice nel fusto `p0` (`r = 0,10 m`,
   `z = 2,7–3,0 m`) e la punta nella chioma `p1` (`r = 1,50 m`,
   `z = 4,1–4,6 m`), ma venivano generati con `trunk.cylinder(midpoint, rad,
   dist(p0, p1), 10, axis="Z")`: quattro cilindri verticali sospesi nel vuoto
   a 80 cm dall'asse del tronco (58 cm fuori dalla corteccia), che spuntavano
   per oltre un metro sotto le fronde fino a quota 2,42 m. Ora ciascun ramo è
   un tubo continuo inclinato (`add_tube`) teso da `p0` a `p1`, radicato dentro
   il fusto (`r = 0,10 m < 0,22 m`) e innestato nei lobi laterali della chioma.
3. **Panni stesi dentro i balconi** — sulle facciate di Palazzo delle Logge e
   Casa del Mercato i panni stesi ai piani primo e secondo tendevano un unico
   cilindro di 6,8 m sull'asse globale `Y` da `x = -3,4` a `+3,4` a quota
   `z = 6,21` e `9,06 m` — cioè 23 cm sotto l'intradosso dei balconi (`6,44` e
   `9,29 m`) — appendendo cinque panni fino a 90 cm sotto le solette e davanti
   alle campate prive di balcone (`x = 0` al primo piano, `x = ±2,96 m` al
   secondo). Ora `add_balcony_laundry` tende i fili nel riferimento locale solo
   dentro i cinque balconi effettivi dei due livelli (`x = ±2,96 m` al primo
   piano; `x = -5,92, 0, +5,92 m` al secondo), alla quota del corrimano
   (`slab_z + 0,78 m`) fra le due spallette laterali, con tre panni per balcone
   appesi al filo e interamente sopra il calpestio (`slab_z + 0,10 m`).

Verifica mirata, con il Python di Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_coperture_alberi_panni.py' -v
```

I sette test verificano che su tutte e tre le taglie di palazzo (`18×14`,
`20×15`, `16×11`) pannelli fotovoltaici, lucernari e lettini stiano sui propri
alloggiamenti sopra la soletta con gli strati superiori scostati lungo la
normale e ruotino con lo `yaw`; che i quattro rami del prototipo di albero
urbano partano dentro il fusto e salgano in diagonale nella chioma senza
cilindri verticali sospesi sotto le fronde; e che i cinque fili e i quindici
panni di ciascun palazzo cadano solo nei balconi presenti sui livelli 1 e 2,
sopra il piano di calpestio e invarianti per rotazione. L'intera suite della
città resta verde: ottantotto test con Blender 5.0.1.

**Stato degli artefatti:** `citta.blend` e `anteprima.png` sono rigenerati con
Blender 5.0.1 e comprendono queste tre migliorie.

## Miglioramenti della diciottesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Tappeto del parco giochi raccordato al prato** — il tappeto di gomma
   (12 × 9 m) alzava il bordo a 19 cm: 11 cm sopra il prato che lo circonda
   (8 cm) e 1 cm sopra i vialetti di ghiaia (18 cm), un gradino netto su tutto
   il perimetro. Il tappeto riceve ora una scarpata perimetrale di gomma larga
   55 cm, con i quattro angoli mitrati, che porta il bordo esterno a 5 cm —
   sotto l'erba e sotto la ghiaia — e smorza il dislivello in una pendenza di
   14,3°, senza scalini né fessure fra tappeto e terreno.
2. **Ruote in sagoma del furgone del mercato** — i quattro anelli stavano a
   0,965 m dal mezzero, cioè 5 cm fuori dalle fiancate (0,91 m), e sembravano
   appoggiati di taglio sul fianco, mentre il vuoto dentro il pneumatico
   lasciava il cerchio aperto, con un mozzo che sporgeva fuori misura. Ora il
   battistrada sta in sagoma (0,905 m, 5 mm dentro la fiancata) ed esce solo
   sotto il bordo basso della carrozzeria; il canale del cerchio, di 0,275 m,
   copre il vuoto del pneumatico (0,28 m interni) e il mozzo, appena esterno al
   canale, chiude il cerchio. Il punto più basso resta 4 cm sopra la
   carreggiata.
3. **Espositori dell'edicola** — le cinque copertine erano lastre da
   36 × 48 cm che galleggiavano 4 cm sopra il banco, sul filo del ripiano; i
   tre quotidiani erano fogli appesi 1,5–2,7 cm davanti al raccoglitore, nel
   vuoto. Ora le copertine salgono su un leggìo inclinato di 62° (0,44 m di
   sviluppo), incastrato fra la base appoggiata sul banco e la sua battuta
   frontale, e la fascetta del titolo poggia su ciascuna copertina. I
   quotidiani stanno su tre mensole dentro il raccoglitore — ora aperto sul
   fronte, con sponde, fondale, fondo e cielo — ognuna con la battuta sul bordo
   libero e il foglio che si appoggia alla mensola e s'inclina contro il
   fondale. Base, battuta e raccoglitore restano nell'ingombro di prima
   (78 × 16 × 94 cm), quindi banco, tenda, insegna e camera non cambiano.

Verifica mirata, con il Python di Blender (come i primi test della città):

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_espositori_tappeto_ruote.py' -v
```

I sette test verificano che il leggìo s'incastri fra base e battuta e che le
cinque copertine vi appoggino con la fascetta sopra; che ogni mensola abbia la
sua battuta e il quotidiano poggiato fra mensola e fondale; che il tappeto
scenda sotto la quota dell'erba con la scarpata mitrata a 14,3°; che i quattro
pneumatici stiano in sagoma sotto le fiancate, con canale e mozzo a chiudere il
cerchio; e, per tutti e tre gli elementi, la validità delle mesh. L'intera
suite della città resta verde: ottantuno test con Blender 5.0.1.

**Stato degli artefatti:** `citta.blend` e `anteprima.png` sono rigenerati con
Blender 5.0.1 e comprendono queste tre migliorie. Nella veduta d'insieme i tre
dettagli occupano pochi pixel: la scarpata del tappeto, le ruote del furgone e
gli espositori dell'edicola si leggono nei ritagli ingranditi.

## Miglioramenti della diciassettesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
posizione degli edifici, arredi, camera o illuminazione della scena:

1. **Corpi scala vetrati leggibili** — sui fianchi dei palazzi il vetro fumé
   rendeva i corpi scala come blocchi neri piatti. Ora il vetro è illuminato
   (`glass_warm`) e due montanti verticali dividono ciascuna facciata in tre
   campate, collegate ai traversi di piano già presenti.
2. **Vetrine del piano terra illuminate** — le vetrine dei negozi e l'ingresso
   vetrato usavano lo stesso vetro fumé che in render sembrava nero. Ora sono in
   vetro illuminato, così il fronte commerciale si legge come negozio.
3. **Montante centrale delle vetrine** — ogni vetrina dei negozi è divisa da un
   montante centrale in due specchiature, invece di una lastra unica.

Le migliorie 2 e 3 riguardano lo stesso fronte commerciale: sono due dettagli
distinti, ma appartengono alla stessa area del piano terra.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_vetrine_scale.py' -v
```

I sette test contano le scatole per materiale (il vetro fumé non viene più
usato per corpi scala e vetrine), verificano la presenza dei montanti, la
posizione dei montanti esterna al piano del vetro e la stabilità della
struttura alle rotazioni. Il caricamento non richiede `bpy`.

**Stato degli artefatti:** `citta.blend` e `anteprima.png` sono rigenerati con
Blender 5.0.1 e comprendono queste tre migliorie.

## Miglioramenti della sedicesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
edifici, posizione degli arredi, camera o illuminazione della scena:

1. **Pensilina della fermata** — era una scatola opaca: una lastra di vetro
   fumé di 5,3 × 2,75 m chiudeva tutto il fondo, una seconda di 1,2 × 2,75 m
   occupava la testata e la copertura era un coperchio scuro senza fascia né
   sottotetto, così da terra l'attesa spariva dietro un volume nero che
   arrivava a coprire il marciapiede. Ora il telaio è aperto sulla
   carreggiata, con parete di fondo vetrata ripartita da cinque montanti,
   ritorni corti alle testate, panca continua, cestino all'ombra e plafoniera
   sotto la copertura, che riceve sottotetto chiaro e fascia antracite.
   L'insegna «FERMATA · LINEA 1» passa sul nuovo bordo, con gli arredi
   arretrati di 10 cm per conservare i 1,775 m di passaggio libero.
2. **Tricolore del municipio** — il pennone era conficcato nella falda di
   poppa a 1,2 m dal colmo, con la base 18 cm sopra le tegole: la bandiera
   pendeva fuori dal tetto verso est, appesa al nulla e larga appena metà di
   quella della torre. Ora l'asta attraversa la falda dentro una piastra di
   ancoraggio, sale 3,5 m sopra il colmo e regge il telo in quota, sopra la
   gronda e al centro della falda, lontano da torre e camini.
3. **Filari alberati dei viali** — le file a y = ±39,5 stavano 49 cm fuori
   dal marciapiede e 12 cm fuori dal limite dei lotti: l'anello in granito
   della piazzola, spesso 1,42 m di raggio, sbordava di 30 cm sul prato e
   spingeva la ghiaia fino a 2,5 m oltre il cordolo, davanti alle case. Le
   trasversali portano ora i filari al centro del marciapiede (y = ±37,25) e
   Viale Roma a x = ±6,35 sulla carreggiata larga 10 m; l'anello scende a
   1,02 m di raggio, 12 cm dentro il cordolo e 2,3 m fuori dalla corsia di
   sosta, e le siepi passano a y = ±38,9 senza tagliare la piazzola.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_fermata_bandiera_viali.py' -v
```

I dieci test verificano apertura del fronte e vetrata di fondo della pensilina,
quote di panca, cestino e plafoniera, invarianza dell'ingombro e del passaggio
libero, ancoraggio e quota del pennone del tricolore, e — per i filari — che
ogni piazzola stia fra il cordolo e il bordo del marciapiede, fuori dai lotti e
dalla corsia di sosta. **Gli artefatti `citta.blend` e `anteprima.png`
comprendono queste tre migliorie**: sono rigenerati con Blender 5.0.1 e
comprendono anche quelle delle versioni precedenti.

## Miglioramenti della quindicesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
edifici, posizione degli arredi, camera o illuminazione della scena:

1. **Lampioni con lanterna intelaiata** — il diffusore luminoso riceve una
   basetta e quattro montanti metallici. Braccio, sostegno, diffusore, telaio
   e centro del cappello seguono ora tutti lo stesso orientamento: prima
   soltanto il box del braccio ruotava, lasciando la lanterna a est del palo.
2. **Secchiello della sabbiera** — il cubetto rosso diventa un secchiello
   rastremato, con pareti interne ed esterne, fondo chiuso appoggiato sulla
   sabbia, bordo anulare e apertura libera. Un manico semicircolare si
   collega ai due lati del bordo. Sabbia e bordi in legno restano invariati.
3. **Cavallino a molla** — la sfera azzurra su un palo diventa una sagoma
   di cavallino con seduta, due impugnature e poggiapiedi. Una vera spirale
   di quattro giri collega la piastra sul tappeto al supporto della seduta;
   tutte le parti sono costruite nel riferimento locale del gioco.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_lampioni_secchiello_molla.py' -v
```

I nove test verificano telaio e orientamento dei lampioni, apertura e appoggio
del secchiello, collegamenti della molla, impugnature, roto-traslazione e
validità delle mesh. Senza `mathutils` vengono intercettate le polilinee dei
tubi; quando è disponibile, i test eseguono anche la tessellazione reale.

**Stato degli artefatti:** queste tre migliorie sono nello script e sono ora
anche in `citta.blend` e `anteprima.png`, rigenerati con Blender 5.0.1.

## Miglioramenti della quattordicesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
edifici, disposizione degli oggetti, camera o illuminazione:

1. **Furgone del mercato** — i due volumi opachi inglobavano quasi tutti i
   vetri e le quattro ruote erano cilindri sull'asse Y globale, quindi non
   seguivano la sosta ruotata. Il mezzo ha ora telaio, vano merci, cabina e
   cofano distinti; parabrezza e finestrini esterni; porta scorrevole,
   portelloni posteriori, specchietti, paraurti, calandra e fanaleria. Quattro
   pneumatici ad anello con mozzi sono costruiti nel riferimento locale e
   ruotano insieme al veicolo.
2. **Cassonetti per la raccolta differenziata** — i quattro contenitori erano
   parallelepipedi senza aperture né ruote. Ora ciascuno poggia su quattro
   ruote piroettanti e riceve basamento, coperchio inclinato con cerniera,
   maniglia, pedaliera, etichetta frontale e tacche del colore della frazione;
   tutti i componenti rispettano l'orientamento del cassonetto.
3. **Edicola aperta e vetrata** — il vecchio chiosco era una scatola blu
   piena, con sei rettangoli bianchi appesi davanti. La nuova edicola ha
   zoccolo, pareti basse e telaio, quattro vetrate attorno a un vero vano di
   vendita, banco, luce interna, copertura aggettante e insegna «EDICOLA».
   Una tenda continua a sei righe ripara cinque riviste e tre quotidiani
   esposti.

Verifica mirata, eseguibile anche senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_furgone_cassonetti_edicola.py' -v
```

I nove test controllano pneumatici, mozzi, aperture e fanaleria del furgone;
ruote, coperchio, pedaliera e codifica cromatica dei cassonetti; vetrate, vano
di vendita, continuità della tenda, insegna e stampa dell'edicola. Per tutti e
tre gli elementi verificano inoltre la roto-traslazione completa e la validità
delle mesh. `citta.blend` e `anteprima.png` sono rigenerati con Blender 5.0.1 e
comprendono anche le migliorie delle versioni dodicesima e tredicesima.

## Miglioramenti della tredicesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
edifici, disposizione degli oggetti, camera o illuminazione:

1. **Persone sedute** — le figure sedute erano persone in piedi sollevate di
   42 cm: gambe dritte conficcate nella seduta della panchina e nel telaio
   della bicicletta, busto sospeso a mezz'aria. La nuova posa ha cosce
   orizzontali appoggiate al piano, stinchi verticali che scendono fino ai
   piedi e braccia lungo i fianchi. La coppia sulla panchina si sposta
   contro lo schienale con i piedi sulle lastre della piazza; i tre
   ciclisti — le cui spalle erano prima perpendicolari alla direzione di
   marcia — vengono orientati come la bicicletta, con l'anca sulla sella e
   i piedi alla quota dei pedali.
2. **Scooter** — le ruote erano dischi piatti sull'asse Y globale: nelle
   soste ruotate restavano perpendicolari alla direzione di marcia. Ora ogni
   scooter ha pneumatici ad anello nel piano locale, mozzi, forcella,
   parafango, piano d'appoggio, codone con sella, scudo anteriore con faro,
   fanale posteriore e manubrio trasversale con manopole e specchietti.
   Tutte le parti seguono la rotazione del mezzo.
3. **Caffè del Borgo arredato** — i due tavolini erano soli sotto il chiosco,
   senza nemmeno una sedia, e le loro gambe spuntavano sotto la platea del
   pavimento. I tavoli sono ora quotati sul calpestio (piano a 76 cm, come
   un tavolo da bar), quattro sedie da bistro — quattro gambe, seduta a
   46 cm, schienale a listelli — li contornano lasciando libero il
   passaggio fra i montanti del gazebo, e due avventori siedono con la
   nuova posa.

Verifica mirata senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_persone_scooter_caffe.py' -v
```

I dieci test verificano cosce/stinchi/piedi quotati su panchina, bici e
sedie, l'invarianza della posa in piedi, le rotazioni, le ruote dello
scooter nel piano locale con mozzi e manubrio, e sedie/tavoli del caffè;
intercettano le polilinee dei tubi senza tessellarle. **Gli artefatti
`citta.blend` e `anteprima.png` comprendono queste tre migliorie**: sono
stati rigenerati con Blender 5.0.1 (versione 16 del generatore).

## Miglioramenti della dodicesima versione

**Esattamente tre migliorie nel generatore**, senza cambiare viabilità,
edifici, disposizione degli oggetti, camera o illuminazione:

1. **Panchine** — le tre assi dello schienale sono ora sovrapposte in
   verticale e collegate ai montanti, anziché disposte come un ripiano
   orizzontale dietro la seduta.
2. **Automobili** — cabina con tetto, montanti e sei superfici vetrate non
   più nascoste nel volume opaco; coppie di fari anteriori e posteriori.
   Pneumatici e mozzi seguono l'orientamento dell'auto anche nelle soste
   ruotate, invece di mantenere sempre l'asse globale Y.
3. **Biciclette** — pneumatici ad anello con otto raggi per ruota, telaio a
   diamante con forcella collegata al mozzo, sella, manubrio trasversale e
   pedali. Tutte le parti rispettano la rotazione del mezzo.

Verifica mirata senza Blender:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_arredi_mobilita.py' -v
```

I quattro test verificano schienali, vetrature/fanali, rotazioni e struttura
delle biciclette; intercettano le polilinee dei tubi senza tessellarle.
**Gli artefatti `citta.blend` e `anteprima.png` comprendono queste tre
migliorie**: sono stati rigenerati con Blender 5.0.1 (versione 16 del
generatore).

## Miglioramenti dell'undicesima versione

**Esattamente tre migliorie**, oltre alla correzione degli edifici in strada
richiesta separatamente. Impianto stradale, illuminazione, inquadratura e i tre
dettagli della decima versione restano invariati.

1. **Fermata autobus coerente** — il bus era dentro l'Albergo del Borgo,
   mentre la pensilina stava lontano dalla carreggiata. Ora l'autobus viaggia
   verso est nella corsia sud della strada a y = −70, accanto alla fermata:
   vetrature esterne anziché nascoste dentro la carrozzeria, due porte sul lato
   del marciapiede, ruote orientate con il veicolo e display «1 CENTRO».
   La pensilina è aperta verso la strada, su una piazzola raccordata al
   marciapiede; portabici, panchina, cestino e bacheca sono arretrati per
   lasciare libero un passaggio di almeno 1,775 m. Le due auto interferenti
   con la zona di fermata e con Residenza Aurora tornano in corsia.
2. **Ponticello continuo sul laghetto** — le sette tavole orizzontali e le
   travi ruotate nel piano sbagliato diventano ventiquattro tavole inclinate,
   con bordi contigui e due travi portanti che seguono l'arco. Entrambe le
   estremità arrivano sulla terraferma; due correnti per lato e quattordici
   montanti seguono la quota del piano di calpestio. Il ponte si collega a
   ovest al marciapiede e a est al sentiero del parco, senza massi, canneti o
   cordoli trasversali nell'accesso. Geometria scenografica, non progetto
   esecutivo o certificazione di accessibilità/sicurezza.
3. **Tricolore del municipio** — il telo monocromatico in materiale mattone
   è sostituito da una bandiera con tre bande verticali verde-bianco-rosso
   della stessa larghezza, in proporzione 2:3. Una superficie suddivisa e
   ondulata mantiene contigue le cuciture; il bordo presso il pennone resta
   fermo e due anelli lo fissano all'asta.

### Correzione aggiuntiva richiesta: edifici fuori dalla strada

Le posizioni precedenti consideravano solo l'origine delle case, non le
sporgenze dei modelli riutilizzati. In particolare la villa ha un ingombro
asimmetrico e, dopo la rotazione, tetti e balconi potevano invadere la strada
anche quando il punto d'origine sembrava corretto.

- **Tutte e 33 le case sono conservate**: 13 casali, 13 chalet e 7 ville.
- Ogni lotto è esterno a carreggiate, marciapiedi e rotatorie. Posizione e,
  solo dove necessario, scala sono adattate all'intero ingombro del modello,
  con **40 cm di margine dal bordo del lotto**.
- Le quattro case prima a (±18,5, ±44), troppo strette fra i palazzi di
  testata e le strade x = ±23, sono trasferite nelle fasce residenziali a
  nord e a sud. Le altre conservano il quartiere di appartenenza.
- I sedici giardini privati, comprese le siepi che prima attraversavano le
  carreggiate, sono riallineati fuori dalla viabilità e dagli ingombri delle
  case; il modello sorgente di ogni edificio resta intatto.
- Prima di salvare, il generatore controlla gli ingombri contro strade,
  marciapiedi, rotatorie, altre case e volumi principali di municipio, pieve e
  palazzi. Un conflitto interrompe la generazione invece di salvare una
  scena con la stessa regressione. Lotto e ingombro sono anche registrati
  come proprietà personalizzate delle istanze Blender.

## Miglioramenti della decima versione

Esattamente tre interventi di dettaglio, senza modificare impianto urbano,
illuminazione o inquadratura:

1. **Fontana con getti ad arco** — gli otto zampilli verticali isolati sono
   sostituiti da tubi d'acqua continui a traiettoria parabolica, alimentati da
   ugelli in ottone nella vasca superiore. I getti superano il bordo e
   terminano sulla superficie della vasca inferiore, con due increspature
   concentriche per ogni punto d'impatto.
2. **Altalena con sostegni coerenti** — i quattro montanti prima verticali
   formano ora due cavalletti a A, con tiranti trasversali e traversa comune.
   I piedi poggiano sul tappeto e le quattro sospensioni raggiungono i lati
   delle due sedute, invece di restare esterne alla loro profondità.
3. **Scivolo realmente inclinato** — la vecchia pedana orizzontale diventa
   una discesa di circa 29°, con sponde parallele e uscita bassa. Un
   pianerottolo su quattro sostegni collega la discesa a una scaletta con
   cinque pedate, cosciali inclinati e corrimani; l'accesso posteriore resta
   libero. Si tratta di geometria scenografica, non di un progetto esecutivo
   o di una certificazione di sicurezza dei giochi.

## Miglioramenti della nona versione

Tre interventi, non di più, su sicurezza stradale, paesaggio e inquadratura:

1. **Semafori e chiamata pedonale** — i segnali agli incroci erano pannelli
   generici senza indicazioni leggibili per chi guida o attraversa. Sei nodi
   ordinari ricevono ora pali con tre lenti rosso-ambra-verdi, mini-segnale
   pedonale con pittogramma rosso/verde e pulsante di chiamata; le due
   rotatorie restano senza semafori, così l'anello e le sue precedenze non
   vengono occupati da pali.
2. **Strada di breccia a tornanti** — la salita al borgo sul colle era un
   nastro quasi rettilineo, sospeso alla quota media del percorso. Ora un
   calcolo su griglia metrica sceglie una discesa continua: nessun passo risale
   il pendio e la pendenza fra nodi resta sotto il 20%. Una spline morbida
   raccorda i tornanti; il varco di cinque metri nel muro di cinta libera
   l'accesso, una casa viene spostata a levante per liberare la curva e i
   bordi del fondo ghiaioso seguono il rilievo fino al viale di circonvallazione.
3. **Piazza al centro della veduta** — il bersaglio alto della camera
   spostava il piano stradale della piazza verso il terzo inferiore, lasciando
   troppo peso al primo piano. La camera resta sullo stesso asse a tre quarti,
   ma ora punta al centro civico: fontana, mercato e municipio diventano il
   fulcro senza perdere la pieve e il borgo sul colle sullo sfondo.

## Miglioramenti dell'ottava versione

Tre interventi, non di più, su viabilità pedonale e profondità della veduta:

1. **Incroci senza passerelle di marciapiede** — i quattro assi orizzontali e
   i cinque verticali disegnavano cordolo e marciapiede da un capo all'altro
   della città; a ogni nodo le due fasce chiare proseguivano quindi dentro la
   carreggiata perpendicolare, rialzate come barriere. Ora ciascun tratto viene
   sottratto in corrispondenza di tutti gli incroci, usando la larghezza reale
   della strada — 10 m per Viale Roma, 8 m per le vie di quartiere — e un
   taglio più ampio dove subentra l'anello delle due rotatorie. I diciotto nodi
   ordinari ricevono una platea d'asfalto pulita e quattro angoli raccordati;
   nei due piazzali di testata gli angoli assorbiti dalla pavimentazione non
   vengono ricreati.
2. **Attraversamenti davvero accessibili** — i vecchi cubi ai quattro angoli
   sono sostituiti da maglie inclinate: dalla quota di 12 cm del marciapiede
   scendono realmente ai 4 cm della carreggiata, mentre i cordoli si arrestano
   ai lati del varco. Su ogni invito compare una piastra gialla
   tattilo-plantare con bottoni rilevati. Le zebre non sono più barre lunghe
   quasi quanto la strada e centrate nel mezzo dell'incrocio: hanno una fascia
   costante di 2,8 m, un numero di elementi calcolato sulla larghezza della
   carreggiata e stanno sulle quattro testate collegate alle rampe.
3. **Orizzonte atmosferico a più piani** — la montagna introdotta nella
   versione precedente era un plateau largo oltre sei chilometri e le tre
   corone di materiale producevano bande orizzontali nette: nel render il
   fondale sembrava una parete grigio-verde. La quota è ora composta da tre
   dorsali gaussiane separate — colline vicine, rilievo intermedio e catena
   appenninica — con armoniche e picchi locali diversi; fra le creste il suolo
   ridiscende e rende leggibile la profondità. Ventiquattro anelli più fitti
   sulle creste e un unico shader radiale a sei passaggi sfumano senza cuciture
   dal verde della piana all'azzurro-grigio della foschia.

## Miglioramenti della settima versione

Tre interventi sui tre piani del fondo della veduta — lontano, colture, cielo:

1. **La catena lontana chiude l'orizzonte** — oltre il rilievo la scena
   finiva con un disco piatto da 6 km che si leggeva come un mare grigio, e
   il bordo netto con cui la campagna si staccava dal cielo non era il margine
   della piana ma il **piano di clip della camera, fermo a 1600 m**: tutta la
   campagna lontana veniva tagliata lì, lasciando sotto il cielo una fascia
   vuota. Ora il clip è portato a 40 km e il disco è sostituito da un **anello
   radiale fino a 13 km** quotato su una nuova funzione di quota: onde leggere
   sulla piana, dossi sparsi a posizioni deterministiche e una **catena
   lontana** — più alta verso nord-ovest, nella direzione della veduta — che
   chiude l'orizzonte con un profilo morbido. Il colore smorza in tre fasce
   verso la foschia (campagna lontana, piana intermedia, colline in foschia),
   e il raccordo col quadrato del rilievo resta una piana piatta: le quote
   della piana lontana si spengono entro i primi 500 m, così nessuno spunzone
   dei rilievi lontani si sovrappone al bordo della città.
2. **I campi del mezzogiorno si leggono** — nel triangolo ovest della veduta,
   fra circonvallazione, strada bianca e boschi, non c'era che erba uniforme,
   e i campi esistenti erano lastre piatte con piccole palline d'olivo.
   Ogni campo ha ora una **base conformata al rilievo** — una maglia di quad
   condivisi quotati punto per punto, la stessa funzione del rilievo — e una
   cultura riconoscibile: **grano con solcature** a passo regolare e due
   **balle di fieno** appena raccolte, **uliveti veri** con tronco e due globi
   di fogliame in filari sfalsati, **vigne a filari** paralleli al lato lungo
   con pali di sostegno. Quattro campi nuovi riempiono il triangolo vuoto —
   vigna, grano e uliveto lungo la strada bianca, e una vigna fra i boschi
   del nord — e tutti gli otto campi storici cambiano cultura, restando al
   loro posto.
3. **Cumuli sull'orizzonte** — il cielo fisico non porta nubi e la fascia
   alta del fotogramma, un quarto della veduta, restava un gradiente vuoto.
   Sei **cumuli con base piatta e cima a cupola** — lobi appiattiti in basso,
   rotondi in alto — sono allineati alla direzione della camera a quote e
   distanze irregolari, fra i 6,8 e i 12,4 km, a quote che li fanno passare
   dietro le creste della catena lontana. Non
   proiettano ombre sulla campagna: sono puro fondale.

## Miglioramenti di questa versione

Tre interventi mirati, uno per ciascun piano della veduta:

1. **Coperture dei palazzi finite e abitate** — fra il cornicione e il
   parapetto la soletta non esisteva: i tre pannelli solari e i due manufatti
   in calcestruzzo flottavano a mezzo metro sopra il vuoto, e i tetti erano
   lastre bianche completamente lisce. Ogni palazzo riceve ora l'impalcato di
   copertura con parapetto e copertina in pietra, la grondaia sul fronte, il
   fotovoltaico inclinato di 16° su telaietti metallici, due comignoli in
   laterizio con cieloletto, due sfiati, il corpo scala con porta, maniglione e
   ringhiera di salita, due lucernari illuminati e una terrazza con pergolato a
   listelli, tavolo, sedie, due lettini, ombrellone, tre fioriere in coccio e
   uno stendino con i panni. Tutto è scritto in coordinate locali e ruota
   quindi con l'edificio, su tutti e otto i palazzi.
2. **Prati urbani, piazzole e bordure** — fra un isolato e l'altro non c'era
   che il cubo di terreno della città: un unico verde piatto, senza cuciture e
   senza manutenzione. Dieci isolati liberi fra i marciapiedi — quote ricavate
   dal reticolo stradale, così da non toccare edifici, giardini e arredi —
   ricevono un tappeto d'erba affondato nel rilievo e tagliato a bande
   alternate di prato e prato chiaro, chiuso da un cordolo con bordura di fiori
   sul lato strada; i viali alberati hanno la piazzola di ghiaia sotto ogni
   chioma con cinque ciuffi fioriti, e i due filari a y = ±39,5 sono legati da
   siepi basse. Le vecchie aiuole coniche di parco e piazza, che lasciavano
   vedere la parete interna del cordolo come un buco nero, sono ora dischi
   pieni.
3. **Il colle e il borgo lontano** — il grappolo di scatole in cima al rilievo
   era il pezzo più visibile e meno finito della scena: tetti conici orientati
   a rombo su muri rettangolari, una sola quota per tutti i volumi (così le
   case ai bordi flottavano o affondavano) e nessun collegamento con la città.
   Ora il borgo ha una pieve con navata, abside, lesene, rosone, portale e
   croce di colmo, un campanile con celle, orologio, guglia allineata alla
   muratura e pennone; sei case a capanna con frontoni nel filo della
   muratura, gronda aggettante, finestre scure, porta, comignolo e orto
   fiorito, ognuna sul proprio zoccolo quotato punto per punto sul pendio; un
   muro di cinta a denti di sega segue l'isoipsa, sei cipressi fiancheggiano
   la salita e un uliveto la chiude a monte. La strada bianca scende dal
   sagrato fino all'anello di circonvallazione e i suoi bordi sono calcolati
   sulla direzione media della dorsale, così il nastro non scagliona nelle
   curve. Due cuciture chiudono il fondo: la lastra di terreno della città,
   che affiorando di quattro centimetri proiettava col sole basso una linea a
   denti di sega su tutta la campagna, è portata sotto il rilievo, e gli
   ultimi 34 m di griglia del rilievo sono riportati alla quota della piana
   lontana con uno smoothstep — il gradino che si leggeva come taglio netto
   all'orizzonte non c'è più.

## Miglioramenti della quarta versione

Tre interventi mirati su acqua, viale e sosta:

1. **Laghetto con bordo sassoso e ponticello** — la sponda del laghetto era un
   cilindro netto senza transizione con il prato; ora diciotto massi irregolari
   in calcestruzzo — dimensione, colore e posizione variati — cingono la riva
   lasciando libero solo l'accesso al pontile, e un ponticello in larice ad
   arco scavalca il lato nord-ovest: sette assiti seguono la curvatura con
   corrimano a montanti e trave superiore che asseconda l'arco, e un secondo
   ciuffo di canne si infittisce dietro i sassi.
2. **Spartitraffico fiorito su Viale Roma** — i due tratti a nord e a sud
   della piazza erano corsie senza carattere; ora un'aiuola rialzata con
   cordolo, manto erboso e siepe bassa divide le carreggiate per tutta la
   lunghezza, e fiori a passo regolare — lilla, gialli, viola, lilla —
   punteggiano la siepe con macchie di colore leggibili dal viale.
3. **Area attrezzata alla fermata autobus** — la pensilina restava isolata sul
   marciapiede; ora la affiancano un portabiciclette ad arco con tre posti,
   una panchina per i pendolari, un cestino portarifiuti con coperchio e una
   bacheca orari con cornice metallica e vetro di protezione.

## Miglioramenti della sesta versione

Tre interventi su errori di impianto che la veduta mostrava in primo piano:

1. **Testate di Viale Roma e rotatorie** — l'asse maggiore e l'aiuola
   spartitraffico passavano dentro Residenza Aurora e nell'Albergo del Borgo:
   la carreggiata entrava nella facciata e ne usciva dal retro, e la siepe
   centrale attraversava anche le quattro intersezioni del viale. Ora il viale
   corre a tronconi fra un incrocio e l'altro e si chiude su due **piazzali di
   testata** davanti alle facciate: platea in asfalto con fascia in pietra
   davanti alle vetrine, isola centrale alberata, due attraversamenti ai lati,
   aiuole fiorite, panchine e lampioni ornamentali; lo spartitraffico fiorito
   si interrompe in corrispondenza degli incroci e l'incrocio nord, che ne era
   privo, riceve le strisce pedonali. Le quattro case che stavano a ±12 m dai
   fondali, con i loro giardini, sono arretrate di sei metri e mezzo: entravano
   di due metri dentro i palazzi. Nelle due rotatorie, infine, i marciapiedi
   delle strade afferenti tagliavano l'anello da parte a parte, sospesi nove
   centimetri sopra la carreggiata: ora si fermano dove incontrano il cerchio,
   una corona di marciapiede con i suoi cordoli chiude i quarti fra le strade,
   e le isole salvagente con le strisce tornano sui quattro assi di afflusso.
2. **La pieve in asse e i volumi a terra** — la navata della pieve era girata
   di un quarto di giro rispetto a tutto ciò che le sta intorno: il tetto
   attraversava il volume per traverso sporgendo sei metri per lato, l'abside
   restava staccata di tre metri dal muro di fondo e il portale galleggiava in
   mezzo al sagrato. La navata è rimessa in asse, con la profondità portata a
   venti metri e il corpo spostato di due metri verso est e di uno e mezzo
   verso sud, così l'abside non entra nella strada di via −70. Sotto la pieve,
   come sotto tutti e otto i palazzi, mancava il basamento: i volumi partivano
   da quota 0,30 mentre il rilievo
   della città sta a −0,06, e in controluce restava una fascia vuota da 36 a
   41 cm, leggibile come un'ombra staccata da terra. Ora uno zoccolo in pietra
   scende fino a −0,60 e la muratura vi poggia sopra. Lo stesso richiamo a
   terra riguarda sagrato, prati dei parchi e siepi del centro civico:
   partivano da un minimo di un centimetro a un massimo di diciassette sopra il
   terreno, e mostravano il vuoto sotto le fronde e sotto il basolato.
3. **L'ingresso del municipio e il mercato** — la scalinata del portico era
   rovesciata: il gradino più alto stava dalla parte del sagrato, così dalla
   piazza si saliva al portico e poi si scendeva verso la porta, la cui soglia
   restava mezzo metro sotto l'ultima pedata. Ora quattro pedate a ventaglio
   salgono verso il portale — con le spallette laterali che ne seguono la
   sfumatura — e soglia, stipiti, architrave e maniglia sono riportati alla
   quota giusta. Il mercato, che con la seconda fila a y = 10,9 m infilava i
   montanti delle bancarelle nei plinti delle colonne e piantava un ombrellone
   in mezzo ai gradini, è arretrato di due metri: i tre ombrelloni passano due
   ai lati del mercato e uno davanti alla fontana, e la panchina che finiva
   dentro una bancarella è sostituita da due panchine ai fianchi. Chiude
   l'intervento un nuovo prato a ponente del municipio, che fa da specchio a
   quello di levante.

## Miglioramenti della quinta versione

Tre interventi mirati, uno per ciascun piano della veduta:

1. **Illuminazione stradale fuori dalla piazza** — i soli punti luce della
   città erano i dodici lampioni ornamentali della piazza: viali e strade di
   quartiere, con il sole a 19° e le ombre già lunghe, restavano al buio.
   Ora ventotto lampioni stradali scandiscono i marciapiedi — dodici su
   Viale Roma, sedici sulle trasversali y = ±32 — con palo antracite,
   collarino dorato, braccio rivolto alla carreggiata e testa a luce calda;
   le posizioni stanno sui marciapiedi esistenti, a distanza da incroci,
   rotatorie e filari alberati, così pali e chiome non si toccano.
2. **Parcheggi di quartiere pavimentati** — della sosta restavano solo
   quattro strisce bianche disegnate sull'erba accanto ai palazzi del viale,
   senza platea né accesso. Ora ci sono due piazzali veri: davanti alle
   Botteghe Ovest e sul retro di Casa del Mercato, entrambi raccordati ai
   marciapiedi. Ognuno ha la platea in asfalto con cordoli di testata, tre
   stalli segnati con fermaruota in calcestruzzo, un'isola d'ombra con
   albero all'angolo, il cartello «P» all'ingresso e tre auto in sosta.
3. **Boschi di macchia sulle colline** — i pendii della campagna erano
   dossi lisci e completamente nudi, e lo sfondo della veduta restava una
   distesa verde uniforme. Tredici macchie di bosco — nove alberi l'una
   fra latifoglie, olivi e qualche cipresso, 117 alberi in tutto —
   punteggiano ora i versanti, con ogni fusto quotato punto per punto su
   `hill_height` e i centri tenuti dentro il margine della griglia del
   rilievo, lontano da campi coltivati, strada bianca e borgo sul colle.

La scena ha dimensioni di circa **214 × 214 metri** per l'abitato, inseriti in
una piana di campagna che si estende fino all'orizzonte collinare, ed è
organizzata in collezioni Blender distinte per edifici, strada, verde, arredo
e mobilità. Il file finale incorpora i modelli importati, quindi può essere
aperto da solo una volta generato.

## Illuminazione e camera

Il cielo è un modello fisico a **scattering multiplo** (Nishita nelle versioni
4.x) con sole basso da sud-ovest: ombre lunghe e luce dorata sulle facciate.
La camera inquadra il centro della piazza a tre quarti da sud-est, con pieve,
mercato e colline sullo sfondo; il render finale è in Cycles a 2000 × 1500 con
denoising OpenImageDenoise e view transform AgX.

## File

| File | Contenuto |
|---|---|
| `citta.blend` | Scena 3D completa, camera e impostazioni Cycles |
| `anteprima.png` | Render panoramico del borgo |
| `genera_citta.py` | Script procedurale e importazione dei modelli esistenti |
| `test_dettagli.py` | Sei controlli geometrici su fontana, altalena e scivolo |
| `test_urbanistica.py` | Diciannove controlli su case, giardini, fermata, ponte e tricolore |
| `test_arredi_mobilita.py` | Quattro controlli su panchine, automobili e biciclette |
| `test_persone_scooter_caffe.py` | Dieci controlli su persone sedute, scooter e caffè |
| `test_furgone_cassonetti_edicola.py` | Nove controlli su furgone, cassonetti ed edicola |
| `test_fermata_bandiera_viali.py` | Dodici controlli su pensilina, tricolore e filari dei viali |
| `test_vetrine_scale.py` | Sette controlli su corpi scala e vetrine del piano terra |
| `test_espositori_tappeto_ruote.py` | Sette controlli su espositori dell'edicola, tappeto giochi e ruote del furgone |
| `test_coperture_alberi_panni.py` | Sette controlli su coperture dei palazzi, rami degli alberi urbani e panni sui balconi |
| `test_pieve_mercato_semafori.py` | Nove controlli su pieve romanica, bancarelle e carretto del mercato e semafori agli incroci |
| `test_pieve_palazzi_laghetto.py` | Tredici controlli su lesene della pieve, corpo scala dei palazzi e laghetto |
| `test_lampioni_secchiello_molla.py` | Nove controlli su lampioni stradali, secchiello della sabbiera e cavallino a molla |
| `test_parchi_caffe_pontile.py` | Tredici controlli su aiuole e fontanella dei parchi, platea del chiosco e pali del pontile |
| `test_fermata_rotatoria_pieve.py` | Tredici controlli su percorso tattile della fermata, isola centrale delle rotatorie ed edicola votiva della pieve |
| `test_figure_panchina_arredo.py` | Quindici controlli su appoggio figure e bici, panchina del parco giochi e arredi |
| `test_cipressi_paletti_tombini.py` | Quindici controlli su quota dei cipressi, paletti e catena della piazza e tombini |
| `test_tavolini_festoni_piccioni.py` | Nove controlli su basi dei tavolini, festoni e piccioni della piazza |
| `test_sagrato_scooter_siepe.py` | Dieci controlli su sagrato della pieve, scooter e siepe del centro civico |
| `test_contatto_ruote_cassonetti.py` | Dodici controlli su ruote di auto, autobus e furgone, cassonetti sul marciapiede e auto dei piazzali |
| `test_migliorie_v30.py` | Sei controlli su becchi delle anatre, ruote visibili dei cassonetti e orientamento dei lampioni |

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
Gli artefatti del repository (`citta.blend` e `anteprima.png`) sono stati
rigenerati con **Blender 5.0.0** alla ventiquattresima versione.

Per eseguire tutti i **199 test geometrici** (inclusi i controlli sugli
ingombri dei modelli sorgente reali), dalla radice del
repository, nello stesso ambiente Python con `bpy`:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_*.py' -v
```

I test caricano i modelli sorgente per misurarne gli ingombri, ma non aprono né
modificano `citta.blend`, non salvano file e non avviano render.
