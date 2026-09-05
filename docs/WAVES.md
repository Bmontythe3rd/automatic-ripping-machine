# ARM Fork Waves

Running changelog for the Bmontythe3rd fork of Automatic Ripping Machine.
Use this to understand what changed and how to roll back.

## Rollback

| Tag | Meaning |
|-----|---------|
| `pre-wave5-baseline` | Stable point after Waves 1–4 (reliability + Docker + UI modernization). **Undo Waves 5+.** |
| `wave5-complete` | Settings GUI / API key save fixes |
| `wave6-complete` | Hardware encode auto-select + compose GPU/DRI docs |
| `wave7-complete` | Multi-user + TOTP 2FA |

```bash
git fetch fork
git checkout main
git reset --hard pre-wave5-baseline   # destructive
# or: git checkout -b restore-baseline pre-wave5-baseline
```

**Wave 7 DB note:** rolling back code after migrating adds user columns. Restore a SQLite backup from before Wave 7, or keep the DB (extra columns are harmless for older code if unused).

### Locked out of 2FA

```bash
# Inside the container or on host with sqlite3 against arm.db:
sqlite3 /home/arm/db/arm.db \
  "UPDATE user SET totp_enabled=0, totp_secret=NULL, backup_codes=NULL WHERE email='admin';"
```

Or as Admin: Users → Clear 2FA for that account.

## Waves 1–4 (already shipped)

- **Wave 1:** DB lock fixes, SQLite WAL, drive identity, abandon process tree, Flask secret
- **Wave 2:** MakeMKV DVD path, title-wait fixes, compose + drive poller script
- **Wave 3:** Fail empty rips, optional in-image drive poller
- **Wave 4:** Media-workshop UI (`arm.css`), home active-rips redesign

## Current fork status

- Branch: `main`
- Baseline: `pre-wave5-baseline`
- Waves 5–7: landed (see below)

## Wave 5 — Settings GUI

**Problem fixed:** Ripper Settings save failed/corrupted yaml when booleans were `false` (Jinja empty string + `DataRequired`), and AJAX only toasted success. OMDB/TMDB keys live in `arm.yaml` and now save correctly from the GUI.

**Changes:**

- [`arm/ui/settings_save.py`](../arm/ui/settings_save.py) — merge POST onto current config; mask secrets; bool coercion
- Ripper Settings: Metadata subsection; bool `<select>`; password fields for keys
- `/save_settings` no longer gated on incomplete `SettingsForm` path validators
- Failure toasts; `DISABLE_LOGIN` applied live to Flask config
- Tests: `test/unittest/test_settings_save.py`

## Wave 6 — Hardware encode

**Changes:**

- [`arm/ripper/hw_transcode.py`](../arm/ripper/hw_transcode.py) — probe NVENC/QSV/VCN; auto preset (NVIDIA → Intel → AMD → software)
- `HB_HW_AUTO` in [`setup/arm.yaml`](../setup/arm.yaml) (default true for new installs)
- `correct_hb_settings()` uses auto when enabled
- Settings → System Info: HW status + “Enable auto HW encode”
- Docs: [`docs/hardware-transcode.md`](hardware-transcode.md); compose comments for `/dev/dri` and NVIDIA
- Tests: `test/unittest/test_hw_transcode.py`

## Wave 7 — Multi-user + TOTP 2FA

**Changes:**

- User model: `role` (`admin`|`operator`), `totp_*`, `backup_codes`, `is_active`
- Alembic: `a1b2c3d4e5f6_user_auth_fields`
- Login by username; `/login/2fa` for TOTP/backup codes
- `/account` — enable/disable 2FA (QR via `qrcode`)
- `/users` — Admin create/disable/reset password/clear 2FA
- Settings + Database routes require **Admin**; Operators keep home/rips/history/logs/jobs
- Deps: `pyotp`, `qrcode` in `requirements.txt`

**After upgrade:** open Settings once (or let DB migrate) so Alembic runs; existing `admin` becomes Admin.
