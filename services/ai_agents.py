from agents import Agent, Runner, trace, function_tool
import ollama
import httpx
from dotenv import load_dotenv
import os
from psycopg.rows import dict_row
from db import pool
import psycopg
import asyncio
import json

load_dotenv(override=True)

DB_NAME = os.getenv("DB_NAME", "recdesk_app")
DB_PARAMS = f"dbname={DB_NAME} user={os.getenv('DB_USER')} password={os.getenv('DB_PASSWORD')} host=localhost"



#tools below
@function_tool
async def get_users_with_interests() -> dict:
    """Fetch users name and email address along with their interests from the database."""
    query = """
        SELECT
            info->'user'->>'name' AS name,
            info->'user'->>'email' AS email,
            COALESCE(info->'interests', '[]'::jsonb) AS interests
        FROM customer_data
        WHERE info ? 'user'
    """

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            rows = await cur.fetchall()

    users = [
        {
            "name": row.get("name"),
            "email": row.get("email"),
            "interests": row.get("interests") or [],
        }
        for row in rows
        if row.get("name") and row.get("email")
    ]

    return {"users": users}

@function_tool
async def send_email_via_postmark(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str
) -> dict:
    """Send an email using Postmark API."""
    
    message_stream = "outbound"
    server_token = os.getenv("POSTMARK_API_KEY")
    if not server_token:
        raise ValueError("POSTMARK_API_KEY is not set")

    from_email = os.getenv("POSTMARK_FROM_EMAIL")
    if not from_email:
        raise ValueError("POSTMARK_FROM_EMAIL is not set")

    replyto_email = os.getenv("POSTMARK_REPLYTO_EMAIL")
    if not replyto_email:
        raise ValueError("POSTMARK_REPLYTO_EMAIL is not set")
        
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Postmark-Server-Token": server_token,
    }

    payload = {
        "From": from_email,
        "To": to_email,
        "ReplyTo": replyto_email,
        "Subject": subject,
        "TextBody": text_body,
        "HtmlBody": html_body,
        "MessageStream": message_stream,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.postmarkapp.com/email",
            headers=headers,
            json=payload,
        )

    response.raise_for_status()
    return response.json()

def _to_pgvector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"

@function_tool
async def insert_campaign_audit(
    theme: str,
    email_address_list: list[str],
    email_sent: str,
) -> dict:
    """Insert an audit row into campaign_audit after campaign emails are sent."""
    if not theme or not theme.strip():
        raise ValueError("theme is required")
    if not email_address_list:
        raise ValueError("email_address_list is required")
    if not email_sent or not email_sent.strip():
        raise ValueError("email_sent is required")

    if getattr(pool, "closed", False):
        await pool.open()

    query = """
        INSERT INTO campaign_audit (theme, email_address_list, email_sent)
        VALUES (%s, %s, %s)
        RETURNING id, created_at
    """

    email_addresses_text = json.dumps(email_address_list)

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, (theme.strip(), email_addresses_text, email_sent.strip()))
            inserted_row = await cur.fetchone()
        await conn.commit()

    return {
        "status": "inserted",
        "id": inserted_row.get("id") if inserted_row else None,
        "created_at": inserted_row.get("created_at").isoformat() if inserted_row and inserted_row.get("created_at") else None,
    }

@function_tool
async def get_relevant_program_data(user_query: str, year: int, limit: int = 8) -> dict:
    query_embedding_response = ollama.embed(
        model="nomic-embed-text:v1.5",
        input=user_query,
    )
    query_embedding = query_embedding_response["embeddings"][0]
    query_embedding_literal = _to_pgvector_literal(query_embedding)

    sql = """
        SELECT
            content,
            metadata,
            program_year,
            1 - (embedding <=> %s::vector) AS similarity
        FROM public.rec_programs
        WHERE program_year = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    if getattr(pool, "closed", False):
        await pool.open()

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, (query_embedding_literal, year, query_embedding_literal, limit))
            rows = await cur.fetchall()

    results = [
        {
            "content": row.get("content"),
            "metadata": row.get("metadata") or {},
            "program_year": row.get("program_year"),
            "similarity": float(row.get("similarity") or 0.0),
        }
        for row in rows
    ]

    combined_context = "\n\n---\n\n".join(
        item["content"] for item in results if item.get("content")
    )

    return {
        "schema": {
            "content": "has chunk data",
            "metadata": "has metadata about chunk",
            "embedding": "embeddings created using nomic-embed-text:v1.5 model",
            "program_year": "the year the data is related. all programs in the embeddings and content belong to this year",
        },
        "query": user_query,
        "year": year,
        "users_message": "Top relevant program chunks for AI processing",
        "results": results,
        "context": combined_context,
    }
