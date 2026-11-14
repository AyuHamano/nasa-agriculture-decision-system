"""API MVP de recomendações agrícolas com contexto climático da NASA POWER.

Execute na raiz do projeto com:
    uvicorn backend.api:app --reload
"""
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.gemini_api_test import (
    DEFAULT_MODEL,
    NASA_PARAMS,
    gerar_resposta,
    montar_prompt,
    obter_resumo_nasa_power,
)

app = FastAPI(title="RaizViva API", version="0.1.0")
API_MAX_OUTPUT_TOKENS = 1200
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCATION_NAME = "Silvânia"
DEFAULT_LATITUDE = -16.66
DEFAULT_LONGITUDE = -48.61
MODIS_CONTEXT_PATH = (
    PROJECT_ROOT / "data" / "cache" / "silvania" / "modis_silvania_context.json"
)
SMAP_CONTEXT_PATH = PROJECT_ROOT / "data" / "cache" / "silvania" / "smaps-silvania.json"


class RecommendationRequest(BaseModel):
    location_name: str | None = Field(default=None, min_length=1, max_length=120)
    latitude: float = Field(default=DEFAULT_LATITUDE, ge=-90, le=90)
    longitude: float = Field(default=DEFAULT_LONGITUDE, ge=-180, le=180)
    rotation: list[str] = Field(min_length=2, max_length=8)
    priorities: list[str] = Field(default_factory=list, max_length=5)
    start_year: int = Field(default=2015, ge=1981)
    end_year: int = Field(default=2025, ge=1981)

    @field_validator("rotation", "priorities")
    @classmethod
    def clean_items(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("Os itens não podem estar vazios.")
        return cleaned

    @field_validator("location_name")
    @classmethod
    def clean_location_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("O nome da localização não pode estar vazio.")
        return cleaned


class RecommendationResponse(BaseModel):
    context: dict[str, Any]
    recommendation: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def load_modis_context(latitude: float, longitude: float) -> dict[str, Any] | None:
    if not MODIS_CONTEXT_PATH.exists():
        return None

    try:
        saved = json.loads(MODIS_CONTEXT_PATH.read_text(encoding="utf-8"))
        site = saved["location"]
        site_latitude = float(site["latitude"])
        site_longitude = float(site["longitude"])
        context = {
            "dataset": saved["dataset"],
            "status": "cached",
            "period": saved["period"],
            "summary": saved["monthly_indicators"],
            "metadata": {
                "spatial_resolution": saved["spatial_resolution"],
                "temporal_resolution": saved["temporal_resolution"],
                "quality_filter": saved["quality_filter"],
                "limitations": saved["limitations"],
                "valid_observations": saved["valid_observations"],
            },
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Cache MODIS inválido em {MODIS_CONTEXT_PATH}.") from error

    if (round(latitude, 4), round(longitude, 4)) != (
        round(site_latitude, 4),
        round(site_longitude, 4),
    ):
        return None

    return context


def load_smap_context(latitude: float, longitude: float) -> dict[str, Any] | None:
    if not SMAP_CONTEXT_PATH.exists():
        return None

    try:
        saved = json.loads(SMAP_CONTEXT_PATH.read_text(encoding="utf-8"))
        metadata = saved["metadata"]
        site = metadata["coordinates"]
        site_latitude = float(site["latitude"])
        site_longitude = float(site["longitude"])
        if (round(latitude, 2), round(longitude, 2)) != (
            round(site_latitude, 2),
            round(site_longitude, 2),
        ):
            return None
        if metadata["status"] != "DONE":
            raise ValueError("A tarefa SMAP não está concluída.")

        smap_launch_date = metadata["period"]["smap_launch_date"]
        monthly_values: dict[int, dict[str, list[float]]] = {}
        valid_observations = 0
        dates: list[str] = []
        for row in saved["data"]:
            if row["date"] < smap_launch_date or row["quality_flag"] != 0:
                continue

            values = {
                "surface_soil_moisture": float(row["sm_surface"]),
                "rootzone_soil_moisture": float(row["sm_rootzone"]),
                "surface_wetness": float(row["sm_surface_wetness"]),
                "rootzone_wetness": float(row["sm_rootzone_wetness"]),
            }
            if not all(math.isfinite(value) for value in values.values()):
                continue

            month = int(row["month"])
            month_values = monthly_values.setdefault(
                month,
                {name: [] for name in values},
            )
            for name, value in values.items():
                month_values[name].append(value)
            valid_observations += 1
            dates.append(row["date"])

        if not monthly_values:
            raise ValueError("O cache SMAP não contém observações válidas.")

        monthly_indicators = [
            {
                "month": month,
                "surface_soil_moisture_mean_m3_m3": round(
                    fmean(values["surface_soil_moisture"]), 3
                ),
                "rootzone_soil_moisture_mean_m3_m3": round(
                    fmean(values["rootzone_soil_moisture"]), 3
                ),
                "surface_wetness_mean_0_1": round(
                    fmean(values["surface_wetness"]), 3
                ),
                "rootzone_wetness_mean_0_1": round(
                    fmean(values["rootzone_wetness"]), 3
                ),
                "valid_days": len(values["surface_soil_moisture"]),
            }
            for month, values in sorted(monthly_values.items())
        ]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Cache SMAP inválido em {SMAP_CONTEXT_PATH}.") from error

    return {
        "dataset": metadata["dataset"],
        "status": "cached",
        "period": {"start": min(dates), "end": max(dates)},
        "spatial_resolution": "~9 km (produto L3 Enhanced)",
        "temporal_resolution": "diária, agregada em médias climatológicas mensais",
        "quality_filter": "quality_flag == 0; observações anteriores ao início da missão excluídas",
        "units": {
            "soil_moisture": "m³/m³",
            "wetness": "índice adimensional de 0 a 1",
        },
        "valid_observations": valid_observations,
        "monthly_indicators": monthly_indicators,
        "limitations": (
            "Resolução espacial aproximada de 9 km; não representa medições "
            "diretas do talhão. A umidade de raízes é uma estimativa do produto "
            "combinado, não uma medição direta da camada de raízes."
        ),
    }


@app.post("/api/recommendations", response_model=RecommendationResponse)
def create_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    if request.start_year > request.end_year:
        raise HTTPException(status_code=422, detail="start_year não pode ser maior que end_year.")

    location = request.location_name
    if location is None:
        if (round(request.latitude, 4), round(request.longitude, 4)) == (
            DEFAULT_LATITUDE,
            DEFAULT_LONGITUDE,
        ):
            location = DEFAULT_LOCATION_NAME
        else:
            location = f"propriedade em {request.latitude:.4f}, {request.longitude:.4f}"
    try:
        power_summary = obter_resumo_nasa_power(
            request.latitude,
            request.longitude,
            request.start_year,
            request.end_year,
        )
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar NASA POWER: {error}") from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    try:
        modis_context = load_modis_context(request.latitude, request.longitude)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    try:
        smap_context = load_smap_context(request.latitude, request.longitude)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    environmental_evidence: list[dict[str, Any]] = [
        {
            "dataset": "NASA POWER",
            "period": f"{request.start_year}-{request.end_year}",
            "parameters": NASA_PARAMS,
            "summary": power_summary,
            "limitations": (
                "Dados climáticos em grade associados às coordenadas informadas; "
                "não são medições diretas do talhão nem previsão meteorológica."
            ),
        }
    ]
    unavailable_datasets = []
    if modis_context is not None:
        environmental_evidence.append(modis_context)
    else:
        unavailable_datasets.append(
            {
                "dataset": "MODIS",
                "status": "unavailable",
                "reason": (
                    "O contexto MODIS pré-processado está disponível somente para "
                    "o ponto de Silvânia (-16.6600, -48.6100)."
                ),
            }
        )
    if smap_context is not None:
        environmental_evidence.append(smap_context)
    else:
        unavailable_datasets.append(
            {
                "dataset": "SMAP",
                "status": "unavailable",
                "reason": (
                    "O contexto SMAP pré-processado está disponível somente "
                    "para Silvânia, nas coordenadas aproximadas "
                    "(-16.6589, -48.6081)."
                ),
            }
        )

    context: dict[str, Any] = {
        "location": {
            "name": location,
            "latitude": request.latitude,
            "longitude": request.longitude,
        },
        "current_rotation": request.rotation,
        "farmer_priorities": request.priorities,
        "environmental_evidence": environmental_evidence,
        "unavailable_datasets": unavailable_datasets,
        "data_gaps": [
            "Análise de solo e histórico de manejo da propriedade.",
            "Datas reais de plantio e colheita, cultivares, irrigação e produtividade.",
            "Restrições de maquinário, mercado local e ocorrência de pragas/doenças.",
        ],
    }

    prompt = montar_prompt(
        location,
        " -> ".join(request.rotation),
        ", ".join(request.priorities),
        json.dumps(context, ensure_ascii=False, indent=2),
    )
    try:
        recommendation = gerar_resposta(
            prompt,
            DEFAULT_MODEL,
            API_MAX_OUTPUT_TOKENS,
        )
    except RuntimeError as error:
        status_code = 503 if "GEMINI_API_KEY" in str(error) else 502
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    return RecommendationResponse(context=context, recommendation=recommendation)
