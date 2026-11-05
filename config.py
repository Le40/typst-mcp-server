from pathlib import Path
import tomllib

SERVER_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SERVER_DIR / "config.local.toml"

with CONFIG_PATH.open("rb") as file:
    settings = tomllib.load(file)

PROJECT_ROOT = (SERVER_DIR / settings["project_root"]).resolve()

OUTPUT_DIR = PROJECT_ROOT / settings["output_dir"]

READ_PATHS = settings["permissions"]["read"]
CREATE_PATHS = settings["permissions"]["create"]

CUSTOM_EXPORTER = settings.get("custom_exporter")