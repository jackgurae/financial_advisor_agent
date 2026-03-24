import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(Path(__file__).parent / "app" / "main.py", run_name="__main__")
