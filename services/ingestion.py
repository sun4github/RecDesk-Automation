import asyncio
import json
import psycopg
import ollama
from unstructured.partion.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title
from dotenv import load_dotenv
import os

load_dotenv(override=True)

DB_PARAMS = f"dbname=recdesk_app user={os.getenv('DB_USER')} password={os.getenv('DB_PASSWORD')} host=localhost"