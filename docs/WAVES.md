# ARM Fork Waves

Running changelog for the Bmontythe3rd fork of Automatic Ripping Machine.
Use this to understand what changed and how to roll back.

## Rollback

| Tag | Meaning |
|-----|---------|
| `pre-wave5-baseline` | Stable point after Waves 1–4 (reliability + Docker + UI modernization). **Use this to undo Waves 5+.** |
| `wave5-complete` | Settings GUI / API key save fixes |
| `wave6-complete` | Hardware encode auto-select + compose GPU/DRI profiles |
| `wave7-complete` | Multi-user + TOTP 2FA |

```bash
# Inspect baseline without changing branch
git show pre-wave5-baseline

# Hard reset local main to baseline (destructive — discard later commits)
git fetch fork
git checkout main
git reset --hard pre-wave5-baseline

# Or check out the tag in a detached worktree / branch for comparison
git checkout -b restore-baseline pre-wave5-baseline
```

Database migrations added in Wave 7 require care when rolling back: restore a DB backup from before Wave 7, or remove new user columns manually if you must keep the SQLite file.

## Waves 1–4 (already shipped)

- **Wave 1:** DB lock fixes, SQLite WAL, drive identity, abandon process tree, Flask secret
- **Wave 2:** MakeMKV DVD path, title-wait fixes, compose + drive poller script
- **Wave 3:** Fail empty rips, optional in-image drive poller
- **Wave 4:** Media-workshop UI (`arm.css`), home active-rips redesign

## Current fork status

- Branch: `main`
- Baseline tag: `pre-wave5-baseline` (created at start of Waves 5–7 work)
- Waves 5–7: in progress (see sections below as they land)

## Wave 5 — Settings GUI

*(Filled when Wave 5 lands.)*

## Wave 6 — Hardware encode

*(Filled when Wave 6 lands.)*

## Wave 7 — Multi-user + 2FA

*(Filled when Wave 7 lands.)*
