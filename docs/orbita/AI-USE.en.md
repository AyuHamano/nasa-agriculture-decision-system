<!-- Generated with AI (Claude) -->
# Órbita Rural · statement on the use of AI

Versão em português: [USO-DE-IA.md](USO-DE-IA.md)

The NASA Space Apps Challenge asks teams to declare their use of artificial intelligence. This is the statement of team Equipe Agronautas for Órbita Rural. This file was also written with AI.

## 1. In development

| what | how AI was involved |
|---|---|
| the code of the engine, the assistant and the screen (`backend/orbita/`, `frontend/orbita/`) and the tests | generated with AI (Claude, by Anthropic) at the team's request, with the team's decisions and review. Code files carry the header "Gerado com IA (Claude)" |
| the programs that download the data (`data/orbita/`) and those of the Goiás tests (`docs/orbita/validacao-regional/`) | generated with AI (Claude). The data itself is not AI-made: it is a copy of what each source returned, with the address and time of the query |
| the texts (the READMEs, these documents, the questionnaire, the spoken script, the project-page text) | written with AI (Claude) and checked by the team |
| the pitch slides (`docs/orbita/pitch/`) | made with AI support. There are no AI-generated images: the satellite picture on the slides is a real NASA image |
| the voice in the video | AI-generated |
| code review | a second model (GPT) reviewed the engine and assistant code at marked points; the defects it found were fixed, each with a test (recorded in `README.md`, `LEIA-ME-motor.md` and `LEIA-ME-agente.md` under `backend/orbita/`) |

**Models used in development:** Claude, by Anthropic, for coding and writing; occasional reviews by a second model (GPT).

What is not AI: the data (NASA, INMET, IBGE), the published crop values (FAO, Embrapa, ZARC) and the project's decisions.

## 2. In the product

The assistant (the AI that talks with the farmer) uses a language model called through OpenRouter:

- default: `anthropic/claude-haiku-5.5` (Claude Haiku 5.5, by Anthropic);
- tested fallback: `deepseek/deepseek-v4.1-flash` (DeepSeek V4.1 Flash).

The key lives only in the terminal environment (`OPENROUTER_API_KEY`); no file in the repository holds a key.

**The AI stays in the conversation.** The "My field today" panel, the rotation rehearsal, the bad year day by day and the season's log are calculations by the engine: they use no AI and work without a key. The explanation the engine writes is made of pre-written sentences filled in with the numbers from the calculation. At onboarding, the buttons build the field profile without AI; the AI comes in when the farmer types and when they tap "Perguntar" (Ask).

## 3. The product's guardrails

The AI does four things: it understands what the farmer says, proposes the values for the profile, chooses which tool to consult (the rotation rehearsal, the field-today panel, the climate of the place, the greenness from orbit) and writes the explanation. Everything else is guaranteed by the program, with tests:

- **The AI never creates a number.** Every number in its text is checked against the calculation (the profile, the comparison and what the tools returned in that turn). If a number is left over, the AI tries once more; if one is left over again, its text does not reach the screen and the engine's pre-written sentences are shown instead.
- **The assistant always gives a pointer, and says what is calculation and what is general knowledge.** Every answer backed by the calculation ends with "A indicação:" (the pointer). When the farmer mentions a place or a rotation that is not stored, the calculation runs with the nearest stored city and the most similar stored rotation, the profile shows both choices for the farmer to confirm, and the answer says which place the weather is from and which rotation was used. Whatever falls outside the calculation is marked as general knowledge; if the AI doesn't say so, the program adds the sentence.
- **What has no calculation is stated as general knowledge.** Nutrients, pests and markets are not measured. The answer comes with a notice up front and with no numbers.
- **The answer sends the farmer to the agronomist.** Every answer carries the notice "Converse com o agrônomo antes de decidir." (Talk to your agronomist before deciding.) The AI does not choose the rotation for the farmer.
- **The calculation only runs after the farmer says "yes"** to the profile, and it is the program, not the AI, that reads the "yes".
- **Every answer with a confirmed profile shows 3 or more rotations**, including the current one, each with its evidence, benefit, risk and what is still unknown.
- **Every answer says where it came from:** `texto_de` (AI or pre-written sentences) and `apoio` (the calculation, data for the place, or general knowledge).
- **Two known mix-ups are blocked:** days of soil cover stated in place of days with no living plants, and "the water ran out" said of the day the water stress only began. Text with characters from another alphabet does not reach the screen either.
- **No personal data is requested** (name, phone, ID number, address), and the API stores nothing. The field is saved only on the farmer's own device.

Where this is written and tested: `backend/orbita/LEIA-ME-agente.md` (the table "O que a IA faz e o que o programa garante") and the tests `backend/orbita/tests/test_agente.py`, `test_ficha.py`, `test_ferramentas.py`, `test_fala_simples.py` and `test_modelo.py`.

## 4. How the conversations were checked

The automatic check looks at whether each number in the text exists in the calculation. The meaning of each sentence is checked by reading: the 6 stored example conversations (recorded on 2026-11-15, with 16 assistant turns, 10 with AI text and 6 with pre-written sentences, none blocked by the number check) were read one by one against the calculation before being stored. Choosing the nearest city and the most similar rotation is done by the AI (if it doesn't choose a rotation, the program picks the one with the most crops in common), which is why the profile shows both to the farmer before the calculation runs.

## 5. The contest rules we follow

- We do not use the NASA logo and do not say that NASA endorses the project. We use public NASA data.
- No name, image or voice of anyone under 18 appears in the project.
- The submission material is in English; the main documents are available in Portuguese and in English.
