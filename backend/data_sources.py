"""Adapters that collect and summarize NASA AppEEARS datasets for one farm point."""
import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "backend" / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@lru_cache(maxsize=2)
def _load_collector(name: str, filename: str) -> ModuleType:
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar o coletor {filename}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _cache_name(latitude: float, longitude: float) -> str:
    point = f"{latitude:.4f}_{longitude:.4f}".replace("-", "m").replace(".", "p")
    return f"farm_{point}"


def collect_modis(
    latitude: float,
    longitude: float,
    start_year: int,
    end_year: int,
) -> dict[str, Any]:
    collector = _load_collector("modis_dataset_collector", "modis-dataset-colector.py")
    name = _cache_name(latitude, longitude)
    try:
        csv_path = collector.baixar(latitude, longitude, start_year, end_year, name)
        monthly = collector.processar(csv_path)
    except SystemExit as error:
        raise RuntimeError(str(error)) from error

    if monthly.empty:
        raise RuntimeError("MODIS não retornou observações válidas para o ponto.")

    return {
        "dataset": "MODIS Terra MOD13Q1.061",
        "period": f"{start_year}-{end_year}",
        "spatial_resolution": "250 m",
        "temporal_resolution": "compostos de 16 dias, agregados por mês",
        "quality_filter": "pixel_reliability <= 1",
        "monthly_indicators": json.loads(
            monthly.reset_index().to_json(orient="records", force_ascii=False)
        ),
        "limitations": (
            "NDVI é um indicador de vigor da vegetação, não identifica sozinho "
            "a cultura nem comprova condição do solo."
        ),
    }


def collect_smap(
    latitude: float,
    longitude: float,
    start_year: int,
    end_year: int,
) -> dict[str, Any]:
    collector = _load_collector("smap_dataset_collector", "smap-dataset-colector.py")
    name = f"{_cache_name(latitude, longitude)}_{start_year}_{end_year}"
    try:
        product = collector.descobrir_produto()
        csv_path = collector.baixar(
            {"farm": (latitude, longitude)},
            max(start_year, 2015),
            end_year,
            product,
            name,
        )
        indicators = collector.processar(csv_path).get("farm")
    except SystemExit as error:
        raise RuntimeError(str(error)) from error

    if indicators is None:
        raise RuntimeError("SMAP não retornou observações válidas para o ponto.")

    return {
        "dataset": f"NASA SMAP L3 Enhanced ({product})",
        "period": indicators["meta"]["periodo"],
        "spatial_resolution": "~9 km",
        "temporal_resolution": "diária, agregada por mês e ano",
        "indicators": indicators,
        "limitations": indicators["meta"]["aviso"],
    }
