# ESP-RFID V3 Roadmap

## Fase 0: Blueprint

Målet er at låse arkitektur, sikkerhedsmodel og scope.

Deliverables:

- v3 blueprint
- arkitekturdiagram
- sikkerhedsmodel
- beslutning om sync-protokol

## Fase 1: Home Assistant Skeleton

Målet er at få den centrale del op at stå først.

Deliverables:

- custom integration scaffold
- config entry + door subentries
- central storage-model
- basisentiteter for door status
- services for unlock og hold-open

## Fase 2: Firmware Core

Målet er at få en lille lokal dørmotor uden HA-afhængighed.

Deliverables:

- relay controller
- Wiegand parser
- access engine mod lokal snapshot
- event queue
- recovery mode skeleton

## Fase 3: Sync Layer

Målet er at binde HA og firmware sammen.

Deliverables:

- snapshot format v1
- heartbeat/status
- event upload
- snapshot fetch/apply
- pending command flow

## Fase 4: Security Hardening

Målet er at lukke de vigtigste sikkerhedshuller før pilot.

Deliverables:

- credential protection
- snapshot auth/signature
- replay protection for commands
- diagnostics og audit flow

## Fase 5: Pilot Med Én Dør

Målet er kontrolleret feltprøve uden at sætte begge døre på spil samtidig.

Deliverables:

- staging build
- rollback-procedure
- backup af eksisterende dørdata
- accepttest for normal drift, HA-nedetid og recovery

## Fase 6: To-Dørs Drift

Målet er at migrere begge døre og bevise den centrale model.

Deliverables:

- fælles brugerbase
- dørspecifik adgang
- samlet HA-status
- samlet audit-log

## Produktbeslutninger Jeg Vil Holde Fast I

- Start med 1 dør pr. node.
- Start med HTTP sync frem for kompleks async-MQTT.
- Byg HA først som control plane, ikke bare som dashboard.
- Hold firmware lille, robust og uden stor admin-overflade.

## Foreslået Første Implementeringsmilesten

Hvis vi starter kode næste runde, vil jeg tage denne rækkefølge:

1. scaffold af HA custom integration
2. simpelt device registry i HA
3. snapshot datamodel i Python
4. firmware-side snapshot parser og access engine
5. minimal simulator for v3 device API
6. lokal Home Assistant dev stack med docker-compose
