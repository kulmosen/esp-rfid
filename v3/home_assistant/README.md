# ESP-RFID V3 Home Assistant Integration

Dette er første scaffold af `esp_rfid_v3` som Home Assistant custom integration.

## Mål for første iteration

- én central config entry for installationen
- lokal storage af kendte dørnoder
- polling af dørstatus via HTTP
- services til unlock, hold-open, sync og door management
- basisentiteter til statusvisning i HA

## Foreløbige begrænsninger

- der er endnu ikke et custom panel
- dørnoder håndteres foreløbigt via services og storage-flow, ikke færdig UI
- firmware-endpoints er designmål, ikke færdigimplementeret protokol endnu

## Foreslået installation i Home Assistant

Kopier mappen:

```text
v3/home_assistant/custom_components/esp_rfid_v3
```

til:

```text
<ha_config>/custom_components/esp_rfid_v3
```

Genstart Home Assistant og tilføj derefter integrationen via UI.

Hvis du vil arbejde lokalt uden at sætte noget op manuelt, ligger der nu en færdig dev stack i:

```text
v3/dev
```

Se [v3/dev/README.md](./../dev/README.md).

## Foreløbige services

- `esp_rfid_v3.register_door`
- `esp_rfid_v3.remove_door`
- `esp_rfid_v3.register_user`
- `esp_rfid_v3.remove_user`
- `esp_rfid_v3.pulse_unlock`
- `esp_rfid_v3.hold_unlock`
- `esp_rfid_v3.cancel_hold`
- `esp_rfid_v3.resync_door`
- `esp_rfid_v3.sync_all`
- `esp_rfid_v3.reboot_door`
- `esp_rfid_v3.push_snapshot`
- `esp_rfid_v3.push_all_snapshots`

## Næste skridt

- færdig door registry UI
- snapshot format v1
- device simulator for v3 endpoints
- første firmware-side snapshot parser
