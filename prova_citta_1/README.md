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
| `test_fermata_bandiera_viali.py` | Dieci controlli su pensilina, tricolore e filari dei viali |
| `test_vetrine_scale.py` | Sette controlli su corpi scala e vetrine del piano terra |

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

Per eseguire tutti i **74 test geometrici** (i sei della decima versione, i 19
di urbanistica, i quattro della dodicesima, i dieci della tredicesima, i nove
della quattordicesima, i nove della quindicesima, i dieci della sedicesima e i sette
della diciassettesima,
inclusi i controlli sugli ingombri dei modelli sorgente reali), dalla radice del
repository, nello stesso ambiente Python con `bpy`:

```bash
python3 -m unittest discover -s prova_citta_1 -p 'test_*.py' -v
```

I test caricano i modelli sorgente per misurarne gli ingombri, ma non aprono né
modificano `citta.blend`, non salvano file e non avviano render.
