# RecDesk-Automation

Automates RecDesk communication workflows for inbound parent emails and outbound seasonal campaign emails.

## What this API offers

The FastAPI app currently exposes these HTTP endpoints (all under `/api/v1/webhooks`):

### 1) `POST /inbound`
Handles inbound Postmark webhook payloads.

- Input model: `PostmarkInbound`
	- `From` -> `from_email`
	- `Subject` -> `subject`
	- `TextBody` -> `text_body`
	- `MessageID` -> `message_id`
	- `RawEmail` -> `raw_email`
- Security: HTTP Basic Auth via `verify_credentials`
- Behavior:
	- Returns immediately with `{ "status": "accepted" }`
	- Runs `process_email(...)` in a FastAPI background task
	- `process_email(...)` spins up a coordinator agent that can:
		- retrieve relevant rec program context (`get_relevant_program_data`)
		- send a response email (`send_email_via_postmark`)

### 2) `POST /campaign`
Starts a new outbound campaign.

- Input model: `Campaign`
	- `theme: string`
	- `id: string`
- Security: HTTP Basic Auth via `verify_credentials`
- Behavior:
	- Returns immediately with `{ "status": "campaign started" }`
	- Runs `start_new_campaign(theme, id)` in a background task
	- `start_new_campaign(...)` coordinates:
		- serious-tone marketing agent
		- funny-tone marketing agent
		- manager agent that can pick a draft and email users

### 3) `GET /status`
Simple health/status endpoint.

---

## Architecture

### High-level flow

1. FastAPI receives webhook/API request.
2. HTTP Basic auth is validated for protected routes.
3. Background task dispatches long-running AI workflow.
4. AI workflow uses tool functions for:
	 - vector retrieval from PostgreSQL + pgvector
	 - recipient/user lookup from JSONB customer table
	 - outbound Postmark email sending

### Application layers

- **API layer**
	- `main.py`: FastAPI app setup, router mounting, pool startup/shutdown
	- `api/webhook_handler.py`: request handlers and background task orchestration
	- `api/deps.py`: HTTP Basic auth dependency

- **Schema layer**
	- `schemas/postmark.py`: inbound payload parsing with Postmark field aliases
	- `schemas/campaign.py`: campaign request schema

- **Service layer**
	- `services/ai_service.py`: orchestrates runtime agents for inbound and campaign flows
	- `services/ai_agents.py`: reusable tool functions exposed with `@function_tool`
		- `get_users_with_interests`
		- `get_relevant_program_data`
		- `send_email_via_postmark`

- **Data + infra layer**
	- `db.py`: global async PostgreSQL connection pool
	- PostgreSQL tables used by service/tools:
		- `public.rec_programs`
		- `public.customer_data`

---

## Data model assumptions used by tools

### `public.rec_programs`

- `content`: chunk text
- `metadata`: metadata for chunk
- `embedding`: vector embedding generated with `nomic-embed-text:v1.5`
- `program_year`: year for that chunk/program context
- `source_file`: source filename (present but not required for most prompts)

### `public.customer_data`

`info` is JSONB and expected to contain:

```json
{
	"user": {
		"id": 102,
		"name": "Sun Kareer",
		"address": { "city": "Houston", "state": "TX" },
		"email": "sun4career@gmail.com"
	},
	"interests": ["tennis", "baseball"]
}
```

The user lookup tool returns:

```json
{
	"users": [
		{ "name": "...", "email": "...", "interests": [] }
	]
}
```

---

## Retrieval and AI context behavior

`get_relevant_program_data(user_query, year, limit)` performs:

1. Embeds the query using Ollama model `nomic-embed-text:v1.5`
2. Vector similarity search on `rec_programs.embedding` using pgvector distance
3. Filters by `program_year = year`
4. Returns an AI-friendly payload with:
	 - `results`: ranked chunk rows with similarity
	 - `context`: merged chunk content for prompt context
	 - schema descriptions for agent grounding

---

## Outbound email behavior

`send_email_via_postmark(...)` posts to Postmark:

- Endpoint: `https://api.postmarkapp.com/email`
- Required headers:
	- `X-Postmark-Server-Token`
	- `Content-Type: application/json`
	- `Accept: application/json`
- Payload fields used:
	- `From` (from `POSTMARK_FROM_EMAIL`)
	- `ReplyTo` (from `POSTMARK_REPLYTO_EMAIL`)
	- `To`, `Subject`, `TextBody`, `HtmlBody`, `MessageStream`

Note: Postmark requires `From` sender signature/domain to be verified.

---

## Ingestion pipeline (offline/CLI)

`services/ingestion.py` is a CLI-style async ingestion flow:

1. Parse and chunk PDF (`unstructured`)
2. Create embeddings for each chunk (`ollama.embed` with `nomic-embed-text:v1.5`)
3. Insert into `public.rec_programs` (`content`, `metadata`, `embedding`, `program_year`, `source_file`)

This pipeline populates the vector store used by API agents.

---

## Configuration overview

Environment variables used in the current implementation:

- DB/Auth:
	- `DB_USER`, `DB_PASSWORD`
	- `POSTMARK_USERNAME`, `POSTMARK_PASSWORD` (HTTP Basic auth for webhook routes)
- Postmark send:
	- `POSTMARK_API_KEY`
	- `POSTMARK_FROM_EMAIL`
	- `POSTMARK_REPLYTO_EMAIL`
- Optional DB selection in ingestion/tool code:
	- `DB_NAME` (defaults to `recdesk_app`)

---

## Notes

- API routes return quickly and defer heavy AI work to background tasks.
- Agent/tool integration depends on the OpenAI Agents SDK runtime.
- The README reflects behavior implemented in this workspace at the time of writing.
