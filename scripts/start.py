"""Start both services with the same interpreter; Ctrl+C stops both."""
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
def main():
    children=[]
    try:
        for module in ('aggregator.aggregator_server', 'app'):
            children.append(subprocess.Popen([sys.executable,'-m',module],cwd=ROOT))
        print('Open http://127.0.0.1:5000 (or your configured FLASK_PORT). Ctrl+C to stop.', flush=True)
        while all(c.poll() is None for c in children): time.sleep(.5)
        print('A service exited; stopping the other service.',file=sys.stderr)
        return 1
    except KeyboardInterrupt: return 0
    finally:
        for child in children:
            if child.poll() is None: child.terminate()
        for child in children:
            try: child.wait(timeout=10)
            except subprocess.TimeoutExpired: child.kill();child.wait()
if __name__=='__main__': raise SystemExit(main())
