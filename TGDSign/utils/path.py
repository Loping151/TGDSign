"""TGDSign 资源 / 缓存目录"""

from pathlib import Path

from gsuid_core.data_store import get_res_path

MAIN_PATH = get_res_path() / "TGDSign"
MAIN_PATH.mkdir(parents=True, exist_ok=True)

CACHE_BASE = MAIN_PATH / "cache"
ANN_CACHE_PATH = CACHE_BASE / "ann"
ANN_RENDER_CACHE_PATH = ANN_CACHE_PATH / "rendered"
BAKE_PATH = CACHE_BASE / "bake"
TEMP_PATH = Path(__file__).parents[1] / "templates"

for p in (CACHE_BASE, ANN_CACHE_PATH, ANN_RENDER_CACHE_PATH, BAKE_PATH):
    p.mkdir(parents=True, exist_ok=True)
