"""Shared AppEEARS authentication, task polling, and CSV download helpers."""
import os
import time
from pathlib import Path
from typing import Any

import requests

API = "https://appeears.earthdatacloud.nasa.gov/api"
TASK_WAIT_SECONDS = 600
TASK_POLL_SECONDS = 20
ACTIVE_STATUSES = {"pending", "queued", "processing", "running"}
FAILED_STATUSES = {"error", "failed", "cancelled", "canceled"}


class AppEEARSTaskTimeout(RuntimeError):
    def __init__(self, task_id: str, status: str):
        self.task_id = task_id
        self.status = status
        super().__init__(
            f"Tarefa AppEEARS {task_id} continua em status '{status}' após "
            f"{TASK_WAIT_SECONDS} segundos. O ID foi mantido para retomar a consulta."
        )


def earthdata_headers() -> dict[str, str]:
    user = os.getenv("EARTHDATA_USER")
    password = os.getenv("EARTHDATA_PASS")
    if not user or not password:
        raise RuntimeError(
            "Defina EARTHDATA_USER e EARTHDATA_PASS no arquivo .env da raiz do projeto."
        )

    response = requests.post(
        f"{API}/login",
        auth=(user, password),
        timeout=60,
    )
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError("O login Earthdata não retornou um token AppEEARS.")
    return {"Authorization": f"Bearer {token}"}


def download_task_csv(
    task: dict[str, Any],
    headers: dict[str, str],
    destination: Path,
    task_id_file: Path,
) -> Path:
    if destination.exists():
        return destination

    task_id_file.parent.mkdir(parents=True, exist_ok=True)
    if task_id_file.exists():
        task_id = task_id_file.read_text(encoding="utf-8").strip()
        if not task_id:
            raise RuntimeError(f"Arquivo de ID da tarefa está vazio: {task_id_file}")
        print(f"[api] retomando tarefa AppEEARS {task_id}")
    else:
        response = requests.post(f"{API}/task", json=task, headers=headers, timeout=60)
        response.raise_for_status()
        task_id = response.json().get("task_id")
        if not task_id:
            raise RuntimeError("AppEEARS não retornou o ID da tarefa criada.")
        task_id_file.write_text(task_id, encoding="utf-8")
        print(f"[api] tarefa criada: {task_id}")

    deadline = time.monotonic() + TASK_WAIT_SECONDS
    while True:
        response = requests.get(f"{API}/task/{task_id}", headers=headers, timeout=60)
        response.raise_for_status()
        task_status = response.json().get("status")
        print(f"[api] status da tarefa {task_id}: {task_status}")

        if task_status == "done":
            break
        if task_status in FAILED_STATUSES:
            raise RuntimeError(
                f"Tarefa AppEEARS {task_id} terminou com status '{task_status}'. "
                f"Consulte a tarefa no AppEEARS antes de tentar novamente."
            )
        if task_status not in ACTIVE_STATUSES:
            raise RuntimeError(
                f"Status inesperado '{task_status}' para a tarefa AppEEARS {task_id}."
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AppEEARSTaskTimeout(task_id, task_status)
        time.sleep(min(TASK_POLL_SECONDS, remaining))

    response = requests.get(f"{API}/bundle/{task_id}", headers=headers, timeout=60)
    response.raise_for_status()
    files = response.json().get("files", [])
    result_file = next(
        (file for file in files if file.get("file_name", "").endswith("-results.csv")),
        None,
    )
    if result_file is None:
        filenames = [file.get("file_name") for file in files]
        raise RuntimeError(f"CSV de resultados não encontrado no AppEEARS: {filenames}")

    response = requests.get(
        f"{API}/bundle/{task_id}/{result_file['file_id']}",
        headers=headers,
        timeout=300,
    )
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    print(f"[cache] salvo em {destination}")
    return destination
