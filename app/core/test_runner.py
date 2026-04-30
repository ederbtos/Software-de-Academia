import subprocess
import threading
from datetime import datetime
from pathlib import Path


class TestRunState:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.started_at = None
        self.finished_at = None
        self.return_code = None
        self.logs = []

    def snapshot(self):
        with self.lock:
            return {
                "running": self.running,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
                "return_code": self.return_code,
                "logs": list(self.logs),
            }


STATE = TestRunState()


def _append_log(line: str):
    with STATE.lock:
        STATE.logs.append(line.rstrip())
        if len(STATE.logs) > 1000:
            STATE.logs = STATE.logs[-1000:]


def start_test_run():
    with STATE.lock:
        if STATE.running:
            return False
        STATE.running = True
        STATE.started_at = datetime.utcnow()
        STATE.finished_at = None
        STATE.return_code = None
        STATE.logs = ["Iniciando suite de testes..."]

    thread = threading.Thread(target=_run_pytest, daemon=True)
    thread.start()
    return True


def _run_pytest():
    cmd = ["pytest", "-q", "tests"]
    _append_log(f"Comando: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(Path(__file__).resolve().parents[2]),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            _append_log(line)
        return_code = proc.wait()
    except Exception as exc:
        _append_log(f"Falha ao executar testes: {exc}")
        return_code = 1

    with STATE.lock:
        STATE.return_code = return_code
        STATE.finished_at = datetime.utcnow()
        STATE.running = False
        if return_code == 0:
            STATE.logs.append("Suite finalizada com sucesso.")
        else:
            STATE.logs.append("Suite finalizada com falhas.")
