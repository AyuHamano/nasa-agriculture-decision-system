# Órbita Rural · project page text (NASA Space Apps Challenge 2026)

> Generated with AI (Claude) on 2026-11-15, at the team's request. Text for the project page, in English. Every number is
> traced to its source in `../VALIDACAO.md` and in the engine's own output (`backend/orbita/`). Anything marked `[a preencher]` is still to be filled in by
> the team. Delete this note before pasting.

---

## Project name
Órbita Rural

## Tagline
Space intelligence. Decisions for the land.

## Challenge
Field Shift: Adapting Farms with NASA Data

## High-level summary
For ten thousand years, farmers have looked to the sky to decide what to plant. Now the sky looks back.

NASA doesn't fly without a rehearsal, without mission control, or without a mission report. Farmers plant with none of
the three. **Órbita Rural brings all three to the field**, built on open NASA Earth observations:

- **Before planting, the rehearsal.** The farmer's crop rotation and two alternatives are run against ten seasons of real
  weather, day by day, and shown side by side.
- **During the season, mission control.** One screen shows the field today: crop stage, water in the soil, heat,
  greenness seen from orbit, soil cover, and an alert that says in how many days the crop will run short of water if it
  doesn't rain.
- **After harvest, the mission report.** The season's log: what was planted and what the land showed.

The farmer talks to an AI assistant, but the AI never creates a number: every figure comes from an open, tested water
balance and is checked before it reaches the screen. The choice stays with the farmer and their agronomist.

## The problem
Farmers choose their crop rotation in the dark: they don't know how it holds up in a bad year, or what it does to their
soil. In Goiás, Brazil, 80 farmers validated the farming pain points listed in an assessment by the IFAG institute
(Dores do Agro 2026). For grain growers, number one is planning under a shifting climate and economy. Rated high in
severity: water stress at critical crop stages (4.5), losses from extreme heat (4.0) and soil losing organic matter (4.5).

No NASA mission launches without a rehearsal. Every crop season does.

## What it does

### The rehearsal: "Maize or sorghum?"
A farmer in Rio Verde, Goiás, planted his soybeans late, on November 10. The second crop will go in on March 8. He asks:
maize or sorghum? Órbita Rural runs the three paths against ten real seasons and answers with numbers:

| in the bad year (2015-16) | maize | maize + cover grass | sorghum |
|---|---|---|---|
| water shortfall (mm) | 252.7 | 252.7 to 263.5 | **220.3** |
| days of strong heat at the critical stage | 9 | 9 | **0** |
| days in a row with no living plants on the soil | 122 | **30** | 122 |

He chooses with his eyes open.

### Mission control: "My field today"
During the season, the farmer opens the app and sees the field today. On November 15, 2026, for a soybean field planted
on October 15 in Rio Verde, the screen read (latest data: November 14):

- **Water-stress alert:** if it doesn't rain, the crop runs short of water in 7 days.
- **Water in the soil:** 66.0 mm, no stress (58.4 mm on the same day of the normal year; 63.4 mm in the worst year).
- **Crop stage:** day 30, growing; the critical stage starts on November 24.
- **Heat:** 2 days above 40 °C since planting (the usual count by this point of the season is 0).
- **Greenness seen from orbit:** 0.41 in the latest satellite composite, within the normal range for this time of year (0.38).
- **Soil cover:** 31 days with living plants, after 122 days without.

Why it matters: Rio Verde, the 2016 season. In our water balance, the maize's water stress began on April 4. On April 24,
the water ran out. The farmer didn't know. The satellite did. Mission control would have sent the warning twenty days
earlier. That season ended as the lowest second-crop maize yield in Rio Verde's official records for the ten seasons we
studied (3,300 kg/ha, against a median of 6,725).

### The mission report
After harvest, the app logs the season: what was planted, next to what the land showed (water shortfall, days of strong
heat, days with no living plants).

## How we use NASA data
- **GPM IMERG** (rainfall estimated from satellites), daily: the rain that drives the water balance, both in the
  ten-season rehearsal and in today's view (for the most recent days, the quick-look IMERG runs).
- **NASA POWER** (daily API): maximum and minimum temperature, for crop water demand and for the count of strong-heat days.
- **MODIS MOD13Q1** (NDVI, 250 m, 16-day composites): the greenness of the fields, seen from orbit.
- **NASA GIBS / Worldview** (MODIS on Terra, true color): the satellite image of Rio Verde on April 24, 2016, shown on
  our cover slide. It is the day the water ran out.

The water balance follows **FAO Irrigation and Drainage Paper 56** (reference evapotranspiration, crop coefficients and a
daily root-zone water balance). Crop calendars come from Brazil's agricultural climate-risk zoning.

## The proof: we tested it across Goiás
- **20 of 20 municipalities.** In the twenty municipalities of Goiás that plant the most second-crop maize, over ten
  seasons, the math moved with the official harvest records (IBGE): the more water shortfall in the math, the lower the
  yield, in all twenty.
- **21 of 27 weather stations.** Against the rain gauges of INMET, Brazil's national weather service, satellite rainfall
  came closer to the rain measured on the ground than model-based rainfall at 21 of 27 stations: 16 of 22 in Goiás and
  5 of 5 in the Federal District.

Here, every number comes with proof: the code and the data are public in the repository.

## Use of artificial intelligence
- **In the product.** A large language model (Claude Haiku 5.5, by Anthropic, called through OpenRouter) holds the
  conversation with the farmer and explains the results. It does not calculate or choose anything: the numbers come from
  the deterministic engine, and a checker compares every number in the AI's text against the engine's output. If a number
  is not in the engine's output, the AI text is discarded and pre-written sentences are shown instead.
- **In development.** The code, tests, documentation, slides and this text were generated with AI (Claude, by Anthropic)
  at the team's request and cross-reviewed by a second AI (GPT). Source files carry the header "Gerado com IA (Claude)".
  The idea, the direction and every decision are the team's.
- **In the media.** No AI-generated images. The satellite picture on the slides is a real NASA image. The 30-second video
  is narrated by an AI-generated voice, marked on screen.

## Who it is for
Free for the farmer. The cooperative pays, per farmer supported. And NASA data becomes a decision in the hands of those
who plant.

Órbita Rural uses public NASA data. It is not a NASA product and is not endorsed by NASA.

## Links
- Repository: [a preencher]
- Demo (30-second video or 7 slides): [a preencher]
- Live app: [a preencher]
- Team: Equipe Agronautas: [a preencher]

## References
- NASA GPM IMERG: https://gpm.nasa.gov/data/imerg · NASA POWER: https://power.larc.nasa.gov/ · MODIS MOD13Q1: https://lpdaac.usgs.gov/products/mod13q1v061/
- NASA GIBS / Worldview: https://worldview.earthdata.nasa.gov/
- FAO Irrigation and Drainage Paper 56: https://www.fao.org/4/X0490E/x0490e00.htm
- IBGE, Municipal Agricultural Production (SIDRA): https://sidra.ibge.gov.br/ · INMET historical data: https://portal.inmet.gov.br/dadoshistoricos
- IFAG, Dores do Agro 2026 (presentation).
