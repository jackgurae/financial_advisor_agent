import sys
from pathlib import Path

from streamlit.web.cli import main as streamlit_main


STREAMLIT_APP_PATH = Path(__file__).resolve().parent / "main.py"


def main() -> None:
    sys.argv = ["streamlit", "run", str(STREAMLIT_APP_PATH)]
    streamlit_main()


if __name__ == "__main__":
    main()
