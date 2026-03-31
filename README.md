# Teknik i Väst - Sophämtning

Custom source for [hacs_waste_collection_schedule](https://github.com/mampfes/hacs_waste_collection_schedule) that adds support for **Teknik i Väst** (Arvika, Eda, Årjäng).

## Installation

1. Install [hacs_waste_collection_schedule](https://github.com/mampfes/hacs_waste_collection_schedule) via HACS.
2. Copy `teknikivast_se.py` into your Home Assistant config:
   ```
   config/custom_components/waste_collection_schedule/waste_collection_schedule/source/teknikivast_se.py
   ```
3. Restart Home Assistant.

## Configuration

```yaml
waste_collection_schedule:
  sources:
    - name: teknikivast_se
      args:
        street_address: "Storgatan 17"
```

On first run, a device is registered and an `api_key` is generated. You'll be prompted to select it in the config flow. After that, use:

```yaml
waste_collection_schedule:
  sources:
    - name: teknikivast_se
      args:
        api_key: <generated key>
```

You can also use the Enhets-ID from the Teknik i Väst app (Settings > Om appen).

## Disclaimer

Reverse-engineered integration, not affiliated with Teknik i Väst or Avfallsapp.
