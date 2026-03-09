# SQLite Migration Notes

## What changed
- Runtime data is now stored in SQLite at `data/skanak.db` by default.
- Legacy JSON files are imported automatically on startup (one time), then backed up in `data/legacy_backups/`.
- Main code path now reads from SQLite for:
  - economy user stats
  - lottery state
  - rename locks
  - counting state
  - meme index
  - cheese leaderboard state

## Why this is safe for deployment
- `git push` only ships code.
- Database files stay on the VPS filesystem and are not overwritten by git.
- On first restart after deploy, if DB is empty, legacy JSON is imported automatically.

## VPS deploy flow
1. Backup current runtime data before first deploy:
   - `cd /opt/SkanakBot/Skanak`
   - `tar -czf /tmp/skanak-runtime-backup-$(date +%F).tgz economy/*.json counting/*.json meme_sender/*.json`
2. Deploy code:
   - `sudo update-skanak`
3. Check logs:
   - `journalctl -u skanak-bot -n 120 --no-pager`
4. Confirm DB exists:
   - `ls -lh /opt/SkanakBot/Skanak/data/skanak.db`

## Optional: custom DB location
Set `SKANAK_DB_PATH` in your service environment if you want another path.
