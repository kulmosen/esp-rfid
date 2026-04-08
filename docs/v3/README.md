# ESP-RFID V3 Blueprint

## Vision

ESP-RFID V3 skal flytte projektet fra device-centric administration til et lille, sikkert adgangssystem med:

- central administration i Home Assistant
- lokal adgangsbeslutning på hver dørnode
- lokal fallback, hvis Home Assistant eller netværk er utilgængeligt
- tydelig audit trail og bedre sikkerhedsmodel end den nuværende v2

V3 er målrettet et lille setup med 2 døre i dag og op til 4-5 døre senere.

## Hardware Model

Hver dørnode består af:

- 1 x ESP8266-baseret controller
- 1 x relæudgang mod dør-automatik
- 1 x Wiegand keypad/tag-reader
- valgfri inputs senere, fx dørsensor, tamper eller dørklokke

Relæet skal kunne håndtere to primære kommandoer:

- `pulse_unlock`: Åbn døren i et konfigurerbart tidsvindue
- `hold_unlock`: Hold døren åben så længe signalet er aktivt

Wiegand-input skal kunne håndtere:

- tag-only adgang
- PIN-only adgang
- tag + PIN

## Arkitekturkort

V3 deles i to produkter, der udvikles sammen:

1. ESP door node firmware
2. Home Assistant custom integration

Home Assistant bliver source of truth for:

- brugere
- adgangsregler
- dørtilknytninger
- hændelsesoversigt
- admin-interface

ESP door node bliver source of execution for:

- læsning af Wiegand events
- adgangsbeslutning ud fra seneste godkendte snapshot
- styring af relæ
- buffering af events under netværksfejl

## Kerneprincipper

### 1. Local First Access

En dør må aldrig være afhængig af et live roundtrip til Home Assistant for at kunne åbne for kendte brugere.

### 2. HA As Control Plane

Home Assistant skal være stedet, hvor administratorer opretter brugere, giver adgang og ser status og historik.

### 3. Small, Explicit Firmware

Firmware skal være lille, defensiv og fokuseret på:

- input
- beslutning
- output
- sync

Alt andet hører hjemme i HA-integrationen.

### 4. Secure By Default

V3 skal designes med eksplicit trusselsmodel, mindst mulige privilegier, lokal recovery og bedre beskyttelse af credentials og PIN-data.

## Høj-Niveau Komponenter

### Home Assistant Integration

- config entry for installationen
- subentry per dørnode
- central storage af brugere, rettigheder og snapshots
- service-lag til åbning, hold-open, sync og revoke
- dashboard/panel til administration

### ESP Door Node

- Wiegand driver
- adgangsmotor
- relæ-controller
- lokal snapshot store
- event queue
- HA sync-klient
- recovery web-UI til nødsituationer

## Hvad V3 Ikke Skal Være

- et generelt access-control-system til store installationer
- et nyt MQTT-baseret automationsframework
- et system hvor HA skal være online for hver enkelt adgang

## Foreslået Repo-Struktur

```text
docs/v3/
  README.md
  architecture.md
  security.md
  roadmap.md

v3/
  firmware/
    esp8266-door-node/
  home_assistant/
    custom_components/
      esp_rfid_v3/
```

Selve koden behøver ikke blive scaffoldet endnu. Første skridt er at få designet rigtigt.

## Næste Dokumenter

- [Architecture](./architecture.md)
- [Security](./security.md)
- [Roadmap](./roadmap.md)
