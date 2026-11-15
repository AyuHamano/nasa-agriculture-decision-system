<!-- Generated with AI (Claude) -->
# Órbita Rural · mission control for the field

Versão em português: [LEIA-ME.md](LEIA-ME.md)

## 1. What it is

Órbita Rural is the app built by team **Equipe Agronautas** for the NASA Space Apps Challenge 2026, challenge "Field Shift: Adapting Farms with NASA Data". It follows the field all year round with open NASA data:

- **Before planting, the farmer rehearses.** "I planted my soybeans late: is maize still worth it, or should I go with sorghum?" The app puts the farmer's crop rotation next to two others and shows how each one came through ten seasons of real weather: the water the crop lacked, the strong heat, and the days the soil had no living plants.
- **During the season, the farmer keeps watch.** The "My field today" screen shows the crop stage, the water in the soil, the heat, the greenness seen from orbit, the soil cover, and an alert: if it doesn't rain, in how many days the crop starts running short of water.
- **After harvest, the farmer logs the season.** The season is kept: what was planted and what the land showed.

An AI assistant talks with the farmer in plain Portuguese. It never creates a number: every figure comes from the calculation and is checked before it is shown. The decision stays with the farmer and their agronomist.

This project uses public NASA data. It is not a NASA product and is not endorsed by NASA.

## 2. The story: mission control for the field

NASA doesn't fly without a rehearsal, without mission control, or without a mission report. Farmers plant with none of the three. Órbita Rural brings all three to the field.

| the moment | in a mission | in the field | in the app |
|---|---|---|---|
| before planting | the rehearsal | the farmer's rotation and two others, against ten seasons of real weather | the **Ensaiar** (Rehearse) tab |
| during the season | mission control | the farmer's field, today, on screen, with the water-stress alert | the **Hoje** (Today) tab, "My field today" |
| after harvest | the mission report | the season's log, which becomes a record from one year to the next | the **Registrar** (Log) tab |

Mission control is the heart of the project. In Rio Verde, in the 2016 season, the calculation shows the maize's water stress starting on April 4 and the water running out on April 24. That is 20 days between one and the other: the time the water-stress alert puts in the farmer's hands.

**The pain we started from.** Planning the season under a changing climate, water shortage at the crop's critical stage, extreme heat and soil losing organic matter are all in the "Dores do Agro 2026" assessment by IFAG: pain points listed by field technicians and validated by 80 farmers in Goiás, Brazil.

## 3. How the farmer uses it, in 5 steps

1. **Tell the app about the field.** On first open, the assistant asks where the field is, what the farmer plants, when the soybeans go in and what the soil is like. Every question has buttons; those who prefer can type. At the end the farmer checks the summary and confirms.
2. **The field is saved on the device.** Next time, the app opens straight on "My field today".
3. **Today.** The farmer sees how the field is doing: the status (calm, attention or alert), the water-stress alert and the other five indicators, each with the date of its data. "Entender" (Understand) opens the full explanation.
4. **Rehearse.** Before planting, the farmer sees the answer in one sentence, the 3 paths side by side on 3 measures (water shortfall, strong heat at the critical stage, days in a row with no living plants on the soil) and one line of risk per path. "Ver a prova" (See the proof) opens the sources; "Ver um ano ruim" (See a bad year) plays the city's bad season day by day.
5. **Log and ask.** After harvest, the farmer sees the season's log and can note how much was harvested. The "Perguntar" (Ask) button, on any screen, opens the assistant, which already knows the field and says where each answer came from: the calculation, NASA data for the place, or general knowledge.

## 4. "My field today": a real example

Rio Verde (Goiás), soybeans planted on October 15, 2026, medium soil. The query was run on 2026-11-15 (`python3 -m orbita.perguntar --lavoura-hoje`); each row carries the date of its data.

| indicator | what the screen showed | date of the data |
|---|---|---|
| the field today | **attention**: the soybeans were 30 days old, growing, with no water stress; heat and the water-stress alert call for attention | Nov 14, 2026 |
| water-stress alert | if it doesn't rain, the soybeans start running short of water in 7 days, on Nov 21, 2026 (over the last 7 days the crop drank 4.1 mm a day on average) | Nov 14, 2026 |
| water | 66.0 mm within reach of the plant, 100% of what the soil holds; on the same day of the normal year (2019-20 season) there were 58.4 mm, and in the worst year (2015-16 season), 63.4 mm | Nov 14, 2026 |
| crop stage | 30 days after planting, growing; the critical stage (flowering and grain filling) starts on Nov 24, 2026 | Nov 14, 2026 |
| heat | 2 days of strong heat since planting (daily maximum above 40 °C, the limit for soybeans); across the 10 stored seasons, up to the same day of the cycle, the middle value was 0 (from 0 to 6); the highest maximum was 40.7 °C, on Nov 7, 2026 | Nov 12, 2026 |
| greenness from orbit | 0.41, on a scale from 0 to 1, within the normal range for the time of year (middle value of the other years: 0.38; from 0.26 to 0.46) | image of Oct 16, 2026 (a 16-day composite) |
| soil cover | living plants for 31 days in a row; before that, 122 days in a row with no living plants | Nov 14, 2026 |

Every answer ends with "Converse com o agrônomo antes de decidir." (Talk to your agronomist before deciding.) The water-stress alert is not a weather forecast: it is the water balance carried forward with no rain at all; any rain that falls changes the result.

**And the rehearsal, in the same place.** A farmer in Rio Verde planted his soybeans on November 10 and asks: maize or sorghum? (`python3 -m orbita.perguntar --cidade rio_verde --rotacao soja,milho --plantio 2026-11-10`)

| in the worst year (2015-16 season) | soybeans and maize | soybeans and maize with cover grass | soybeans and sorghum |
|---|---|---|---|
| water shortfall (mm) | 252.7 | 252.7 to 263.5 | **220.3** |
| days of strong heat at the critical stage | 9 | 9 | **0** |
| days in a row with no living plants on the soil | 122 | **30** | 122 |

## 5. How the project answers the challenge

The challenge asks for a decision-support tool that brings together NASA Earth observations, local soil data, crop characteristics and farmer priorities, so farmers can explore crop rotations, without replacing their judgment or local agricultural knowledge.

| what the challenge asks for | how Órbita Rural answers |
|---|---|
| NASA data | satellite rainfall (GPM IMERG), temperature (NASA POWER) and field greenness (MODIS), three of the datasets the challenge names |
| local soil data | the soil type in the farmer's profile (sandy, medium, clay) becomes the water the soil can hold, using the values of ZARC, Brazil's agricultural climate-risk zoning |
| crop characteristics | the calendar, water demand and heat limit of soybeans, maize, sorghum and brachiaria grass, each value with its source and the label "published" or "hypothesis" |
| farmer priorities | the calculation runs on the farmer's own field (place, rotation, planting date, soil); what worries them most (water, heat or soil) changes the order and the emphasis, never the numbers |
| compare at least 3 rotations, including the current one | every rehearsal shows 3 paths: soybeans, maize and fallow; soybeans and maize with brachiaria; soybeans and sorghum |
| evidence, benefit, risk and gap for each one | four sentences per rotation, built only from numbers in the calculation; on screen, one line of risk per path and the rest under "See the proof" |
| compare satellite data with ground measurements | satellite rainfall against 27 INMET weather stations in Goiás and the Federal District (section 7) |
| flag bare soil and crop stress | days with no living plants (from the calendar and from the satellite), days of water stress, days of strong heat, and the water-stress alert |
| communicate uncertainty | the rotation with cover grass is given as a range; every indicator on the panel carries the date of its data; values that are hypotheses are labelled |
| understandable to non-experts; human judgment | farm words ("water shortfall", "days of thirst", "soil with no living plants"), buttons instead of a form, "Understand" on every card and a technical view for the agronomist in the footer; every answer ends with "Talk to your agronomist before deciding." |

## 6. NASA data behind each indicator

| indicator | NASA data | what else goes in |
|---|---|---|
| water in the soil and the water-stress alert | GPM IMERG satellite rainfall (the ten-season series and each day's rain up to yesterday) and NASA POWER temperature, which gives the crop's water demand | the FAO-56 water balance |
| heat | each day's maximum temperature, from NASA POWER | each crop's limit, from published sources (Embrapa and FAO) |
| greenness from orbit | MODIS NDVI (MOD13Q1 product, 250 m, one image every 16 days) | 6 cropland points per city |
| soil cover | MODIS greenness checks the calendar | the rotation's calendar |
| crop stage | (comes from the calendar) | the rotation's calendar and the FAO stage tables |
| water shortfall in the rehearsal and the log | GPM IMERG rainfall and NASA POWER temperature, day by day, over 10 seasons | the FAO-56 water balance |

The address of each query, the period, the licence and where each dataset is stored: [DADOS-E-FONTES.md](DADOS-E-FONTES.md) (in Portuguese).

## 7. The proof: we tested it across Goiás

- **20 of 20 municipalities.** In the 20 municipalities of Goiás that plant the most second-crop maize, over ten seasons, where the calculation showed more water shortfall the harvest recorded by IBGE (Brazil's statistics office) was lower. In all 20. For the region as a whole, year by year, the relationship between the two is −0.72 (on a scale where 0 means no relationship and −1 means the harvest falls every time the water shortfall rises).
- **21 of 27 weather stations.** Satellite rainfall came closer to the rain measured on the ground than model-based rainfall at 21 of 27 stations of INMET, Brazil's national weather service: 16 of 22 in Goiás and 5 of 5 in the Federal District.

The method, the numbers for each municipality and each station, and how to rerun both tests: [VALIDACAO.md](VALIDACAO.md) and the [validacao-regional/](validacao-regional/) folder (in Portuguese).

## 8. How to run it

All you need is Python 3 (standard library). The commands below were run on 2026-11-15 and worked.

**The tests**, from inside `backend/`:

    python3 -m unittest

More than 500 automated tests, no failures, in about a minute.

**The panel, the rehearsal, the bad year and the log**, from inside `backend/`:

    python3 -m orbita.perguntar --lavoura-hoje                                               # "My field today" (Rio Verde)
    python3 -m orbita.perguntar --cidade rio_verde --rotacao soja,milho --plantio 2026-11-10 # the 3-rotation rehearsal
    python3 -m orbita.perguntar --replay 2015-16                                             # the bad year, day by day
    python3 -m orbita.perguntar --registro 2015-16                                           # the season's log
    python3 -m orbita.validar                                                                # the Rio Verde checks

The cities: `rio_verde`, `jatai`, `silvania`. With `--json`, each command returns the full structure.

**The API** (the door the screen uses to ask), from inside `backend/`:

    python3 -m orbita.api                              # starts on http://127.0.0.1:8000 (this machine only)
    curl -s http://127.0.0.1:8000/saude                # lists the routes and says whether the AI is on
    curl -s -X POST http://127.0.0.1:8000/lavoura-hoje -H 'Content-Type: application/json' \
      -d '{"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media", "plantio_da_soja": "2026-10-15"}'

The screen uses four calculation routes, which answer with no key at all: `POST /lavoura-hoje` (the panel), `POST /recomendacao` (the rehearsal), `POST /replay` (the bad year) and `POST /registro` (the season's log). Free-form questions go to the assistant, on `POST /agente`, which needs the OpenRouter key in the terminal environment, never in a file: `export OPENROUTER_API_KEY=...` before starting the API. All routes, with examples: `backend/orbita/API.md`.

**The screen** (as described in `frontend/orbita/LEIA-ME.md`): with the API running, open `frontend/orbita/index.html?api=http://127.0.0.1:8000`. Without the API, double-click `frontend/orbita/index.html`: the app opens with the stored numbers and says what day they are from.

**Each day's rain** is downloaded by `data/orbita/chuva-do-dia/baixar_chuva_do_dia.py` (the commands are in that folder's LEIA-ME).

## 9. The parts and where each one lives

| the part | what it is | where it is |
|---|---|---|
| the engine | the program that does the calculation (no AI, no key, no internet at question time) | `backend/orbita/` (`README.md`, `LEIA-ME-motor.md`, `API.md`) |
| the assistant | the AI that talks with the farmer, with the guardrails that check the numbers | `backend/orbita/` (`LEIA-ME-agente.md`) |
| the screen | the farmer's app: onboarding through the assistant and the Today, Rehearse and Log tabs | `frontend/orbita/` (`LEIA-ME.md`) |
| the data | everything that was downloaded, with the address and time of each query | `data/orbita/` |
| the documents | this file, the AI-use statement, data and sources, the validation, the Goiás tests and the farmer questionnaire | `docs/orbita/` |
| the pitch | the 7 slides in Portuguese and in English, the spoken script, the project-page text and the 30-second video | `docs/orbita/pitch/` (`LEIA-ME.md`) |

Órbita Rural's work lives in these four folders. The rest of the repository belongs to the other team members.

## 10. Use of AI

Declared in [AI-USE.en.md](AI-USE.en.md) (in Portuguese: [USO-DE-IA.md](USO-DE-IA.md)).

## 11. Credits

- **The team:** Equipe Agronautas, NASA Space Apps Challenge 2026.
- **Members:** to be filled in.
- **The visual base of the screen:** the first version started from the dashboard on the team's `nat` branch, as recorded in `frontend/orbita/LEIA-ME.md`. The logo and visual identity belong to the team.
- **The typefaces:** Anton and Montserrat, under the SIL Open Font License 1.1 (`frontend/orbita/fontes/OFL-Anton.txt` and `OFL-Montserrat.txt`).
- **The data:** NASA (GPM IMERG, NASA POWER, MODIS), INMET, IBGE, FAO, Embrapa, ZARC, CHIRPS and ERA5. Each day's rain comes from the open copy of IMERG kept by dynamical.org ("NASA IMERG from dynamical.org", CC BY 4.0). The full list is in [DADOS-E-FONTES.md](DADOS-E-FONTES.md).
- There is no NASA logo in this project.

## 12. License

To be defined by the team. On 2026-11-15 there was no license file in the repository.

## 13. The scope of this version

- The app has stored data for three cities in Goiás (Rio Verde, Jataí and Silvânia) and three rotations, all starting with soybeans.
- The data is for the region (the city's point), not for the individual plot.
- The tool supports the decision and does not replace the agronomist.
- When the assistant answers from general knowledge (pests, fertiliser, markets), it says so.
