# Órbita Rural

Órbita Rural is a decision-support system for farmers, created by Equipe Agronautas for the NASA Space Apps Challenge 2026 challenge “Field Shift: Adapting Farms with NASA Data.” It brings together a browser-based application and a Python engine to help farmers understand field conditions, compare crop rotations, and review past seasons.

The project uses public Earth-observation and agricultural data. It is not a NASA product or endorsed by NASA, and it does not replace a farmer’s judgment or advice from an agronomist.

## What it does

The app supports decisions at three points in the crop cycle:

- **Today:** Displays the field’s status and indicators for available soil water, crop stage, heat, satellite-observed greenness, soil cover, and a water-stress alert.
- **Rehearse:** Compares three crop-rotation scenarios across water shortfall, heat during critical crop stages, and consecutive days without living soil cover. It also provides evidence, risks, and a day-by-day replay of a difficult season.
- **Log:** Reviews a completed season and lets the farmer record a harvest estimate locally in the browser.

Farmers can set up their field through a guided conversation and ask the assistant questions from any screen. An agronomist view exposes technical details, assumptions, and the engine’s full results.

The interface currently supports three municipalities in Goiás, Brazil—Rio Verde, Jataí, and Silvânia—and rotations based on soybeans followed by maize, maize with brachiaria grass, or sorghum. The results describe regional data for a municipality, not measurements from an individual plot.

## Data and calculations

The engine combines:

- **GPM IMERG** precipitation, **NASA POWER** temperature, and **MODIS** vegetation-index observations.
- A daily soil-water balance based on **FAO-56**, crop calendars, and soil water-holding categories.
- Agricultural and validation data from sources including **IBGE** and **INMET**.

The application displays the available data dates and identifies assumptions where applicable. When the API is unavailable, the browser can use the pre-generated datasets included with the frontend; those values may not reflect the latest data.

## Run the application

### Option 1: Open the frontend with its included data

Open [`frontend/orbita/index.html`](frontend/orbita/index.html) in a browser. The interface loads pre-generated data from the repository and does not require the API. Its screens and assistant are currently in Portuguese.

### Option 2: Run the frontend with the local API

Use Python 3. From the repository root, start the API in one terminal:

```bash
cd backend
python3 -m orbita.api
```

By default, the API listens on `http://127.0.0.1:8000`. In a second terminal, serve the frontend:

```bash
cd frontend/orbita
python3 -m http.server 8080
```

Open <http://127.0.0.1:8080/?api=http://127.0.0.1:8000>. The API’s calculation routes do not need an API key. To use the AI assistant, set an OpenRouter key in the environment of the terminal running the API, then start the server:

```bash
export OPENROUTER_API_KEY="your-key"
python3 -m orbita.api
```

The assistant is optional; the dashboard, rotation comparison, and season log continue to work without it. Do not put a real key in a committed file. The API is intended for local use by default; do not expose it to an untrusted network without appropriate protection.

### Run the engine from the command line

From `backend/`, the engine can also be used without starting the API:

```bash
python3 -m orbita.perguntar --lavoura-hoje
python3 -m orbita.perguntar --cidade rio_verde --rotacao soja,milho --plantio 2026-11-10
python3 -m orbita.perguntar --replay 2015-16
python3 -m orbita.perguntar --registro 2015-16
```

Use `--json` with supported commands to print structured results. The engine’s defaults and available options are documented in [`backend/orbita/README.md`](backend/orbita/README.md).

## Run the tests

From `backend/`:

```bash
python3 -m unittest
```

## Repository map

| Path | Contents |
| --- | --- |
| [`backend/orbita/`](backend/orbita/) | Python calculation engine, HTTP API, assistant, and tests |
| [`frontend/orbita/`](frontend/orbita/) | Browser app, pre-generated data, and interface assets |
| [`data/orbita/`](data/orbita/) | Source datasets and data-download utilities |
| [`docs/orbita/`](docs/orbita/) | Project documentation, validation notes, and challenge materials |

For the detailed English project guide, see [`docs/orbita/README.en.md`](docs/orbita/README.en.md). API routes and request examples are in [`backend/orbita/API.md`](backend/orbita/API.md); the frontend guide is in [`frontend/orbita/LEIA-ME.md`](frontend/orbita/LEIA-ME.md) (Portuguese).
