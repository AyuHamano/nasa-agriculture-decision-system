<!-- Generated with AI (Claude) -->
# Órbita Rural · the whole project, for newcomers

Versão em português: [LEIA-ME.md](LEIA-ME.md)

## 1. What it is, in 5 lines

- Órbita Rural is the tool built by team **Equipe Agronautas** for the NASA Space Apps Challenge 2026, challenge "Field Shift: Adapting Farms with NASA Data".
- The farmer says where they plant and what they plant. The system runs the calculation with what NASA satellites recorded at that place and puts the farmer's crop rotation next to two others.
- It looks at three things: the water the crop lacked, the days of strong heat, and the days the soil had no living plant.
- An AI talks with the farmer in plain Portuguese. It does not create numbers: every number comes from the calculation and is checked before it is shown.
- The tool supports the decision. It does not replace the agronomist, does not promise profit and does not promise a bigger harvest.

This project uses public NASA data. It is not a NASA product and is not endorsed by NASA.

## 2. The story

"Órbita Rural follows the farm all year round with NASA data: it rehearses before planting, follows the crop during the season and keeps the record afterwards. And every number comes with proof."

| the moment | the farmer's question | what the tool does |
|---|---|---|
| before planting | "What do I plant now?" | compares 3 rotations (the farmer's and two others) in a normal year and in the region's worst year |
| during the season | "How is my crop doing?" | shows the water in the soil on the last day with data, next to the same day of the normal year and of the worst year |
| after harvest | "What did the soil show?" | keeps the record of the season: what was planted, the water, the heat and the days with no living plant |

The worst year (the 2015-16 season in Rio Verde, Goiás, Brazil) is the proof that the calculation works. It is not the product.

**The pain we started from.** Planning the season under an unstable climate, water shortage in the crop's critical phase, extreme heat and soil losing organic matter appear in the assessment "Dores do Agro 2026" by IFAG (pains listed by technicians and validated by 80 farmers in Goiás). Public citation of that document still awaits confirmation by the team.

## 3. The challenge and how the project answers it

The challenge asks for a decision-support tool that brings together NASA Earth observations, local soil data, crop characteristics and farmer priorities, so the farmer can explore crop rotations. It supports and does not replace farmer judgment or local agricultural expertise.

| what the challenge asks for | how Órbita Rural answers |
|---|---|
| NASA data | three of the datasets the challenge names: satellite rainfall (GPM IMERG), temperature (NASA POWER) and crop greenness (MODIS) |
| local soil data | the soil type from the farm form (sandy, medium texture, clay) becomes the water the soil holds, using the values of ZARC (the Brazilian agricultural climate-risk zoning) |
| crop characteristics | the calendar, water demand and heat limit of soybean, maize, sorghum and brachiaria grass, each value with its source and the label "published" or "hypothesis" |
| farmer priorities | in the conversation the farmer says what worries them most (water, heat or soil); this changes the order and the emphasis, never the numbers |
| compare at least 3 rotations, including the current one | every answer with a confirmed form brings 3 rotations: soybean, maize and fallow; soybean, maize with brachiaria; soybean and sorghum |
| evidence, benefit, risk and information gap for each | four sentences per rotation, built only with numbers from the calculation |
| compare satellite with ground measurements | satellite rainfall against the INMET weather station in Rio Verde (section 7) |
| flag bare-soil periods and crop stress | the days with no living plant (by the calendar and by the satellite), the days of water stress and the days of strong heat |
| communicate uncertainty | the rotation with grass is given as a range; today's soil water is given as a range; 30 values of the calculation are labeled as hypotheses |
| explain technical terms | answers use farm words ("water shortage", "days of thirst", "no green plant") and say what each one means; the "Agrônomo" tab of the screen shows how the calculation was made |
| understandable by non-experts; human judgment | conversation in plain Portuguese; every answer ends with "Talk to your agronomist before deciding." |

What the challenge mentions and the calculation does not measure: nutrients, pests and markets. On these the agent answers as general knowledge, with a notice, and with no numbers.

## 4. The three legs

| the leg | what it measures | what data feeds it |
|---|---|---|
| water | the water shortage day by day, per season (what the plant asked for minus what it managed to drink) | satellite rainfall from NASA's GPM IMERG; temperature from NASA POWER; the method of the FAO-56 manual |
| heat | the days of strong heat in the critical phase of each crop | maximum temperature from NASA POWER; each crop's limit from a published source (Embrapa and FAO) |
| covered soil | the consecutive days with no living plant | the crop calendar and the greenness seen by the MODIS satellite (NDVI, an index of leaf greenness) |

Addresses, periods and where each dataset is stored: [DADOS-E-FONTES.md](DADOS-E-FONTES.md) (in Portuguese).

## 5. The pieces and where each one lives

| the piece | what it is | where it is |
|---|---|---|
| the engine | the program that runs the calculation (no AI, no key, no internet at question time) | `backend/orbita/` (start with `README.md` and `LEIA-ME-motor.md`) |
| the agent | the AI that talks with the farmer, with the safeguards that check the numbers | `backend/orbita/` (`LEIA-ME-agente.md`; the web API is described in `API.md`) |
| the screen | what the farmer sees: the conversation, the form, the rotations side by side and the replay of the bad season | `frontend/orbita/` (`LEIA-ME.md`) |
| the data | everything that was downloaded, with the address and time of each query | `data/orbita/` |
| the documents | this file, the AI use statement, data and sources, validation and the questionnaire | `docs/orbita/` |

The Órbita Rural work lives only in these four folders. The rest of the repository belongs to the other team members and was not changed.

## 6. How to run

Only Python 3 is needed (standard library). The commands below were run on 2026-11-15 on a copy of branch `jose` (commit `fe578c6`), and all of them worked, except where noted.

**The tests**, from inside `backend/`:

    python3 -m unittest

Result on that copy: 440 tests, no failures, in about 40 seconds.

**A question to the engine**, from inside `backend/` (the output is in Portuguese):

    python3 -m orbita.perguntar --cidade jatai --rotacao soja,sorgo --plantio 2026-11-20   # the 3 rotations compared
    python3 -m orbita.perguntar --cidade jatai --verde                                     # what the satellite saw of the soil
    python3 -m orbita.perguntar --hoje                                                     # how the soil water is today (Rio Verde)
    python3 -m orbita.perguntar --replay 2015-16                                           # the bad season, day by day
    python3 -m orbita.perguntar --registro 2015-16                                         # the record of the season
    python3 -m orbita.validar                                                              # the proofs of section 7

The cities: `rio_verde`, `jatai`, `silvania`. With `--json`, each command returns the full structure.

**The API**, from inside `backend/`:

    python3 -m orbita.api                              # starts at http://127.0.0.1:8000 (this machine only)
    curl -s http://127.0.0.1:8000/saude                # lists the routes and says whether the AI is on

Without an AI key the API starts all the same; only the route `POST /agente` answers 503 (checked). For the live agent, the OpenRouter key goes only in the terminal environment, never in a file: `export OPENROUTER_API_KEY=...` before starting the API. **Not checked here:** the live conversation with the AI, because this check was done without a key. `LEIA-ME-agente.md` records the real use done on 2026-11-15.

**The screen with the saved answers:** double-click `frontend/orbita/index.html`. No server or internet needed.

**The live screen:** start the API (above, with the key) and open `frontend/orbita/index.html?api=http://127.0.0.1:8000`. If the API does not answer, the screen says so and goes back to the saved conversations. **Not checked here:** opening the screen in a browser; both modes are described and checked in the screen's `LEIA-ME.md`.

**Regenerating what the screen reads** (after changing the engine or the agent):

    python3 -m orbita.exportar_conversas ../frontend/orbita/dados --sem-ia    # from inside backend/; no key, ready-made sentences
    python3 -B frontend/orbita/dados/gerar-dados.py                           # from the repository root

Both were run in a test folder and worked (4 conversations, 13 agent turns). The first one replaces the saved conversations written by the AI with ready-made sentences: run it without `--sem-ia`, with the key, to keep the AI text.

## 7. The proofs

The numbers below come from `python3 -m orbita.validar` and from the files in `data/orbita/validacao/`. Details: [VALIDACAO.md](VALIDACAO.md) (in Portuguese).

**The satellite against the ground station** (INMET station A025, 4.79 km from the Rio Verde point; February to June window; 8 seasons compared):

| rainfall source | mean error against the station |
|---|---|
| GPM IMERG (NASA's satellite, the engine's default) | 12.1% |
| CHIRPS | 17.6% |
| ERA5 | 26.7% |
| NASA POWER (model rainfall) | 33.2% |

NASA POWER model rainfall gave, on average, 86% of the station's rainfall in the 4 seasons compared up to 2020, and 51% in the 4 from 2021 on. In the year 2025: 678.4 mm in the model against 1,548.0 mm in the rain gauge. That is why the engine uses satellite rainfall.

**The calculation against the IBGE harvest** (second-season maize in Rio Verde, IBGE Municipal Agricultural Production survey, 10 seasons, medium soil):

- The 2 seasons with the largest maize water shortage in the calculation (2021-22, with 54.8% of demand, and 2015-16, with 49.6%) are the 2 worst harvests in IBGE (5,100 and 3,300 kg/ha). The median of the 10 seasons is 6,725 kg/ha.
- The third largest shortage is 2020-21 (45.9%), which was not a bad harvest in Rio Verde (7,200 kg/ha).
- The rank correlation between water shortage and yield is -0.52. These are only 10 seasons: it is a sign, not proof.

**Satellite greenness against the calendar.** The calendar gives 122 consecutive days with no living plant in the rotation with fallow. The satellite saw, at the median, 96 consecutive days with no green plant in Rio Verde (36 measurements, from 16 to 160 days), 80 in Jataí (30 measurements, from 0 to 128) and 96 in Silvânia (35 measurements, from 16 to 192). The calendar number fits inside the satellite range in all three cities.

**The bad season, day by day** (Rio Verde, 2015-16, by the calculation): maize goes in on February 10, 2016; water stress starts on April 4 and lasts 60 consecutive days; on April 24 the water the plant can reach drops to 0.1 mm; 220.6 mm were missing, 49.6% of what the maize asked for. The 0.1 mm value comes from the calculation, fed by satellite rainfall. Nobody measured the soil.

## 8. The limits, stated plainly

- **No test on a real farm.** The calculation uses the climate of the city point, not of the farm. No farmer has used the tool through a season, and the validation questionnaire has no answers yet.
- **What holds only for Rio Verde:** the comparison with the ground station (the only checked station is there) and the match with the 2 worst harvests. In Jataí the "strong thirst" level flags all 10 seasons and only one was a bad harvest in IBGE; in Silvânia no season fell below the cut, and the level comes out empty. Jataí's worst year by harvest had less water shortage in the calculation than the normal year, and the answer says so.
- **The satellite's "12%" error holds for the long series** (8 seasons, February to June). It does not hold for recent rainfall.
- **Recent rainfall comes as a wide range.** The fast path (2 days of delay) reads rainfall from the color of a NASA image. Over 50 days of September and October 2026, against the Rio Verde station, the satellite gave 32% to 38% more and the model rainfall 45% less. So "how it is today" shows the calculation with both rainfalls and the range between them.
- **The satellite greenness points were chosen on the map.** We do not know whose they are or what was planted, and nobody checked them in the field. The years 2024 and 2025 were left out (images are missing in the service we queried). The satellite measures leaf greenness and does not see crop residue (straw).
- **What is a hypothesis:** 30 values of the calculation, listed in the engine's answer. Among them: how much the grass competes with the maize for water (hence the range), the residue cover, the sorghum's mid-season water demand, the sorghum root depth, the critical phase of each crop and the use of the day's maximum temperature for heat.
- **A day of strong heat is not a crop loss, and water shortage is not a crop failure.** The calculation does not measure income, price, cost or yield. The temperature is that of a square of about 50 km.
- **The AI.** The check looks at whether each number in the text exists in the calculation. It does not check what the number refers to. That is why the saved conversations were read one by one.
- The screen is in Portuguese only. The API has no password and should only run on the local machine.

## 9. Next steps

- Take the questionnaire to farmers and publish the count of answers.
- Test with farmers and agronomists through a real season, and check the satellite greenness points in the field.
- Exact recent rainfall for each day, in mm, from NASA's GES DISC (needs a free Earthdata account).
- Compare with more ground stations, also in Jataí and Silvânia.
- Phases, cycle and root depth of second-season sorghum measured in Goiás.
- The screen in English, the cooperative dashboard (following several farmers) and the conversation over WhatsApp.

## 10. AI use

Declared in [AI-USE.en.md](AI-USE.en.md) (in Portuguese: [USO-DE-IA.md](USO-DE-IA.md)).

## 11. Credits

- **The team:** Equipe Agronautas, NASA Space Apps Challenge 2026.
- **Members:** to be filled in.
- **The visual base of the screen:** the first version started from the dashboard on the team's `nat` branch, as recorded in `frontend/orbita/LEIA-ME.md`. The logo and visual identity belong to the team.
- **The typefaces:** Anton and Montserrat, under the SIL Open Font License 1.1 (`frontend/orbita/fontes/OFL-Anton.txt` and `OFL-Montserrat.txt`).
- **The data:** NASA (GPM IMERG, NASA POWER, MODIS), INMET, IBGE, FAO, Embrapa, ZARC, CHIRPS and ERA5. Full list in [DADOS-E-FONTES.md](DADOS-E-FONTES.md).
- There is no NASA logo in this project.

## 12. License

To be defined by the team. On 2026-11-15 there was no license file on any branch of the repository.
