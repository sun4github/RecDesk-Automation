from agents import Agent, Runner, trace, function_tool
import os
import asyncio
import json
import psycopg
import ollama
from psycopg.rows import dict_row
from db import pool
from services.ai_agents import (
    get_relevant_program_data,
    get_users_with_interests,
    send_email_via_postmark,
)


async def process_email(from_email: str, subject: str, text_body: str, message_id: str, raw_email: str) -> str:
    print("Processing email content with AI...")
    print(f"Content: {text_body}")

    #agents here
    instructions1 = """You are a rec desk program coordinator working for Lanc Rec Desk \
    that helps parents and citizens find the right programs that fit their needs. You will get emails from parents \
    If no year or season is specified, assume they are looking for programs in the current year and season. \
    Your job is to find the right programs for them, and respond to them to their email in a convincing way. Use the get_relevant_program_data tool to \
    gather program data. Use the send_email_via_postmark tool to send an email to the provided send_email of the parent. \
    write compelling email content, and send an email to the parent who responded. Your tone should be sporty but exciting
    """

    coordinator_agent = Agent(
        name="Rec Desk Program Coordinator Agent",
        instructions=instructions1,
        model="gpt-5-mini-2025-08-07",
        tools=[get_relevant_program_data, send_email_via_postmark])

    response = await Runner.run(coordinator_agent, json.dumps({
        "from_email": from_email,
        "subject": subject,
        "text_body": text_body,
        "message_id": message_id,
        "raw_email": raw_email
    }))
    print("\n=== Generated Email Response ===")
    print(response.final_output)

    return f"Processed email content: {from_email}"


async def start_new_campaign(theme: str, id: str) -> dict:
    print("Starting new campaign...")
    print(f"Campaign ID: {id}, Theme: {theme}")

    #agents here
    instructions1 = """You are a rec desk marketing agent working for Lanc Rec Desk \
    that helps with email marketing campaigns for rec center programs in a given season. Use the tools provided to \
    gather program data and write compelling email content. Your tone should be professional yet engaging \
    If no year or season is specified, assume they are looking for programs in the current year and season. 
    """

    instructions2 = """You are a rec desk marketing agent working for Lanc Rec Desk \
    that helps with email marketing campaigns for rec center programs in a given season. Use the tools provided to \
    gather program data and write funny and context aware email content. Stay casual and lighthearted. \
    If no year or season is specified, assume they are looking for programs in the current year and season.
    """

    manager_instructions = """You are the Campaign Manager Agent. Your job is to coordinate two marketing agents \
    to create a well-rounded email marketing campaign for the Rec Desk. \

    Follow these steps carefully: \
    1. Generate drafts: use the funny_agents_tool and serious_agent_tool to generate two different email drafts based on the campaign theme. \
    2. Evaluate drafts: review both email drafts and assess their effectiveness in engaging the target audience. \
    3. Select the best draft: choose the email draft that you believe will have the highest impact for the campaign. \
    4. Personalize and send: use the get_users_with_interests tool to fetch a list of users interested in the campaign theme. \

    Critical Rules: \
    - Do not generate email content yourself; rely solely on the two marketing agents for drafts. \
    - Ensure the selected email draft aligns with the campaign theme and resonates with the target audience. \
    - Use the send_email_via_postmark tool to send the finalized email to all users interested in the campaign theme. \
    """

    marketing_agent_serious = Agent(
        name="Rec Desk Marketing Agent - Serious Tone",
        instructions=instructions1,
        model="gpt-5-mini-2025-08-07",
        tools=[get_relevant_program_data])

    serious_agent_tool = marketing_agent_serious.as_tool(tool_name="serious_marketing_agent", tool_description="Generates serious marketing email content based on program data.")

    marketing_agent_funny = Agent(
        name="Rec Desk Marketing Agent - Funny Tone",
        instructions=instructions2,
        model="gpt-5-mini-2025-08-07",
        tools=[get_relevant_program_data])

    funny_agent_tool = marketing_agent_funny.as_tool(tool_name="funny_marketing_agent", tool_description="Generates funny marketing email content based on program data.")

    manager_agent = Agent(
        name = "Campaign Manager Agent",
        instructions=manager_instructions,
        model="gpt-5-mini-2025-08-07",
        tools=[serious_agent_tool, funny_agent_tool, get_users_with_interests, send_email_via_postmark]
    )


    with trace("Marketing campaign manager selecting best email"):
        best_email = await Runner.run(manager_agent, json.dumps({"campaign_theme": theme}))

    print(f"\n=== Selected Email for Campaign {id} ===")
    print(best_email.final_output)
    
    return {
        "status": "started",
        "campaign_id": id,
        "theme": theme,
    }




