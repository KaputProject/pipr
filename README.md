# Python Blockchain Rudarjenje (MPI & Multiprocessing)

Projekt implementira rudarjenje bločne verige (Proof-of-Work) s podporo za paralelizacijo in porazdeljeno obdelavo.

## Zmožnosti

- **Porazdeljeno rudarjenje (MPI):** Uporaba več procesov/računalnikov za skupno rudarjenje.
- **Lokalno večnitno rudarjenje:** Uporaba `multiprocessing` za izkoriščanje vseh jeder enega računalnika.
- **MQTT Integracija:** Prejemanje podatkov za bloke preko MQTT protokola.
- **Dinamična težavnost:** Prilagajanje težavnosti rudarjenja glede na hitrost.

## Struktura projekta

- `main.py`: Vstopna točka. Privzeto zažene MPI rudarjenje, lahko pa se preklopi na lokalno.
- `mpi_mining.py`: Logika za porazdeljeno MPI rudarjenje.
- `block.py` / `blockchain.py`: Osnovni razredi za verigo blokov.
- `utils/`:
    - `mqttListener.py`: Razred za upravljanje MQTT povezave v ozadju.
    - `mqttUtils.py`: Pomožne funkcije za MQTT.
    - `blockchainUtils.py`: Pomožne funkcije za izpis in statistiko.
- `server.py`: Testna skripta za MQTT server.

## Namestitev

### 1. Python knjižnice

Namestite potrebne pakete:

```bash
pip install -r requirements_mpi.txt
```
*(Če `requirements_mpi.txt` ne obstaja, namestite: `mpi4py`, `paho-mqtt`, `python-dotenv`)*

### 2. MPI (Za porazdeljeno rudarjenje)

Za delovanje v načinu MPI je potrebna namestitev Microsoft MPI (na Windows):
- Prenesite in namestite **MS-MPI v10.0** (ali novejši): [Povezava](https://docs.microsoft.com/en-us/message-passing-interface/microsoft-mpi)
- Potrebujete `msmpisetup.exe` (Runtime) in `msmpisdk.msi` (SDK).

## Konfiguracija

### MQTT
Ustvari `.env` datoteko v korenski mapi projekta (po potrebi):
```env
MQTT_BROKER=ssl://broker.hivemq.com:8883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password
```

### Nastavitve rudarjenja
Nastavitve se nahajajo v `main.py` in `mpi_mining.py`:
- `fixed_difficulty`: Fiksna težavnost (npr. 5). Če je `None`, se uporablja dinamična.
- `block_limit`: Število blokov, preden se program ustavi.
- `RUN_MPI_MINING` (v `main.py`): `True` za MPI, `False` za lokalno multiprocessing.

## Uporaba

### 1. Porazdeljeno rudarjenje (MPI) - Privzeto

Zagon glavne skripte bo samodejno poskusil zagnati MPI rudarjenje:

```bash
python main.py
```

To bo uporabilo `mpiexec` za zagon procesov (privzeto uporabi vsa jedra).

Za ročni zagon z določenim številom procesov (npr. 4):
```bash
mpiexec -n 4 python mpi_mining.py
```

#### Zagon na več računalnikih (Cluster)
1. Namesti MS-MPI in Python odvisnosti na vseh računalnikih.
2. Kopiraj projekt na vsa vozlišča (ista pot).
3. Zaženi `smpd -d` na vseh vozliščih.
4. Uredi `hostfile.txt` z IP-ji in številom procesov.
5. Zaženi: `mpiexec -f hostfile.txt -n <skupno_procesov> python mpi_mining.py`

### 2. Lokalno večnitno rudarjenje

Če ne želite uporabljati MPI, uredite `main.py` in nastavite:
```python
if __name__ == "__main__":
    RUN_MPI_MINING = False  # <--- Nastavi na False
    ...
```
Nato zaženite:
```bash
python main.py
```
Program bo uporabljal `multiprocessing.Pool` za rudarjenje na lokalnem stroju.

## MQTT Listener

Projekt uporablja prenovljen `MqttListener` razred (`utils/mqttListener.py`) za asinhrono prejemanje podatkov.
- Ko pride novo sporočilo na temo `blockchain/data` (oz. nastavljeno temo), se vsebina doda v čakalno vrsto.
- Rudarji uporabijo te podatke kot vsebino ("data") za naslednji blok.

## Arhitektura

### MPI Način
- **Rank 0 (Server):** 
  - Inicializira `MqttListener`.
  - Upravlja Blockchain stanje.
  - Generira naloge (`TaskMessage`) in jih pošilja delavcem.
  - Preverja rešitve in dodaja bloke.
- **Rank 1+ (Workers):**
  - Prejmejo nalogo.
  - Zaženejo več nitno rudarjenje (lokalni `multiprocessing`).
  - Ko najdejo "nonce", pošljejo blok nazaj strežniku.

### Odpravljanje težav

- **`ImportError: No module named mpi4py`**: Preverite namestitev `mpi4py`. Če uporabljate Anaconda: `conda install mpi4py`. Na Windowsih z pip morda potrebujete MS-MPI SDK.
- **MPI se ne zažene:** Preverite, da je `mpiexec` v sistemski poti (PATH).
- **MQTT napake:** Preverite `.env` datoteko in internetno povezavo. Če broker ni dosegljiv, program nadaljuje brez MQTT.
