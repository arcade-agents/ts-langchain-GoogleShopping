---
title: "Build a GoogleShopping agent with LangChain (TypeScript) and Arcade"
slug: "ts-langchain-GoogleShopping"
framework: "langchain-ts"
language: "typescript"
toolkits: ["GoogleShopping"]
tools: []
difficulty: "beginner"
generated_at: "2026-03-12T01:34:42Z"
source_template: "ts_langchain"
agent_repo: ""
tags:
  - "langchain"
  - "typescript"
  - "googleshopping"
---

# Build a GoogleShopping agent with LangChain (TypeScript) and Arcade

In this tutorial you'll build an AI agent using [LangChain](https://js.langchain.com/) with [LangGraph](https://langchain-ai.github.io/langgraphjs/) in TypeScript and [Arcade](https://arcade.dev) that can interact with GoogleShopping tools — with built-in authorization and human-in-the-loop support.

## Prerequisites

- The [Bun](https://bun.com) runtime
- An [Arcade](https://arcade.dev) account and API key
- An OpenAI API key

## Project Setup

First, create a directory for this project, and install all the required dependencies:

````bash
mkdir googleshopping-agent && cd googleshopping-agent
bun install @arcadeai/arcadejs @langchain/langgraph @langchain/core langchain chalk
````

## Start the agent script

Create a `main.ts` script, and import all the packages and libraries. Imports from 
the `"./tools"` package may give errors in your IDE now, but don't worry about those
for now, you will write that helper package later.

````typescript
"use strict";
import { getTools, confirm, arcade } from "./tools";
import { createAgent } from "langchain";
import {
  Command,
  MemorySaver,
  type Interrupt,
} from "@langchain/langgraph";
import chalk from "chalk";
import * as readline from "node:readline/promises";
````

## Configuration

In `main.ts`, configure your agent's toolkits, system prompt, and model. Notice
how the system prompt tells the agent how to navigate different scenarios and
how to combine tool usage in specific ways. This prompt engineering is important
to build effective agents. In fact, the more agentic your application, the more
relevant the system prompt to truly make the agent useful and effective at
using the tools at its disposal.

````typescript
// configure your own values to customize your agent

// The Arcade User ID identifies who is authorizing each service.
const arcadeUserID = process.env.ARCADE_USER_ID;
if (!arcadeUserID) {
  throw new Error("Missing ARCADE_USER_ID. Add it to your .env file.");
}
// This determines which MCP server is providing the tools, you can customize this to make a Slack agent, or Notion agent, etc.
// all tools from each of these MCP servers will be retrieved from arcade
const toolkits=['GoogleShopping'];
// This determines isolated tools that will be
const isolatedTools=[];
// This determines the maximum number of tool definitions Arcade will return
const toolLimit = 100;
// This prompt defines the behavior of the agent.
const systemPrompt = "# AI Agent Prompt \u2014 Google Shopping ReAct Agent\n\n## Introduction\nYou are a ReAct-style shopping assistant agent that helps users find and compare products using Google Shopping. Use the provided GoogleShopping_SearchProducts tool to locate product listings, extract key details (title, price, seller, rating, availability, link), and deliver clear, sourced recommendations. Always follow ReAct conventions: alternate explicit thoughts (reasoning) and actions (tool calls), and produce a concise, user-facing final answer.\n\n## Instructions\n- Always use the ReAct pattern in your reasoning trace. Each step should include:\n  - Thought: (your internal reasoning, concise)\n  - Action: (the tool call and parameters, when applicable)\n  - Observation: (tool output summary)\n  - Thought: (interpretation)\n  - ...repeat until ready to answer\n  - Final Answer: (clean, user-facing response; no internal thoughts)\n- Use the GoogleShopping_SearchProducts tool exactly with the parameters:\n  - keywords (required): query string describing the product and constraints (brand, model, price limits, features).\n  - country_code (optional): 2-letter country code (default \u0027us\u0027). Use to localize availability/currency.\n  - language_code (optional): 2-letter language code (default \u0027en\u0027).\n- When uncertain about user requirements (budget, brand, must-have features, country), ask a clarifying question before searching.\n- Do not fabricate product details. If the tool returns limited fields, explicitly state which fields are unavailable.\n- Include source links for each recommended product (use the link field returned by the tool).\n- Respect currency and units\u2014reflect the country or ask user to confirm if ambiguous.\n- If a search returns no results or errors, refine the query and/or ask the user for clarification.\n- Limit search calls: try to gather needed info in 1\u20133 targeted searches, refining queries if needed.\n- For comparisons, extract and present a concise table or bullet list of key specs (title, price, seller, rating, link).\n- State confidence and any caveats (stock changes, shipping, taxes, promotions).\n\n## Tool usage examples\nWhen calling the tool, format the action like this:\n\n```\nAction: GoogleShopping_SearchProducts\n{\n  \"keywords\": \"Sony WH-1000XM5 noise cancelling headphones under $350\",\n  \"country_code\": \"us\",\n  \"language_code\": \"en\"\n}\n```\n\nAfter the tool returns, summarize the Observation:\n\n```\nObservation: 5 products found. Top results:\n- Sony WH-1000XM5 \u2014 $298 \u2014 Amazon \u2014 4.6 stars \u2014 link: https://...\n- Sony WH-1000XM5 (bundle) \u2014 $329 \u2014 Best Buy \u2014 4.5 stars \u2014 link: https://...\n...\n```\n\nThen continue reasoning and act accordingly.\n\n## Workflows\nBelow are common workflows and the recommended sequence of actions (tool calls). Each workflow shows an example of how to think and which calls to make.\n\n1) Quick Product Search (single best match)\n- Purpose: Find a single product matching a concise user query.\n- Sequence:\n  - Clarify if needed (budget, country).\n  - Action: GoogleShopping_SearchProducts with focused keywords.\n  - Observation: Summarize top 3 results.\n  - Final Answer: Provide best match with title, price, seller, rating, link, plus one-sentence rationale.\n\nExample:\n```\nThought: User asked for \"iPhone 14 128GB\" \u2014 assume US unless told otherwise.\nAction: GoogleShopping_SearchProducts\n{ \"keywords\": \"iPhone 14 128GB\", \"country_code\": \"us\", \"language_code\": \"en\" }\nObservation: ...\nFinal Answer: ...\n```\n\n2) Comparative Shopping (find best options within constraints)\n- Purpose: Present 3\u20135 top options that meet criteria (budget, features).\n- Sequence:\n  - Ask clarifying questions if constraints are missing.\n  - Action: GoogleShopping_SearchProducts with query including constraints (e.g., \"under $500\", \"4K\", \"OLED\").\n  - If results are broad, refine: call GoogleShopping_SearchProducts again with tighter keywords (e.g., add brand or phrase \"best seller\", \"top rated\").\n  - Observation: Aggregate and normalize price/currency data.\n  - Final Answer: Provide a ranked list (price, rating, seller, link) and short pros/cons for each.\n\n3) Find Cheapest Option Meeting Minimum Specs\n- Purpose: Identify lowest-price item that satisfies must-haves.\n- Sequence:\n  - Clarify must-have specs and shipping/country.\n  - Action: GoogleShopping_SearchProducts with strict keywords (\"must-have\", brand, model, \"refurbished\" only if allowed).\n  - Observation: Filter results for specs (if tool doesn\u0027t provide specs, state uncertainty and list product pages for user validation).\n  - Final Answer: Provide the cheapest qualifying product, price, seller, link, and ask if they want to purchase or track price.\n\n4) Top-Rated within Budget\n- Purpose: Show highest-rated products within a budget.\n- Sequence:\n  - Confirm budget and country.\n  - Action: GoogleShopping_SearchProducts with keywords including budget (\"under $200\") and product type.\n  - Repeat with synonyms/brand names if few results.\n  - Observation: Extract ratings; if ratings missing, note it.\n  - Final Answer: List top-rated products (title, price, rating, seller, link).\n\n5) Accessory or Complement Finder\n- Purpose: Find accessories for a specified product (cases, chargers).\n- Sequence:\n  - Clarify product model and compatibility requirements.\n  - Action: GoogleShopping_SearchProducts e.g., \"iPhone 14 leather case MagSafe compatible\".\n  - Observation: Summarize compatible items.\n  - Final Answer: Provide recommended accessories with compatibility notes and links.\n\n6) Iterative Refinement (when initial search returns too many or irrelevant results)\n- Purpose: Narrow down results through targeted re-searches.\n- Sequence:\n  - Action: GoogleShopping_SearchProducts with broad keywords.\n  - Observation: If irrelevant, Thought: identify missing filters (brand, size, price).\n  - Action: GoogleShopping_SearchProducts with refined keywords.\n  - Repeat until results are relevant or user asks to stop.\n  - Final Answer: Present final, filtered results with sources.\n\n## Output format for Final Answer\n- Start with a one-line summary recommendation (1\u20132 sentences).\n- Provide a short ranked list (3\u20135 items) with:\n  - Title\n  - Price (and currency)\n  - Seller/merchant\n  - Rating (if available)\n  - Link (source URL)\n  - One-line pros/cons or reason for recommendation\n- End with a short follow-up question (\"Would you like help buying one? Want me to track price or check coupons?\").\n\nExample final answer:\n```\nFinal Answer:\nBest overall: Sony WH-1000XM5 \u2014 $298 (Amazon) \u2014 4.6\u2605\n- Link: https://...\n- Why: best noise cancellation and battery life for the price.\n\nAlso consider:\n1) Sony WH-1000XM5 (bundle) \u2014 $329 \u2014 Best Buy \u2014 4.5\u2605 \u2014 https://...\n2) Bose QuietComfort 45 \u2014 $249 \u2014 Amazon \u2014 4.4\u2605 \u2014 https://...\nWould you like me to check stock at a specific retailer or set up a price alert?\n```\n\n## Handling errors and no-results\n- If tool returns an error: Thought: note the error, ask user if they want to retry or change scope.\n- If no results: Thought: propose clarifications or alternative keywords (e.g., broaden price range, allow refurbished).\n- If product details are incomplete: present what you have and include links so the user can verify specifics.\n\n## Safety, honesty, and provenance\n- Never hallucinate prices, ratings, or links. If uncertain, label as \"not provided by tool\".\n- Always include the source links returned by the tool.\n- If availability or price may change quickly, add a caveat about possible changes since the search.\n\n---\n\nUse this prompt and workflows whenever you need to search Google Shopping. Remember: Think (short), Act (tool), Observe (tool output), Repeat, then produce a clear Final Answer with sources and follow-up options.";
// This determines which LLM will be used inside the agent
const agentModel = process.env.OPENAI_MODEL;
if (!agentModel) {
  throw new Error("Missing OPENAI_MODEL. Add it to your .env file.");
}
// This allows LangChain to retain the context of the session
const threadID = "1";
````

Set the following environment variables in a `.env` file:

````bash
ARCADE_API_KEY=your-arcade-api-key
ARCADE_USER_ID=your-arcade-user-id
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5-mini
````

## Implementing the `tools.ts` module

The `tools.ts` module fetches Arcade tool definitions and converts them to LangChain-compatible tools using Arcade's Zod schema conversion:

### Create the file and import the dependencies

Create a `tools.ts` file, and add import the following. These will allow you to build the helper functions needed to convert Arcade tool definitions into a format that LangChain can execute. Here, you also define which tools will require human-in-the-loop confirmation. This is very useful for tools that may have dangerous or undesired side-effects if the LLM hallucinates the values in the parameters. You will implement the helper functions to require human approval in this module.

````typescript
import { Arcade } from "@arcadeai/arcadejs";
import {
  type ToolExecuteFunctionFactoryInput,
  type ZodTool,
  executeZodTool,
  isAuthorizationRequiredError,
  toZod,
} from "@arcadeai/arcadejs/lib/index";
import { type ToolExecuteFunction } from "@arcadeai/arcadejs/lib/zod/types";
import { tool } from "langchain";
import {
  interrupt,
} from "@langchain/langgraph";
import readline from "node:readline/promises";

// This determines which tools require human in the loop approval to run
const TOOLS_WITH_APPROVAL = [];
````

### Create a confirmation helper for human in the loop

The first helper that you will write is the `confirm` function, which asks a yes or no question to the user, and returns `true` if theuser replied with `"yes"` and `false` otherwise.

````typescript
// Prompt user for yes/no confirmation
export async function confirm(question: string, rl?: readline.Interface): Promise<boolean> {
  let shouldClose = false;
  let interface_ = rl;

  if (!interface_) {
      interface_ = readline.createInterface({
          input: process.stdin,
          output: process.stdout,
      });
      shouldClose = true;
  }

  const answer = await interface_.question(`${question} (y/n): `);

  if (shouldClose) {
      interface_.close();
  }

  return ["y", "yes"].includes(answer.trim().toLowerCase());
}
````

Tools that require authorization trigger a LangGraph interrupt, which pauses execution until the user completes authorization in their browser.

### Create the execution helper

This is a wrapper around the `executeZodTool` function. Before you execute the tool, however, there are two logical checks to be made:

1. First, if the tool the agent wants to invoke is included in the `TOOLS_WITH_APPROVAL` variable, human-in-the-loop is enforced by calling `interrupt` and passing the necessary data to call the `confirm` helper. LangChain will surface that `interrupt` to the agentic loop, and you will be required to "resolve" the interrupt later on. For now, you can assume that the reponse of the `interrupt` will have enough information to decide whether to execute the tool or not, depending on the human's reponse.
2. Second, if the tool was approved by the human, but it doesn't have the authorization of the integration to run, then you need to present an URL to the user so they can authorize the OAuth flow for this operation. For this, an execution is attempted, that may fail to run if the user is not authorized. When it fails, you interrupt the flow and send the authorization request for the harness to handle. If the user authorizes the tool, the harness will reply with an `{authorized: true}` object, and the system will retry the tool call without interrupting the flow.

````typescript
export function executeOrInterruptTool({
  zodToolSchema,
  toolDefinition,
  client,
  userId,
}: ToolExecuteFunctionFactoryInput): ToolExecuteFunction<any> {
  const { name: toolName } = zodToolSchema;

  return async (input: unknown) => {
    try {

      // If the tool is on the list that enforces human in the loop, we interrupt the flow and ask the user to authorize the tool

      if (TOOLS_WITH_APPROVAL.includes(toolName)) {
        const hitl_response = interrupt({
          authorization_required: false,
          hitl_required: true,
          tool_name: toolName,
          input: input,
        });

        if (!hitl_response.authorized) {
          // If the user didn't approve the tool call, we throw an error, which will be handled by LangChain
          throw new Error(
            `Human in the loop required for tool call ${toolName}, but user didn't approve.`
          );
        }
      }

      // Try to execute the tool
      const result = await executeZodTool({
        zodToolSchema,
        toolDefinition,
        client,
        userId,
      })(input);
      return result;
    } catch (error) {
      // If the tool requires authorization, we interrupt the flow and ask the user to authorize the tool
      if (error instanceof Error && isAuthorizationRequiredError(error)) {
        const response = await client.tools.authorize({
          tool_name: toolName,
          user_id: userId,
        });

        // We interrupt the flow here, and pass everything the handler needs to get the user's authorization
        const interrupt_response = interrupt({
          authorization_required: true,
          authorization_response: response,
          tool_name: toolName,
          url: response.url ?? "",
        });

        // If the user authorized the tool, we retry the tool call without interrupting the flow
        if (interrupt_response.authorized) {
          const result = await executeZodTool({
            zodToolSchema,
            toolDefinition,
            client,
            userId,
          })(input);
          return result;
        } else {
          // If the user didn't authorize the tool, we throw an error, which will be handled by LangChain
          throw new Error(
            `Authorization required for tool call ${toolName}, but user didn't authorize.`
          );
        }
      }
      throw error;
    }
  };
}
````

### Create the tool retrieval helper

The last helper function of this module is the `getTools` helper. This function will take the configurations you defined in the `main.ts` file, and retrieve all of the configured tool definitions from Arcade. Those definitions will then be converted to LangGraph `Function` tools, and will be returned in a format that LangChain can present to the LLM so it can use the tools and pass the arguments correctly. You will pass the `executeOrInterruptTool` helper you wrote in the previous section so all the bindings to the human-in-the-loop and auth handling are programmed when LancChain invokes a tool.


````typescript
// Initialize the Arcade client
export const arcade = new Arcade();

export type GetToolsProps = {
  arcade: Arcade;
  toolkits?: string[];
  tools?: string[];
  userId: string;
  limit?: number;
}


export async function getTools({
  arcade,
  toolkits = [],
  tools = [],
  userId,
  limit = 100,
}: GetToolsProps) {

  if (toolkits.length === 0 && tools.length === 0) {
      throw new Error("At least one tool or toolkit must be provided");
  }

  // Todo(Mateo): Add pagination support
  const from_toolkits = await Promise.all(toolkits.map(async (tkitName) => {
      const definitions = await arcade.tools.list({
          toolkit: tkitName,
          limit: limit
      });
      return definitions.items;
  }));

  const from_tools = await Promise.all(tools.map(async (toolName) => {
      return await arcade.tools.get(toolName);
  }));

  const all_tools = [...from_toolkits.flat(), ...from_tools];
  const unique_tools = Array.from(
      new Map(all_tools.map(tool => [tool.qualified_name, tool])).values()
  );

  const arcadeTools = toZod({
    tools: unique_tools,
    client: arcade,
    executeFactory: executeOrInterruptTool,
    userId: userId,
  });

  // Convert Arcade tools to LangGraph tools
  const langchainTools = arcadeTools.map(({ name, description, execute, parameters }) =>
    (tool as Function)(execute, {
      name,
      description,
      schema: parameters,
    })
  );

  return langchainTools;
}
````

## Building the Agent

Back on the `main.ts` file, you can now call the helper functions you wrote to build the agent.

### Retrieve the configured tools

Use the `getTools` helper you wrote to retrieve the tools from Arcade in LangChain format:

````typescript
const tools = await getTools({
  arcade,
  toolkits: toolkits,
  tools: isolatedTools,
  userId: arcadeUserID,
  limit: toolLimit,
});
````

### Write an interrupt handler

When LangChain is interrupted, it will emit an event in the stream that you will need to handle and resolve based on the user's behavior. For a human-in-the-loop interrupt, you will call the `confirm` helper you wrote earlier, and indicate to the harness whether the human approved the specific tool call or not. For an auth interrupt, you will present the OAuth URL to the user, and wait for them to finishe the OAuth dance before resolving the interrupt with `{authorized: true}` or `{authorized: false}` if an error occurred:

````typescript
async function handleInterrupt(
  interrupt: Interrupt,
  rl: readline.Interface
): Promise<{ authorized: boolean }> {
  const value = interrupt.value;
  const authorization_required = value.authorization_required;
  const hitl_required = value.hitl_required;
  if (authorization_required) {
    const tool_name = value.tool_name;
    const authorization_response = value.authorization_response;
    console.log("⚙️: Authorization required for tool call", tool_name);
    console.log(
      "⚙️: Please authorize in your browser",
      authorization_response.url
    );
    console.log("⚙️: Waiting for you to complete authorization...");
    try {
      await arcade.auth.waitForCompletion(authorization_response.id);
      console.log("⚙️: Authorization granted. Resuming execution...");
      return { authorized: true };
    } catch (error) {
      console.error("⚙️: Error waiting for authorization to complete:", error);
      return { authorized: false };
    }
  } else if (hitl_required) {
    console.log("⚙️: Human in the loop required for tool call", value.tool_name);
    console.log("⚙️: Please approve the tool call", value.input);
    const approved = await confirm("Do you approve this tool call?", rl);
    return { authorized: approved };
  }
  return { authorized: false };
}
````

### Create an Agent instance

Here you create the agent using the `createAgent` function. You pass the system prompt, the model, the tools, and the checkpointer. When the agent runs, it will automatically use the helper function you wrote earlier to handle tool calls and authorization requests.

````typescript
const agent = createAgent({
  systemPrompt: systemPrompt,
  model: agentModel,
  tools: tools,
  checkpointer: new MemorySaver(),
});
````

### Write the invoke helper

This last helper function handles the streaming of the agent’s response, and captures the interrupts. When the system detects an interrupt, it adds the interrupt to the `interrupts` array, and the flow interrupts. If there are no interrupts, it will just stream the agent’s to your console.

````typescript
async function streamAgent(
  agent: any,
  input: any,
  config: any
): Promise<Interrupt[]> {
  const stream = await agent.stream(input, {
    ...config,
    streamMode: "updates",
  });
  const interrupts: Interrupt[] = [];

  for await (const chunk of stream) {
    if (chunk.__interrupt__) {
      interrupts.push(...(chunk.__interrupt__ as Interrupt[]));
      continue;
    }
    for (const update of Object.values(chunk)) {
      for (const msg of (update as any)?.messages ?? []) {
        console.log("🤖: ", msg.toFormattedString());
      }
    }
  }

  return interrupts;
}
````

### Write the main function

Finally, write the main function that will call the agent and handle the user input.

Here the `config` object configures the `thread_id`, which tells the agent to store the state of the conversation into that specific thread. Like any typical agent loop, you:

1. Capture the user input
2. Stream the agent's response
3. Handle any authorization interrupts
4. Resume the agent after authorization
5. Handle any errors
6. Exit the loop if the user wants to quit

````typescript
async function main() {
  const config = { configurable: { thread_id: threadID } };
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  console.log(chalk.green("Welcome to the chatbot! Type 'exit' to quit."));
  while (true) {
    const input = await rl.question("> ");
    if (input.toLowerCase() === "exit") {
      break;
    }
    rl.pause();

    try {
      let agentInput: any = {
        messages: [{ role: "user", content: input }],
      };

      // Loop until no more interrupts
      while (true) {
        const interrupts = await streamAgent(agent, agentInput, config);

        if (interrupts.length === 0) {
          break; // No more interrupts, we're done
        }

        // Handle all interrupts
        const decisions: any[] = [];
        for (const interrupt of interrupts) {
          decisions.push(await handleInterrupt(interrupt, rl));
        }

        // Resume with decisions, then loop to check for more interrupts
        // Pass single decision directly, or array for multiple interrupts
        agentInput = new Command({ resume: decisions.length === 1 ? decisions[0] : decisions });
      }
    } catch (error) {
      console.error(error);
    }

    rl.resume();
  }
  console.log(chalk.red("👋 Bye..."));
  process.exit(0);
}

// Run the main function
main().catch((err) => console.error(err));
````

## Running the Agent

### Run the agent

```bash
bun run main.ts
```

You should see the agent responding to your prompts like any model, as well as handling any tool calls and authorization requests.

## Next Steps

- Clone the [repository](https://github.com/arcade-agents/ts-langchain-GoogleShopping) and run it
- Add more toolkits to the `toolkits` array to expand capabilities
- Customize the `systemPrompt` to specialize the agent's behavior
- Explore the [Arcade documentation](https://docs.arcade.dev) for available toolkits

