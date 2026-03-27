# 🛰 ASTRA — LEO Pass Predictor

Daily forecast of visible LEO satellite passes over Loiano Observatory,
delivered automatically every morning via Telegram.

**Observatory:** Loiano | 44°16'N 11°19'E | 841 m a.s.l.
**Part of:** [ASTRA project](https://www.inaf.it) — INAF-OAS Bologna

---

## What it does

Every day at 06:00 UTC the pipeline:

1. Downloads the full TLE catalog from [Celestrak](https://celestrak.org) (~3000 objects)
2. Filters for LEO objects only (orbital period < 128 min)
3. Computes all passes over Loiano for the upcoming night using [Skyfield](https://rhodesmill.org/skyfield/)
4. Keeps only **visible** passes: satellite sunlit + observer in astronomical darkness + elevation ≥ 20°
5. Sorts by maximum elevation and sends the top 25 to Telegram

No LLM involved — this is structured orbital mechanics, plain formatting is faster and cheaper.

---

## Example output

```
🛰 ASTRA — LEO Pass Forecast
Loiano | Tonight | March 27, 2026
Min elevation: 20° | Times: UTC
─────────────────────────────

#1 ISS (ZARYA)
   Rise 20:14 → Max 78.3° (S) → Set 20:21
   Culmination: 20:17:42 | Dist: 421 km

#2 STARLINK-2271
   Rise 21:03 → Max 45.1° (SW) → Set 21:09
   Culmination: 21:06:18 | Dist: 558 km

...

─────────────────────────────
Total visible passes: 18
Sorted by max elevation
```

---

## Setup

### 1. Create a Telegram Bot (skip if you already have one)
- Message `@BotFather` → `/newbot`
- Copy the bot token
- Get your chat ID from `@userinfobot`

### 2. Create a new GitHub repository
- Name it `astra-leo-predictor` (or anything you like)
- Set visibility to **Private**

### 3. Upload the files
Upload all files from this zip. For the `.github/workflows/` folder,
create it manually via **Add file → Create new file** and name it
`.github/workflows/leo_predictor.yml`.

### 4. Add GitHub Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name          | Value                        |
|----------------------|------------------------------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID`   | Your numeric Telegram ID      |

These are the same secrets as `astro-digest` — you can reuse the same bot.

### 5. Test manually
**Actions → ASTRA LEO Pass Predictor → Run workflow**

From then on it runs automatically every day at 06:00 UTC (07:00/08:00 Italian time).

---

## Project structure

```
leo-predictor/
├── fetcher.py      — downloads TLE catalog from Celestrak
├── predictor.py    — computes passes with Skyfield, filters visible + sunlit
├── formatter.py    — formats the Telegram report
├── main.py         — orchestrator + error notifications
├── requirements.txt
└── .github/
    └── workflows/
        └── leo_predictor.yml   — cron: daily at 06:00 UTC
```

## Dependencies

| Package    | Purpose                        |
|------------|--------------------------------|
| `skyfield` | Orbital mechanics, pass finding |
| `requests` | TLE download + Telegram API     |
| `numpy`    | Magnitude estimation            |

---

## Customisation

| Parameter | File | Default | Description |
|---|---|---|---|
| `MIN_ELEVATION_DEG` | `predictor.py` | `20.0` | Minimum pass elevation |
| `MAX_LEO_PERIOD_MIN` | `predictor.py` | `128.0` | LEO filter threshold |
| `max_objects` | `main.py` | `3000` | TLE catalog size |
| `max_passes` | `main.py` | `25` | Max passes in report |
| Cron schedule | `leo_predictor.yml` | `0 6 * * *` | When to run |

---

## Part of ASTRA

This tool supports observational planning for the **ASTRA** wide-field optical network
for LEO Space Situational Awareness, developed at INAF-OAS Bologna.

Pipeline: `astra_pipeline_main.py` | TLE matching: `astra_TLE_matcher.py`
