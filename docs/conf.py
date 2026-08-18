"""Compatibility entry point for local Sphinx commands.

Read the Docs builds from ``docs/source/conf.py``. Keep this file as a thin
forwarder so local commands cannot silently use a different configuration.
"""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).parent / "source" / "conf.py"), run_name=__name__)
