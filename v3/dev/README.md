# ESP-RFID V3 Local Dev Stack

Dette miljø giver en lokal Home Assistant testinstans og to simulerede dørnoder.

## Hvad der følger med

- 1 x Home Assistant container på `http://127.0.0.1:8123`
- 1 x frontdør-simulator på `http://127.0.0.1:18101`
- 1 x bagdør-simulator på `http://127.0.0.1:18102`
- synkroniseret kopi af `esp_rfid_v3` integrationen i dev-konfigurationen

## Start

```sh
/Users/dennis/RadixCloud/A-IT/Projekter/esp-rfid/v3/dev/up.sh
```

Scriptet synkroniserer custom integrationen ind i `v3/dev/homeassistant/custom_components`,
før containerne startes. Det gør miljøet mere robust på Docker Desktop og efter genstarter.

## Stop

```sh
cd /Users/dennis/RadixCloud/A-IT/Projekter/esp-rfid/v3/dev
docker compose down
```

## Første opsætning i Home Assistant

1. Åbn `http://127.0.0.1:8123`
2. Gennemfør Home Assistant onboarding
3. Tilføj integrationen `ESP-RFID V3`
4. Åbn sidebar-punktet `ESP-RFID V3`
5. Registrér dørnoder og brugere direkte i admin-panelet

## Demo dørdata

Frontdør simulator:

- `device_id`: `frontdoor`
- `name`: `Front Door`
- `base_url`: `http://esp_rfid_v3_frontdoor:18101`
- `api_token`: `frontdoor-dev-token`

Vigtigt: brug ikke `http://127.0.0.1:18101` eller `http://localhost:18101` inde i Home Assistant.
Fra HA-containeren peger `127.0.0.1` på containeren selv, ikke på frontdør-simulatoren.

Bagdør simulator:

- `device_id`: `backdoor`
- `name`: `Back Door`
- `base_url`: `http://esp_rfid_v3_backdoor:18102`
- `api_token`: `backdoor-dev-token`

## Eksempel på service call i Home Assistant

Service: `esp_rfid_v3.register_door`

```yaml
device_id: frontdoor
name: Front Door
base_url: http://esp_rfid_v3_frontdoor:18101
api_token: frontdoor-dev-token
allow_hold_open: true
enabled: true
```

Gentag med `backdoor` for den anden simulator.

Eksempel på bruger:

Service: `esp_rfid_v3.register_user`

```yaml
user_id: dennis
name: Dennis
door_ids:
  - frontdoor
  - backdoor
rfid_uid: A1B2C3D4
pin: "1234"
active: true
```

## Smoke Test

Du kan teste simulatoren uden Docker via:

```sh
python3 /Users/dennis/RadixCloud/A-IT/Projekter/esp-rfid/v3/dev/simulator/smoke_test.py
```
