# An agent that uses GoogleShopping tools provided to perform any task

## Purpose

# Introduction
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
   - Return the refined results to the user.

## MCP Servers

The agent uses tools from these Arcade MCP Servers:

- GoogleShopping

## Getting Started

1. Install dependencies:
    ```bash
    bun install
    ```

2. Set your environment variables:

    Copy the `.env.example` file to create a new `.env` file, and fill in the environment variables.
    ```bash
    cp .env.example .env
    ```

3. Run the agent:
    ```bash
    bun run main.ts
    ```