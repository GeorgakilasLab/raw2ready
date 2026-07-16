"""Paths Utilities module.

Configures and ensures existence of standardized application folders
under the configured RAW2READY_OUTPUT_DIR or fallback user home subfolder.
"""

import os
from pathlib import Path


def ensure_dirs():
    """Initializes and creates all default directories for raw2ready.

    Reads the output root from the RAW2READY_OUTPUT_DIR environment variable.
    Falls back to ``~/.raw2ready`` if the variable is not set.

    Creates directories for logs, configs, uploads, cache, temp, exports,
    reports, charts, protocols, and agent_logs if they do not already exist.

    Returns:
        Dictionary mapping directory key names to Path objects.
    """

    base = Path(
        os.environ.get(
            "RAW2READY_OUTPUT_DIR",
            Path.home() / ".raw2ready",
        )
    )

    dirs = {
        "base": base,
        "logs": base / "logs",
        "configs": base / "configs",
        "uploads": base / "uploads",
        "cache": base / "cache",
        "temp": base / "temp",
        "exports": base / "exports",
        "reports": base / "reports",
        "charts": base / "charts",
        "protocols": base / "protocols",
        "agent_logs": base / "agent_logs",
    }

    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    return dirs