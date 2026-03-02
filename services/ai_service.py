from openai import OpenAI
import os

async def process_email(from_email: str, subject: str, text_body: str, message_id: str, raw_email: str) -> str:
    print("Processing email content with AI...")
    print(f"Content: {text_body}")
    return f"Processed email content: {from_email}"