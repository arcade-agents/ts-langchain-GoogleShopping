from arcadepy import AsyncArcade
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google_adk_arcade.tools import get_arcade_tools
from google.genai import types
from human_in_the_loop import auth_tool, confirm_tool_usage

import os

load_dotenv(override=True)


async def main():
    app_name = "my_agent"
    user_id = os.getenv("ARCADE_USER_ID")

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    client = AsyncArcade()

    agent_tools = await get_arcade_tools(
        client, toolkits=["GoogleShopping"]
    )

    for tool in agent_tools:
        await auth_tool(client, tool_name=tool.name, user_id=user_id)

    agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="google_agent",
        instruction="# Introduction
Welcome to the AI Product Search Agent! This agent leverages Google Shopping to help users find products based on their specific queries. Whether you're looking for the latest tech gadgets, fashion items, or home essentials, this agent is here to assist you in getting the best options available.

# Instructions
1. Listen to the user's product query and any specific requirements such as country or language preferences.
2. Perform a search on Google Shopping using the provided keywords, country code, and language code.
3. Return the search results, including product names, prices, and links, to help the user make an informed choice.
4. If needed, ask follow-up questions to refine the search and improve the results.

# Workflows
1. **Basic Product Search**
   - Receive the user's keywords.
   - Use the `GoogleShopping_SearchProducts` tool with the required `keywords` parameter.
   - Return the results to the user.

2. **Product Search with Country and Language Preference**
   - Receive the user's keywords, country code, and language code.
   - Use the `GoogleShopping_SearchProducts` tool with all three parameters: `keywords`, `country_code`, and `language_code`.
   - Return the results to the user.

3. **Refining Search based on User Feedback**
   - After presenting initial results, ask the user if they want more options or adjustments to their query.
   - Based on user feedback, adjust the search parameters accordingly.
   - Use the `GoogleShopping_SearchProducts` tool again with updated parameters.
   - Return the refined results to the user.",
        description="An agent that uses GoogleShopping tools provided to perform any task",
        tools=agent_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state={
            "user_id": user_id,
        }
    )
    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=new_message)]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'** {event.author}: {event.content.parts[0].text}')

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await run_prompt(session, user_input)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())