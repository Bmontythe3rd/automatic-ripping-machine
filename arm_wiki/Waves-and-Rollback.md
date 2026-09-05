# Waves and Rollback

Full detail lives in the repo: [`docs/WAVES.md`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docs/WAVES.md).

## Tags

| Tag | Meaning |
|-----|---------|
| `pre-wave5-baseline` | After Waves 1–4 (stability + UI). Safe undo for Waves 5+ |
| `wave5-complete` | Settings GUI / API key saves |
| `wave6-complete` | Hardware encode auto |
| `wave7-complete` | Multi-user + TOTP |

```bash
git fetch origin   # or: git fetch fork
git checkout main
git reset --hard pre-wave5-baseline   # destructive
```

## Wave summary

1. **Reliability** — DB locks, WAL, drive identity, abandon kill tree, Flask secret  
2. **Rip path / Docker** — MakeMKV DVD path, compose, drive poller  
3. **Success detection** — fail empty rips; optional poller service  
4. **UI** — media-workshop theme  
5. **Settings GUI** — bools, secrets, OMDB/TMDB save correctly  
6. **HW encode** — `HB_HW_AUTO`  
7. **Auth** — Admin/Operator + TOTP  

## 2FA lockout recovery

```bash
sqlite3 data/home/db/arm.db \
  "UPDATE user SET totp_enabled=0, totp_secret=NULL, backup_codes=NULL WHERE email='admin';"
```
