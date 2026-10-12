# Modelli3D

Raccolta di modelli 3D in formato Blender (`.blend`), generati in modo
procedurale da script Python (modulo `bpy`). Ogni cartella contiene il modello,
lo script che lo costruisce e un'immagine di anteprima renderizzata con Cycles.

| Cartella | Modello | File |
|---|---|---|
| [`albero_1`](albero_1) | Albero a foglia larga con chioma, radici e foglie a terra | `albero.blend`, `genera_albero.py`, `anteprima.png` |
| [`albero_2`](albero_2) | Ciliegio ornamentale in fiore: ~56 000 mazzetti istanziati (GN), petali a terra e in aria, erba | `ciliegio.blend`, `genera_ciliegio.py`, `anteprima.png` |
| [`casa_1`](casa_1) | Casale a due piani con tetto in coppi, serramenti, balcone e giardino | `casa.blend`, `genera_casa.py`, `anteprima.png` |
| [`casa_2`](casa_2) | Villa contemporanea: facciata vetrata a doppia altezza, tetto piano con fotovoltaico, terrazza, interni arredati, piscina a sfioro | `villa.blend`, `genera_villa.py`, `anteprima.png` |

Per rigenerare un modello serve il modulo Python di Blender:

```bash
pip install bpy
cd casa_1 && python3 genera_casa.py --render
cd casa_2 && python3 genera_villa.py --render
cd albero_2 && python3 genera_ciliegio.py -- --render
```
