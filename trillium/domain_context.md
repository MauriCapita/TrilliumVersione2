# Trillium V2 — Contesto di Dominio per RAG

> Questo file viene letto automaticamente dal sistema RAG.
> Il contenuto qui scritto viene usato come "conoscenza di base" per guidare
> le risposte dell'AI e migliorare la ricerca nei documenti.
> Se il file è vuoto, il sistema funziona normalmente senza contesto aggiuntivo.

---

## Obiettivo del Sistema

Questo sistema è progettato per **Trillium Pumps Italy S.p.A.** e serve per la
**stima dei pesi dei componenti principali di pompe centrifughe** a partire da:
- Disegni tecnici storici (TIF, PDF)
- Datasheet e parts list di pompe di riferimento
- Parametri di progetto (Nq, pressione, temperatura, materiale, flange rating)

Le risposte devono sempre orientarsi verso la stima dei pesi e l'identificazione
di pompe di riferimento simili nel database.

---

## Formule di Scaling

### Componenti di fusione (casting)
Per giranti, diffusori, bowl, volute, crossover, balance drum:
```
pnew = pref × f^(2.3÷2.4) × ρnew/ρref
```
dove:
- `pref` = peso del componente nella pompa di riferimento (kg)
- `f` = fattore di scala (rapporto diametri girante nuova/riferimento)
- `ρnew/ρref` = rapporto densità tra materiale nuovo e materiale di riferimento
- L'esponente è tipicamente 2.35 (media tra 2.3 e 2.4)

### Componenti pressurizzati
Per corpi pompa (casing), coperchi, barrel, dove lo spessore è critico:
```
pnew = pref × f² × ρnew/ρref × Snew/Sref
```
dove:
- `Snew/Sref` = rapporto spessori parete (nuovo/riferimento)

### Componenti semplici (geometria elementare)
Per colonne, alberi, gomiti, telai motore:
- Cilindri: `W = π/4 × (D² - d²) × L × ρ`
- Coni: media tra diametri × superficie laterale × spessore × densità
- Anelli: come cilindro con altezza ridotta

### Flange
Peso da tabella ASME B16.5 per (dimensione in pollici, rating).
Se il materiale non è acciaio al carbonio, scalare per rapporto densità.

---

## Famiglie di Pompe API 610

### OH — Overhung (a sbalzo)
- **OH1**: End suction overhung — monostadio, la più comune
- **OH2**: Between bearings overhung — con due supporti cuscinetti
- **OH3**: Vertical inline — montaggio verticale in linea
- **OH4**: Rigid coupling overhung
- **OH5**: Close coupled — motore diretto

### BB — Between Bearings (tra cuscinetti)
- **BB1**: Cassa bipartita assialmente, monostadio
- **BB2**: Cassa bipartita assialmente, multistadio
- **BB3**: Barrel multistadio alta pressione
- **BB4**: Between bearings monostadio
- **BB5**: Barrel multistadio — per alte pressioni (boiler feed, injection)

### VS — Vertical Suspended (verticali sospese)
- **VS1**: Verticale monostadio
- **VS4**: Verticale multistadio
- **VS6**: Verticale a can (canned)
- **VS7**: Verticale a doppia cassa

---

## Glossario e Sinonimi

Per migliorare la ricerca, ecco i termini equivalenti usati nei documenti:

| Termine IT | Termine EN | Sinonimi |
|-----------|-----------|---------|
| Girante | Impeller | ruota, runner |
| Corpo pompa | Casing | corpo, housing, barrel (per BB3/BB5) |
| Diffusore | Diffuser | guide vane, palettatura di ritorno |
| Corpo stadio | Bowl | stage casing |
| Albero | Shaft | asse |
| Cuscinetto | Bearing | supporto |
| Tenuta meccanica | Mechanical seal | guarnizione, gland |
| Anello anti-usura | Wear ring | anello di tenuta |
| Colonna | Column pipe | riser pipe |
| Gomito di scarico | Discharge elbow | discharge head |
| Campana aspirazione | Suction bell | inlet bell |
| Supporto motore | Motor frame | motor stool |
| Piastra di tensione | Tension plate | |
| Accoppiamento | Coupling | giunto |
| Basamento | Baseplate | sole plate |
| Flangia | Flange | flangiatura |
| Bulloneria | Bolting | studs, nuts |
| Tamburo bilanciamento | Balance drum | balance disc, balance piston |

---

## Materiali Comuni e Densità

| Materiale | Densità (kg/m³) | Uso tipico |
|-----------|-----------------|------------|
| Carbon Steel (A216 WCB) | 7850 | Materiale di riferimento standard |
| SS 316 / 316L | 7960 | Pompe chimiche, offshore |
| SS 304 | 7930 | Applicazioni generali inox |
| Duplex 2205 | 7820 | Offshore, desalinizzazione |
| Super Duplex 2507 | 7850 | Alta corrosione, acqua di mare |
| 13Cr-4Ni (CA6NM) | 7740 | Giranti di grandi pompe acqua |
| Monel 400 | 8830 | Acido fluoridrico |
| Inconel 625 | 8440 | Alta temperatura e corrosione |
| Hastelloy C-276 | 8890 | Ambienti altamente corrosivi |
| Bronze / NAB | 7600-8800 | Pompe acqua di mare |
| Cast Iron | 7200 | Pompe bassa pressione |
| Titanium Gr.2 | 4510 | Leggero, alta resistenza corrosione |

---

## Mapping Documenti Chiave

Quando si cercano informazioni su specifici argomenti, questi sono i documenti più rilevanti:

| Argomento | Documenti di riferimento |
|-----------|------------------------|
| Spessore parete / castabilità | SOP-569, Mod.546 |
| Selezione cuscinetti | SOP-580, Mod.556 |
| Pulsazioni di pressione | SOP-559, Mod.541 |
| Dimensionamento albero | SOP con analisi rotordinamica |
| Analisi laterale / Long Seals | SOP-518 (§ 5.2.3) |
| Standard pompe | API 610, API 685 |
| Flange | ASME B16.5 |
| Materiali | ASME BPVC Sezione II |

---

## Regole di Validazione

- La temperatura di progetto non deve superare il limite del materiale scelto
- Il flange rating deve essere coerente con la pressione di progetto
- Per pompe multistadio (BB, VS): moltiplicare i componenti "per stadio" per il numero di stadi
- Il fattore di scala `f` è tipicamente tra 0.5 e 2.5
- Se Nq > 100: pompe a flusso misto/assiale (regole di scaling diverse)
- Se Nq < 10: pompe ad alta prevalenza (possibile necessità di più stadi)
