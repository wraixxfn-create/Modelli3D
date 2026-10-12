# casa_3 — Chalet alpino procedurale ad alto dettaglio

![anteprima](anteprima.png)

Modello 3D procedurale completo di uno **chalet alpino tradizionale (baita tirolese)** a due piani con sottotetto abitabile, basamento in pietra rustica e piano superiore in tronchi di larice (*Blockbau*), balconata panoramica avvolgente intagliata, tetto in scandole di larice posate singolarmente e rigoglioso paesaggio montano. È il terzo modello della raccolta architettonica, dopo il casale tradizionale di [`casa_1`](../casa_1) e la villa contemporanea di [`casa_2`](../casa_2).

Tutta la geometria, i materiali, gli arredi e la vegetazione sono generati interamente da codice in [`genera_chalet.py`](genera_chalet.py), senza dipendenze da file di mesh, texture esterne o pacchetti di terze parti.

| Caratteristica | Dettaglio |
|---|---|
| File Blender | `chalet.blend` (compatibile Blender 4.2+ / Cycles) |
| Script generatore | `genera_chalet.py` (~850 righe di Python procedurale) |
| Risoluzione anteprima | `anteprima.png` (Cycles, 1500 × 1050, AgX) |
| Complessità geometrica | ~984.000 vertici, ~566.000 facce |
| Dimensioni corpo principale | 9,20 × 7,40 m; zoccolo e muri in pietra (40 cm), Blockbau (28 cm) |
| Dimensioni copertura | 11,10 × 10,10 m con ampi sporti (1,35 m in gronda, 0,95 m sui timpani); pendenza 28° |
| Altezza colmo / comignolo | 7,87 m / 9,62 m |
| Materiali procedurali | 22 shader procedurali dedicati (legni, pietre, maiolica, rame, tessuti, flora, cielo) |

---

## Caratteristiche architettoniche del modello

### 1. Basamento e muratura in pietra (Piano Terra)
- Zoccolo perimetrale in pietra squadrata con cordonature ed elementi angolari bugnati (*cantonali*).
- Muratura rustica alpina con vani passanti precisi per porte e finestre.
- Architravi massicce in legno scuro squadrato a vista su tutti i vani del piano terra.
- Fascia marcapiano intagliata di transizione tra muratura in pietra e struttura lignea superiore.

### 2. Struttura Blockbau in legno di larice (Piano Primo e Timpani)
- Pareti a tronchi orizzontali sovrapposti incastrati agli angoli con teste sporgenti (*Kerve / incastri a sella*).
- Timpani aperti con travature alpine sagomate, montanti e rosone centrale traforato in cirmolo.
- Variazione cromatica procedurale tra i singoli tronchi per simulare la naturale stagionatura del legno.

### 3. Balconata panoramica avvolgente e intagli
- Ballatoio a L continuo sul fronte principale Sud e risvolto Ovest.
- Assito in tavole di larice e travi portanti sporgenti rinforzate da saettoni obliqui sagomati.
- Parapetto tradizionale tirolese con montanti intagliati, capriate di raccordo e decine di balaustre sagomate.
- Grandi fioriere in legno massello ricolme di ciuffi di gerani alpini cascanti fioriti di rosso vivo.

### 4. Portico d'ingresso, legnaia e accessori montani
- Porticato d'ingresso coperto su pilastri in legno e plinti in pietra con pavimento in lastre di beola.
- Legnaia laterale con tettoia in scandole e catasta di ciocchi di legna spaccata disposti individualmente.
- Panca rustica in massello con schienale sagomato, antichi sci in frassino con bastoncini e slitta da neve.
- Lanterne in ferro battuto con gabbia forgiata, vetro satinato e sorgente luminosa calda funzionante.

### 5. Copertura alpina in scandole, orditura e lattoneria
- Tetto a due falde con ampia orditura a vista: trave di colmo intagliata, arcarecci intermedi e decine di travetti sagomati.
- Tavolato continuo sottostante e posa di migliaia di singole scandole di larice con sfalsamento di corso e rotazioni organiche.
- Travi fermaneve in tronchi con staffe di ancoraggio in ferro battuto forgiato.
- Grondaie sagomate e pluviali verticali con collari in rame invecchiato.
- Comignolo monumentale in pietra con canna fumaria, capitello di protezione e banderuola segnavento.

### 6. Interni visibili (Stube tirolese e arredi)
- Pavimenti in doghe di larice al piano terra e al primo piano con orditura di travi a soffitto.
- Tradizionale **Stube tirolese** con stufa in maiolica verde bosco lucida, focolare con brace ardente e panca perimetrale riscaldata.
- Grande tavolo conviviale con sedie alpine intagliate e lampadario in ferro battuto.
- Camera da letto con letto matrimoniale in massello, piumone in lana e punti luce caldi.

### 7. Paesaggio e flora alpina
- Terreno collinare montuoso modellato proceduralmente con profilo orografico naturale.
- Fontana monumentale in tronco di larice scavato con cannella in rame e specchio d'acqua corrente.
- Staccionata di recinzione in tronchi scortecciati.
- Sentiero in beole e gradini in pietra naturale.
- Rocce e massi erratici di granito con deformazione organica e muschio.
- Vegetazione alpina dettagliata: ciuffi d'erba montana, arbusti di rododendri fioriti, stelle alpine, genziane blu e margherite.
- Maestosi abeti rossi e pini cembri con rami pendenti e ciuffi di aghi.
- Catena montuosa alpina sullo sfondo con vette rocciose e nevi perenni.

---

## Esecuzione e rendering

Per rigenerare il file `.blend` e/o l'immagine renderizzata serve Python con il modulo `bpy`:

```bash
cd casa_3

# Rigenera il file Blender (chalet.blend) in pochi secondi
python3 genera_chalet.py

# Rigenera il modello e renderizza l'anteprima Cycles (1500x1050)
python3 genera_chalet.py --render

# Render rapido di controllo (840x588, 20 campioni)
python3 genera_chalet.py --quick

# Render personalizzato con parametri specifici
python3 genera_chalet.py --render --samples 64 --res 1920x1080
```

### Parametri CLI supportati

| Flag | Descrizione | Default |
|---|---|---|
| `--render` | Esegue il rendering finale Cycles e salva `anteprima.png` | `False` |
| `--quick` | Modalità bozza rapida (risoluzione ridotta, 20 campioni) | `False` |
| `--samples N` | Numero di campioni di campionamento Cycles | `96` (o `48`/`20` con flag) |
| `--res WxH` | Risoluzione immagine (es. `1920x1080`, `1200x800`) | `1500x1050` |
| `--cam px,py,pz,tx,ty,tz` | Posizione e coordinate target della telecamera | Vista prospettica 3/4 |
