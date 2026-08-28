# SOL desk CLI

One terminal command runs both paper books, the lock agent, and the board.

```bash
cd ~/xrp-swing-formula
chmod +x scripts/desk.sh
./scripts/desk.sh up
```

Then open http://localhost:8501. The board reloads every 15 seconds.

| Command | What it does |
|---|---|
| `./scripts/desk.sh up` | git pull, lock check, start 1m + 15m + lock agent + dashboard |
| `./scripts/desk.sh down` | stop all four |
| `./scripts/desk.sh status` | which processes are alive + last lock result |
| `./scripts/desk.sh pull` | git pull only |
| `./scripts/desk.sh dash` | restart the dashboard only |
| `./scripts/desk.sh lock` | run the formula-drift audit once |

Grok cloud automations cannot start processes on this Mac. This script is the local hook.
