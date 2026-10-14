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
- fontana a due vasche, pavimentazione in lastre, caffè all'aperto, panchine,
  lampioni, aiuole, festoni colorati e due **rotatorie fiorite** con fontana;
- **otto palazzi** residenziali/commerciali su basamento in pietra, con
  vetrine, balconi, tende, insegne, marcapiani, corpo scala vetrato e
  **coperture calpestabili**:
  pergolato, tavolo e sedie, lettini, ombrellone, fioriere, stendino, comignoli,
  due lucernari, corpo scala con ringhiera e fotovoltaico inclinato;
- **trentatré case** istanziate dai modelli esistenti (casale, villa
  contemporanea, chalet alpino) con giardini privati, siepi, orti e frutteti;
- viali, incroci rialzati, marciapiedi correttamente interrotti ai nodi,
  attraversamenti pedonali con **rampe e piastre tattili**, segnaletica,
  lampioni stradali, due **piazzali di testata** di Viale Roma, due parcheggi
  di quartiere con auto in sosta, automobili, autobus, furgone del mercato,
  scooter, biciclette e pensilina;
- **prati curati**: undici isolati con manto erboso tagliato a bande alternate,
  cordolo di chiusura e bordura di fiori, e piazzole di ghiaia con corona di
  fiori ai ventisei alberi da viale e da parco, legate da siepi basse;
- **vita di strada**: pedoni, ciclisti, persone sedute, piccioni in piazza e
  uccelli in volo, panni stesi sui balconi, cassonetti, edicola e tombini;
- **Parco delle Rose** con laghetto, anatre, ninfee, canne e pontile in legno,
  e **Giardino del Borgo** con parco giochi: altalene, scivolo, sabbiera;
- ciliegi fioriti ripresi dal modello `albero_2`, alberature urbane
  procedurali e cipressi;
- **campagna circostante**: colline dolci che si chiudono sull'orizzonte senza
  gradini, boschi di macchia mediterranea sui pendii, campi di grano, vigne e
  uliveti a filari, cipressi isolati e il borgo sul
  colle a nord-ovest — pieve con abside e rosone, campanile a vela, sei case a
  capanna su zoccoli quotati, muro di cinta, uliveto e una **strada bianca**
  che scende fino all'anello stradale della città — e oltre le colline tre
  **dorsali lontane in foschia** che chiudono l'orizzonte, con **cumuli** nel
  cielo.

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
