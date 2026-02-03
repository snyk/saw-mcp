from __future__ import annotations
from .tools import build_server


def main() -> None:
    app = build_server()
    app.run()


if __name__ == "__main__":
    main()
