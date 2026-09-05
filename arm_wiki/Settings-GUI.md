# Settings GUI

Ripper options (including **OMDB** / **TMDB** API keys) are stored in `arm.yaml` and edited under **Settings → Ripper Settings**.

## Metadata / Movies DB

At the top of Ripper Settings:

- `METADATA_PROVIDER` — `omdb` or `tmdb`
- `OMDB_API_KEY` / `TMDB_API_KEY` — password fields; leave blank to keep the current secret

Save should toast success. If save fails, a failure toast / message appears (older upstream builds often failed silently when booleans were `false`).

## Booleans

Keys such as `MANUAL_WAIT`, `DISABLE_LOGIN`, `HB_HW_AUTO` use true/false selects so yaml is not corrupted.

## Who can edit settings

**Admin** only. Operators can run rips, history, logs, and title search, but not Settings or Database.

## UI settings tab

Presentation options (refresh rates, skin, language) save to the SQLite `UISettings` row, not `arm.yaml`.
