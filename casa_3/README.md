# casa_3 — Chalet alpino (base del modello)

![anteprima](anteprima.png)

Modello 3D di uno **chalet di montagna a due piani**: zoccolo in pietra, corpo
in legno con tavole orizzontali e grande tetto a due falde con gronde molto
sporgenti. È il terzo tipo di casa della raccolta, dopo il casale tradizionale
di [`casa_1`](../casa_1) e la villa contemporanea di [`casa_2`](../casa_2).

Questa è la **prima versione del modello**: contiene solo la base della casa,
senza troppi dettagli. Tutto è costruito **in modo procedurale** dallo script
[`genera_chalet.py`](genera_chalet.py): nessuna geometria importata, nessuna
texture esterna.

| | |
|---|---|
| File del modello | `chalet.blend` (Blender 4.2+ / 5.0, Cycles) |
| Script generatore | `genera_chalet.py` |
| Anteprima | `anteprima.png` (render Cycles 1500×1050, 96 campioni) |
| Ingombro | corpo 9,0 × 7,0 m; gronde a 10,2 × 8,9 m; colmo a 9,3 m |
| Unità | metri (sistema metrico, scala 1:1) |
| Geometria | ~1 200 vertici, ~900 facce |
| Materiali | 6 materiali procedurali (nessuna texture esterna) |
| Seme casuale | `SEED = 20261013` (risultato deterministico) |

## Cosa contiene (per ora)

**Struttura (collezione `Edificio`)**
- zoccolo in pietra che sporge 6 cm dal filo dei muri, alto 84 cm, con la
  gradinata d'ingresso in pietra (4 gradini da 21 cm)
- corpo in legno su due piani: muri con spessore reale di 28 cm e **vani
  passanti** (le finestre e la porta hanno spalle vere, non disegnate)
- timpani in legno sui due prospetti corti

**Copertura (collezione `Tetto`)**
- due falde in tavole scure con pendenza 26°, gronde sporgenti 95 cm sulle
  facciate e 60 cm sui timpani (il filo del tetto si vede da sotto, come nei
  chalet veri)
- colmo in legno

**Serramenti ridotti all'essenziale (collezione `Serramenti`)**
- vetri scuri incassati nei vani con telai piatti in legno scuro
- porta d'ingresso massiccia in legno con telaio
- niente ante, persiane, davanzali o maniglie: arrivano nelle prossime versioni

**Terreno (collezione `Terreno`)**
- prato pianeggiante a maglia unica

**Scena** — cielo procedurale (Nishita, quota 1 200 m), sole alle 34° di
elevazione, camera 38 mm con profondità di campo, Cycles + AgX.

## Prossimi passi

Il modello è volutamente rimasto alla base: nelle prossime iterazioni si
possono aggiungere balconi in legno con balaustrini, persiane e ante con
vetri, comignolo in pietra, interni visibili, vialetto, erba e alberi di
montaggio, magari un po' di neve sul tetto.

## Rigenerare il modello

Serve il modulo Python di Blender 4.x/5.x (`pip install bpy`):

```bash
cd casa_3
python3 genera_chalet.py                          # ricostruisce chalet.blend (<1 s)
python3 genera_chalet.py --render                 # + anteprima.png (Cycles CPU)
python3 genera_chalet.py --render --res 900x630 --samples 24   # anteprima rapida
```

| Opzione | Effetto |
|---|---|
| `--render` | salva anche l'anteprima (`anteprima.png`) |
| `--quick` | anteprima rapida (840×588, 20 campioni) |
| `--samples N` | campioni Cycles (predefiniti 96) |
| `--res WxH` | risoluzione dell'anteprima (predefinita 1500x1050) |
| `--cam px,py,pz,tx,ty,tz` | posizione e bersaglio della camera (per viste di controllo) |

La costruzione della geometria richiede meno di un secondo; il render di
anteprima (1500×1050, 96 campioni, denoiser) qualche minuto su CPU.
