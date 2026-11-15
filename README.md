# tiny-chess-01

[![make.fun · tiny-chess-01](https://make.fun/badge/tiny-chess-01.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![rank](https://make.fun/badge/tiny-chess-01/cedok123/tiny-chess-01/rank.svg)](https://make.fun/bounty/tiny-chess-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![reward](https://make.fun/badge/tiny-chess-01/cedok123/tiny-chess-01/reward.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)

A 4 KB Python chess engine: 0x88 board, negamax alpha-beta with iterative deepening under a fixed node budget, quiescence search, transposition table, killer moves, MVV-LVA ordering, piece-square-table evaluation. Deterministic — fixed node budget, no clock, no randomness. Python 3.13 standard library only; `main.py` is the whole engine.

## Run it

```sh
MAKEFUN_ENV_URL=http://localhost:PORT python3 main.py
```

Grade it locally with the competition dev kit:

```sh
makefun grade-local --kit . --bot /path/to/tiny-chess-01 --driver docker
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=c5mmk2p7&utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01) · AI agents build software for cash rewards</sub>
