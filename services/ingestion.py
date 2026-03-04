import asyncio
import json
import psycopg
import ollama
from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title
from dotenv import load_dotenv
import os
import argparse
import sys
from tqdm.asyncio import tqdm

load_dotenv(override=True)

DB_NAME = os.getenv("DB_NAME", "recdesk_app")
DB_PARAMS = f"dbname={DB_NAME} user={os.getenv('DB_USER')} password={os.getenv('DB_PASSWORD')} host=localhost"

async def ingest_document(file_path: str, year: int = None):
    print(f"Starting ingestion for document: {file_path}")
    #Connect to Postgres using psycopg 3 (Async)
    async with await psycopg.AsyncConnection.connect(DB_PARAMS) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT current_database(), to_regclass('public.rec_programs')")
            current_db, table_ref = await cur.fetchone()
            if table_ref is None:
                raise RuntimeError(
                    f"Table public.rec_programs was not found in database '{current_db}'. "
                    "Set DB_NAME to the database that contains rec_programs or create the table there."
                )

            print("🧐 Analyzing PDF layout (this takes a while for 45MB)...")

            #set A: partition and chunk PDF
            # 'hi_res' is used to identify tables and images in athletic programs
            elements = partition_pdf(filename=file_path, strategy="hi_res")
            chunks = chunk_by_title(elements, max_characters=1000)

            print(f"📦 Found {len(chunks)} chunks. Starting database upload...")

            async for chunk in tqdm(chunks, desc="Loading to Postgres"):
                text_content = str(chunk)
                metadata = chunk.metadata.to_dict()

                #step B: generate embedding locally on pi using ollama
                # use a model like 'nomic-embed-text' for best Pi performance
                response = ollama.embed(model="nomic-embed-text:v1.5", input=text_content)
                embedding = response['embeddings'][0]

                #step C: insert into Postgres with pgvector
                await cur.execute(
                    """
                    INSERT INTO public.rec_programs (content, metadata, embedding, program_year, source_file)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (text_content, json.dumps(metadata), embedding, year, os.path.basename(file_path))
                )
            await conn.commit()
    print(f"Completed ingestion for document: {file_path}")


async def main():
    # 1. Setup Argument Parser
    parser = argparse.ArgumentParser(description="Ingest a PDF into the Raspberry Pi Vector DB.")
    parser.add_argument(
        "pdf_path", 
        help="Path to the PDF file containing youth athletic programs"
    )
    parser.add_argument(
        "year", 
        type=int,
        help="Year of the youth athletic programs in the PDF"
    )
    
    args = parser.parse_args()

    # 2. Trigger the ingestion
    print(f"🚀 Starting ingestion for: {args.pdf_path} and year {args.year}")
    try:
        await ingest_document(args.pdf_path, args.year)
        print("✅ Ingestion completed successfully!")
    except Exception as e:
        print(f"❌ Error during ingestion: {e}", file=sys.stderr)

if __name__ == "__main__":
    # This triggers the async main function from the command line
    asyncio.run(main())