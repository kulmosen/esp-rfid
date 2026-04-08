# ESP-RFID V3 Security Model

## Mål

V3 skal være markant mere sikker end v2 uden at blive urealistisk tung for ESP8266.

## Trusselsbillede

Vi skal mindst beskytte mod:

- uautoriseret åbning via netværket
- kompromitteret eller lækket admin-password
- plaintext-lagring af følsomme credentials og PIN-koder
- manipulation af snapshots eller kommandoer
- replay af gamle kommandoer
- tab af audit-spor ved midlertidig netværksfejl
- for bred lokal recovery-adgang på device

## Grundprincipper

### 1. Adgangsbeslutning er lokal

En angriber skal ikke kunne åbne døren blot ved at DoS’e Home Assistant.

### 2. Central administration er ikke det samme som central enforcement

HA ejer reglerne. Device håndhæver dem.

### 3. Mindst muligt hemmeligt materiale på ESP

Device skal kun have det, der kræves for:

- at verificere snapshots
- at autentificere sig mod HA
- at udføre lokal adgangskontrol

### 4. Ingen plaintext-PIN-lagring

PIN-koder må ikke ligge i klartekst i HA-storage eller på device.

## Credential Model

### RFID Tags

RFID UID bør ikke lagres i klartekst som primær storageform. HA bør gemme en normaliseret hashform, og device bør arbejde med samme normaliserede form i snapshot.

### PIN Codes

PIN bør lagres som:

- unik salt per bruger eller credential
- stærk password hashing i HA
- device-venlig verifier i snapshot

Et pragmatisk v3-design kan bruge PBKDF2-HMAC-SHA256 på device-siden for lokal verificering. Det er ikke det stærkeste tænkelige, men mere realistisk på ESP8266 end tunge memory-hard algoritmer direkte på controlleren.

## Pairing og Device Identity

Hver dørnode skal have:

- et stabilt `device_id`
- en unik device secret
- en recovery secret eller engangspairing-flow

Pairing bør være eksplicit. En ny device må ikke automatisk accepteres af HA uden godkendelse.

## Snapshot Security

Hvert snapshot skal indeholde:

- versionsnummer
- issued-at
- optional expires-at
- monoton version eller revision
- signatur eller MAC

Jeg vil anbefale, at HA signerer snapshots med en delt enhedsnøgle eller en install-nøgle, og at device afviser:

- snapshots med ugyldig signatur
- ældre snapshots end det senest accepterede
- snapshots der mangler obligatoriske felter

## Command Security

Kommandoer som `hold_unlock` og `cancel_hold` skal:

- autentificeres
- tidsbegrænses
- have request-id eller nonce
- kunne afvises ved replay

## Recovery Mode

Recovery mode må ikke være et bagdørspanel til almindelig drift.

Recovery mode bør:

- være fysisk eller lokalt netværksbegrænset
- være tidsbegrænset
- kræve recovery credential
- kun understøtte få funktioner

Tilladte recovery-funktioner kan være:

- netværksrecovery
- bootstrap af ny HA pairing
- eksport af diagnostics

Ikke tilladt i normal recovery:

- fri brugeradministration
- permanent bypass
- anonym hold-open

## Audit og Logs

Alle adgangsbeslutninger skal kunne spores.

Minimum:

- event-id
- device-id
- bruger-id eller ukendt credential
- beslutning
- årsag
- lokal timestamp
- sync-status

Hvis HA er nede:

- events køes lokalt
- events uploades senere
- upload må være idempotent

## Netværk

V3 bør antage lokalt netværk, men ikke stole blindt på det.

Jeg vil anbefale:

- dedikeret HA-bruger eller device-credential per node
- netværkssegmentering hvis muligt
- ingen åbne admin-endpoints uden auth
- stram input-validering på alle device-endpoints

## Home Assistant Som Sikkerhedsgrænse

Når brugeradministration flyttes til HA, skal vi udnytte det aktivt:

- kun HA-administratorer må ændre brugere og adgang
- almindelige dashboards må gerne kunne vise status uden at kunne ændre policy
- unlock og hold-open bør kunne bindes til separate services og rettigheder

## Sikkerhedsbeslutninger Jeg Vil Tage Tidligt

- ingen plaintext-PIN i snapshots
- ingen vilkårlig config-overførsel uden signering/auth
- ingen brugeradministration over åbne device-websockets
- ingen "unlock by IP match only"
- ingen implicit trust i broadcast eller mDNS alene

## Acceptabel V3-Sikkerhed på ESP8266

V3 bør være:

- lille nok til at være stabil på ESP8266
- stærk nok til et privat lokalnet med rigtige trusler
- designet, så en senere ESP32-version kan hæve sikkerhedsniveauet yderligere

Det betyder, at vi skal vælge sikkerhedsmekanismer, der faktisk kan implementeres og vedligeholdes på hardwareplatformen.
