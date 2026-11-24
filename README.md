# Mannaka（まんなか）

Find the fairest train station for a group to meet in the Tokyo area.

- Pick each person's nearest station (最寄駅); the app finds stations where everyone's trip is about equally long (or equally priced).
- View-only members can join without being counted.
- Per-person "+ minutes" for a bus, bike or long walk to the station.
- Opens Google Maps or Apple Maps to find dinner, cafés, bars or parking near the chosen station.
- Runs entirely in the browser: no paid APIs.

## Status

Prototype. Travel times are **estimates** from station positions and typical line speeds (often 20–30% off); fares are rough. Rooms use the free ntfy.sh relay (no accounts needed); rooms last about 12 hours. Next steps: real timetables (ODPT), weekday/holiday schedules, delays, and a Supabase backend for rooms.

## Data

Station data: 国土数値情報 鉄道データ (N02), Ministry of Land, Infrastructure, Transport and Tourism, via [antfu/mlit-json](https://github.com/antfu/mlit-json). Rebuild `rail.json` with:

```
pip install pykakasi
python tools/build_data.py path/to/mlit-json/data rail.json
```
