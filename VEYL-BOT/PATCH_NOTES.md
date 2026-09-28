# VEYL 5.1 patch

## Main fix
`/predict` no longer asks for a Solana mint. It now exposes exactly 25 crypto choices in the Discord slash-command dropdown.

The selected asset is resolved internally and VEYL uses:
- Binance real OHLCV candles first (`15m`, up to 200 candles)
- CoinGecko historical prices as a fallback
- the existing VEYL Quant engines for the analysis

## Other fixes
- Added a central 25-asset catalog.
- Added Binance OHLCV support and short-lived candle caching.
- Added short stale-price fallback during Binance outages.
- Added Binance 418/429 handling.
- Added CoinGecko 429 cooldown to avoid repeated rate-limit requests.
- Fixed VEYL chart typography: text/ticks are now readable on the dark background.
- Added `matplotlib` to requirements so the chart engine is available after installation.
- `.env` loading is now automatic.
- `VEYL_TOKEN` is supported, with `DISCORD_TOKEN` as a compatibility fallback.
- Removed the exposed Discord bot token from the project archive.
- `/test` now checks Binance (the primary market provider) instead of making CoinGecko availability a critical requirement.

## Important
A Discord bot token that was previously present in the uploaded archive was exposed during the development exchange. Regenerate/reset that token in the Discord Developer Portal and put the new value in your local `.env`:

`VEYL_TOKEN=YOUR_NEW_TOKEN`

Do not commit `.env`.
