from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .tools import build_server

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                Path.home() / 'saw-mcp.log',
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=3),  # Keep 3 backup files
            logging.StreamHandler()  # Also keep console output
        ])
    logger.info("Starting Snyk API&Web MCP server")
    app = build_server()
    app.run()


if __name__ == "__main__":
    main()
