"""API MVP de recomendações agrícolas com contexto climático da NASA POWER.

Execute na raiz do projeto com:
    uvicorn backend.api:app --reload
"""
import json
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


class RecommendationRequest(BaseModel):
    location_name: str | None = Field(default=None, min_length=1, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
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


@app.post("/api/recommendations", response_model=RecommendationResponse)
def create_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    if request.start_year > request.end_year:
        raise HTTPException(status_code=422, detail="start_year não pode ser maior que end_year.")

    location = request.location_name or (
        f"propriedade em {request.latitude:.4f}, {request.longitude:.4f}"
    )
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

    context: dict[str, Any] = {
        "location": {
            "name": location,
            "latitude": request.latitude,
            "longitude": request.longitude,
        },
        "current_rotation": request.rotation,
        "farmer_priorities": request.priorities,
        "environmental_evidence": [
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
        ],
        "unavailable_datasets": [
            {
                "dataset": "MODIS",
                "status": "paused",
                "reason": "Consulta temporariamente fora do escopo desta versão da API.",
            },
            {
                "dataset": "SMAP",
                "status": "paused",
                "reason": "Consulta temporariamente fora do escopo desta versão da API.",
            },
        ],
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
