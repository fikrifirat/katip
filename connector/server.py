"""Plugin entry point: `python3 ${CLAUDE_PLUGIN_ROOT}/server.py` starts the local Katip MCP server."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from katip_kalkan.launch import main  # noqa: E402

main()
