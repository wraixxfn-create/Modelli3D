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
- **otto palazzi** residenziali/commerciali con vetrine, balconi, tende,
  insegne, marcapiani, corpo scala vetrato e **coperture calpestabili**:
  pergolato, tavolo e sedie, lettini, ombrellone, fioriere, stendino, comignoli,
  due lucernari, corpo scala con ringhiera e fotovoltaico inclinato;
- **trentatré case** istanziate dai modelli esistenti (casale, villa
  contemporanea, chalet alpino) con giardini privati, siepi, orti e frutteti;
- viali, incroci rialzati, marciapiedi, attraversamenti pedonali, segnaletica,
  lampioni stradali, due parcheggi di quartiere con auto in sosta, automobili,
  autobus, furgone del mercato, scooter, biciclette e pensilina;
- **prati curati**: dieci isolati con manto erboso tagliato a bande alternate,
  cordolo di chiusura e bordura di fiori, e piazzole di ghiaia con corona di
  fiori ai ventisei alberi da viale e da parco, legate da siepi basse;
- **vita di strada**: pedoni, ciclisti, persone sedute, piccioni in piazza e
  uccelli in volo, panni stesi sui balconi, cassonetti, edicola e tombini;
- **Parco delle Rose** con laghetto, anatre, ninfee, canne e pontile in legno,
  e **Giardino del Borgo** con parco giochi: altalene, scivolo, sabbiera;
- ciliegi fioriti ripresi dal modello `albero_2`, alberature urbane
  procedurali e cipressi;
- **campagna circostante**: colline dolci che si chiudono sull'orizzonte senza
  gradini, boschi di macchia mediterranea sui pendii, campi di grano e uliveti
  a filari, cipressi isolati e il borgo sul
  colle a nord-ovest — pieve con abside e rosone, campanile a vela, sei case a
  capanna su zoccoli quotati, muro di cinta, uliveto e una **strada bianca**
  che scende fino all'anello stradale della città.

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
