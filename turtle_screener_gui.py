#!/usr/bin/env python3
"""Local browser GUI for turtle_screener.py.

The existing turtle_screener.py CLI remains the scan engine. This file only
provides a local configuration page and runs the scan in a background thread.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from turtle_screener import TurtleConfig, scan


@dataclass(frozen=True)
class GuiRunConfig:
    input_csv: str
    output_root: str
    timeframe: str
    period: str
    entry_period: int
    exit_period: int
    atr_period: int
    atr_stop_multiple: float
    signal_candle: str
    batch_size: int
    delay_seconds: float
    only_buy: bool


STATE: dict[str, object] = {"running": False, "status": "Siap", "output": "", "error": ""}
STATE_LOCK = threading.Lock()

HTML = """<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Turtle Screener / TuTCI</title>
<style>
:root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
body { margin: 0; background: #111827; color: #e5e7eb; }
main { max-width: 980px; margin: 30px auto; padding: 0 18px; }
.card { background: #1f2937; border: 1px solid #374151; border-radius: 14px; padding: 22px; margin-bottom: 16px; box-shadow: 0 10px 30px #0003; }
h1 { margin: 0 0 5px; font-size: 26px; } h2 { font-size: 17px; margin-top: 0; color: #93c5fd; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 13px 18px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #cbd5e1; }
input, select { box-sizing: border-box; width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #4b5563; background: #111827; color: #f9fafb; }
.full { grid-column: 1 / -1; } .inline { flex-direction: row; align-items: center; gap: 10px; }
.inline input { width: auto; } .radio { display: flex; gap: 18px; flex-wrap: wrap; }
button { padding: 11px 18px; border: 0; border-radius: 8px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; }
button:disabled { opacity: .5; cursor: wait; } .muted { color: #94a3b8; font-size: 13px; }
#status { white-space: pre-wrap; min-height: 80px; background: #0b1220; border-radius: 8px; padding: 13px; color: #c7d2fe; }
@media (max-width: 700px) { .grid { grid-template-columns: 1fr; } .full { grid-column: auto; } }
</style>
</head>
<body><main>
<div class="card"><h1>Turtle Screener / TuTCI</h1><div class="muted">GUI ini menjalankan turtle_screener.py. Script CLI tetap dapat digunakan terpisah.</div></div>
<form id="scan-form" class="card"><h2>Konfigurasi scan</h2><div class="grid">
<label class="full">Input CSV
<input name="input_csv" value="__INPUT__" required></label>
<label class="full">Output folder
<input name="output_root" value="__OUTPUT__" required></label>
<label>Yahoo period<input name="period" value="2y"></label>
<label>Batch size<input name="batch_size" type="number" min="1" value="50"></label>
<label>Entry length<input name="entry_period" type="number" min="1" value="20"></label>
<label>Exit length<input name="exit_period" type="number" min="1" value="10"></label>
<label>ATR period<input name="atr_period" type="number" min="1" value="20"></label>
<label>ATR stop multiple<input name="atr_stop_multiple" type="number" min="0.01" step="0.1" value="2.0"></label>
<label>Delay antar batch (detik)<input name="delay_seconds" type="number" min="0" step="0.1" value="0"></label>
<label>Timeframe<select name="timeframe"><option value="daily">Daily</option><option value="weekly">Weekly dari candle daily</option></select></label>
<label>Status sinyal<select name="signal_candle"><option value="current">Current candle</option><option value="h-1">H-1 / candle selesai</option></select></label>
<label class="inline full"><input name="only_buy" type="checkbox"> Simpan chart hanya untuk candle sinyal BUY</label>
</div><br><button id="run" type="submit">Mulai Scan</button></form>
<div class="card"><h2>Status</h2><div id="status">Siap</div></div>
</main>
<script>
const form = document.querySelector('#scan-form'); const button = document.querySelector('#run'); const status = document.querySelector('#status');
function readForm() { const data = Object.fromEntries(new FormData(form).entries()); data.only_buy = form.only_buy.checked; return data; }
form.addEventListener('submit', async (event) => { event.preventDefault(); button.disabled = true; status.textContent = 'Memulai scan...';
  const response = await fetch('/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(readForm())});
  const result = await response.json(); if (!response.ok) { status.textContent = result.error || 'Konfigurasi tidak valid'; button.disabled = false; return; } poll();
});
async function poll() { const response = await fetch('/status'); const data = await response.json(); status.textContent = data.error ? 'ERROR: ' + data.error : (data.output ? data.status + '\nOutput: ' + data.output : data.status);
  if (data.running) setTimeout(poll, 1000); else button.disabled = false; }
</script></body></html>"""


def _validate_config(payload: dict[str, Any]) -> tuple[GuiRunConfig, TurtleConfig]:
    input_csv = Path(str(payload.get("input_csv", ""))).expanduser()
    if not input_csv.is_file():
        raise ValueError(f"Input CSV tidak ditemukan: {input_csv}")
    config = TurtleConfig(
        timeframe=str(payload.get("timeframe", "daily")),
        entry_period=int(payload.get("entry_period", 20)),
        exit_period=int(payload.get("exit_period", 10)),
        atr_period=int(payload.get("atr_period", 20)),
        atr_stop_multiple=float(payload.get("atr_stop_multiple", 2.0)),
        signal_candle=str(payload.get("signal_candle", "current")),
    )
    batch_size = int(payload.get("batch_size", 50))
    delay_seconds = float(payload.get("delay_seconds", 0))
    if batch_size < 1:
        raise ValueError("Batch size harus >= 1")
    if delay_seconds < 0:
        raise ValueError("Delay tidak boleh negatif")
    run_config = GuiRunConfig(
        input_csv=str(input_csv),
        output_root=str(Path(str(payload.get("output_root", "image"))).expanduser()),
        timeframe=config.timeframe,
        period=str(payload.get("period", "2y")).strip(),
        entry_period=config.entry_period,
        exit_period=config.exit_period,
        atr_period=config.atr_period,
        atr_stop_multiple=config.atr_stop_multiple,
        signal_candle=config.signal_candle,
        batch_size=batch_size,
        delay_seconds=delay_seconds,
        only_buy=bool(payload.get("only_buy", False)),
    )
    return run_config, config


def _run_background(run_config: GuiRunConfig, config: TurtleConfig) -> None:
    try:
        output = scan(
            input_csv=run_config.input_csv,
            output_root=run_config.output_root,
            config=config,
            period=run_config.period,
            batch_size=run_config.batch_size,
            delay_seconds=run_config.delay_seconds,
            only_buy=run_config.only_buy,
        )
        with STATE_LOCK:
            STATE.update(running=False, status="Selesai", output=str(output), error="")
    except Exception as exc:  # noqa: BLE001 - surface worker error in the GUI
        with STATE_LOCK:
            STATE.update(running=False, status="Gagal", error=str(exc))


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/status":
            with STATE_LOCK:
                self._send_json(dict(STATE))
            return
        project_dir = Path(__file__).resolve().parent
        page = HTML.replace("__INPUT__", str(project_dir / "data" / "all_stock.csv")).replace("__OUTPUT__", str(project_dir / "image"))
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/run":
            self._send_json({"error": "Endpoint tidak ditemukan"}, 404)
            return
        with STATE_LOCK:
            if STATE["running"]:
                self._send_json({"error": "Scan masih berjalan"}, 409)
                return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            run_config, config = _validate_config(payload)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, 400)
            return
        with STATE_LOCK:
            STATE.update(running=True, status="Scanning...", output="", error="")
        threading.Thread(target=_run_background, args=(run_config, config), daemon=True).start()
        self._send_json({"ok": True})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    url = "http://127.0.0.1:8765"
    print(f"Turtle Screener GUI: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGUI dihentikan")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
