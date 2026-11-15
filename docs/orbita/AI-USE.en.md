<!-- Generated with AI (Claude) -->
# Órbita Rural · AI use statement

Versão em português: [USO-DE-IA.md](USO-DE-IA.md)

The NASA Space Apps Challenge asks teams to declare their use of artificial intelligence. This is the statement of team Equipe Agronautas for Órbita Rural. This file was also written with AI.

## 1. In development

| what | how AI was used |
|---|---|
| the code of the engine, the agent and the screen (`backend/orbita/`, `frontend/orbita/`) and the tests | generated with AI (Claude, by Anthropic) at the team's request, with the team's decisions and checks. Each code file carries the header "Gerado com IA (Claude)" ("Generated with AI") |
| the programs that download the data (`data/orbita/`) | generated with AI (Claude). The data itself is not AI output: it is a copy of what each source returned, stored with the query address and time |
| the texts (the READMEs, these documents, the questionnaire, the submission text) | written with AI (Claude) and checked by the team |
| the pitch slides | made with AI support |
| the video voice | AI-generated |
| code review | another model (GPT) reviewed the engine and agent code at marked points; the defects found were fixed, each with a test (recorded in `README.md`, `LEIA-ME-motor.md` and `LEIA-ME-agente.md` under `backend/orbita/`) |

**Models used in development:** Claude, by Anthropic, for programming and writing; occasional reviews by another model (GPT).

What is not AI output: the data (NASA, INMET, IBGE), the published crop values (FAO, Embrapa, ZARC) and the project decisions.

## 2. In the product

The agent (the AI that talks with the farmer) uses a language model called through OpenRouter:

- default: `anthropic/claude-haiku-5.5` (Claude Haiku 5.5, by Anthropic);
- tested fallback: `deepseek/deepseek-v4.1-flash` (DeepSeek V4.1 Flash).

The key lives only in the terminal environment (`OPENROUTER_API_KEY`); no file in the repository holds a key. Without a key, the product works with the saved conversations and the engine's ready-made sentences.

The engine (the calculation) does not use AI. The explanation it writes is built from ready-made sentences filled with the numbers of the calculation.

## 3. The product's safeguards

The AI does four things: it understands what the farmer says, proposes the values of the farm form, chooses which tool to consult and writes the explanation. Everything else is enforced by the program, with tests:

- **The AI does not create numbers.** Every number in its text is checked against the calculation (the form, the comparison and what the tools returned in that turn). If a number is left over, the AI tries once more; if it happens again, its text does not reach the screen and the engine's ready-made sentences are shown instead.
- **What has no calculation is stated as general knowledge.** Nutrients, pests and markets are not measured. The answer is labeled as general knowledge, with a notice in front, and with no numbers.
- **The answer tells the farmer to check with the agronomist.** Every answer carries the notice "Converse com o agrônomo antes de decidir." ("Talk to your agronomist before deciding."). The AI does not choose the rotation for the farmer.
- **The calculation only runs after the farmer says "yes"** to the form, and the program reads that "yes", not the AI.
- **Every answer with a confirmed form brings 3 or more rotations**, including the current one, each with the evidence, the benefit, the risk and what is still unknown.
- **Every answer says where it came from:** `texto_de` (AI or ready-made sentences) and `apoio` (the calculation, the local data or general knowledge).
- **No personal data is requested** (name, phone, tax ID, address), and the API stores nothing.

Where this is written and tested: `backend/orbita/LEIA-ME-agente.md` (the table "O que a IA faz e o que o programa garante") and the tests `backend/orbita/tests/test_agente.py`, `test_ficha.py`, `test_ferramentas.py` and `test_modelo.py`.

## 4. What the safeguards do not catch

The check looks at whether each number in the text exists in the calculation. It does not check what the number refers to, its sign, or numbers written out in words. A sentence that wrongly compares two correct numbers can pass. Two known meaning swaps are blocked by the program (the days of covered soil, and "the water ran out" said about the day the water stress only began). For that reason the 4 saved conversations (13 agent turns, 9 with AI text) were read one by one against the calculation before being stored.

## 5. Contest rules we follow

- We do not use the NASA logo and we do not say NASA endorses the project. We use public NASA data.
- No name, image or voice of anyone under 18 appears in the project.
- The submission material is in English; the main documents exist in Portuguese and in English.
