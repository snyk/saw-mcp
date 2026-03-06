from __future__ import annotations

import logging

from .tools import build_server

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Snyk API&Web MCP server")
    app = build_server()
    app.run()


if __name__ == "__main__":
    main()
