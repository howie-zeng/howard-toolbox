# LAN Gomoku

Browser-based 五子棋 for two players on the same WiFi / local network.

## Setup

Use the default Python environment, not `pyprod`.

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python -m gomoku.run --host 0.0.0.0 --port 8000
```

The host can open:

```text
http://localhost:8000
```

Coworkers on the same WiFi/LAN should open the LAN URL printed by the command, usually something like:

```text
http://192.168.x.x:8000
```

The game page also shows copyable room links and prefers the LAN IP link over `127.0.0.1`.

## If Coworkers Cannot Connect

1. Confirm the server is running with `--host 0.0.0.0`.
2. Check Windows Firewall and allow Python on private networks if prompted.
3. Run `ipconfig` and use the IPv4 address for the active WiFi adapter.
4. Some guest or corporate WiFi networks isolate clients; if so, same-WiFi browser play may be blocked by the network.

## Gameplay

- Freestyle Gomoku: 15x15 board, black first, no forbidden moves, `>=5` contiguous stones wins.
- Stones land on line intersections, with star points and coordinate labels for easier move discussion.
- No login. Players enter only a display name.
- The browser stores a hidden local player ID so refresh/reconnect can reclaim the same seat.
- Joiners start as spectators and can claim an open black or white seat.
- Undo (`悔棋`) rolls back the latest move only after both seated players agree.
- After a win or draw, both seated players must accept rematch.
- The interface defaults to a quiet low-distraction theme; use the Quiet / Classic toggle to switch back to the original board-game style.
