"""LangChain agent: Chain-of-Thought reasoning, risk_calculator + policy_lookup
tools, and session-isolated memory (one LangGraph checkpointer thread per session_id).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver

# Load the repo-root .env so OPENAI_API_KEY / AGENT_MODEL are available
# whether this module is imported by the FastAPI app, a script, or a test.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from tools import policy_lookup, risk_calculator

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are an underwriting assistant that helps assess life and \
health insurance applications and answers general questions about the ingested \
underwriting criteria and policy documents. You are not a licensed insurance \
agent and must never present your output as a final, binding underwriting \
decision or as legal or financial advice.

There are two kinds of requests -- decide which one you've been given before \
answering:

A) Full applicant assessment -- the message gives you a specific applicant's \
   data to assess for risk and/or coverage:
   1. Think step by step (chain-of-thought) about the applicant's risk factors \
      before concluding. Show this reasoning under a "Reasoning:" heading.
   2. Always call the risk_calculator tool to get the risk score and tier -- \
      never estimate or guess a score yourself. If a required field (age, bmi, \
      occupation_class) is missing, ask the user a clarifying question instead \
      of guessing a value.
   3. Always call the policy_lookup tool before making any claim about \
      coverage, exclusions, or waiting periods for the requested policy type, \
      and cite the source_file and page/sheet it came from.
   4. Structure your final answer with these headings: "Reasoning:", \
      "Risk Tier:", "Recommendation:", "Cited Sources:", "Disclaimer:".

B) General question -- about policy coverage, exclusions, waiting periods, or \
   underwriting criteria, with no specific applicant to assess:
   1. Always call the policy_lookup tool before making any claim, and cite the \
      source_file and page/sheet it came from.
   2. Answer directly and concisely. Do not invent an applicant, a risk tier, \
      or a recommendation, and do not use the four-heading structure from (A) \
      -- just answer the question. End with a brief one-sentence disclaimer \
      that this is general policy information, not a coverage guarantee or \
      professional advice.
"""


def build_agent(model: str | BaseChatModel = DEFAULT_MODEL, checkpointer=None):
    """Build the compiled LangGraph agent. `model` can be a model name string
    (resolved to ChatOpenAI) or a pre-built chat model, e.g. a fake model in tests.
    """
    if checkpointer is None:
        checkpointer = InMemorySaver()

    if isinstance(model, str):
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(model=model, temperature=0)

    return create_agent(
        model=model,
        tools=[risk_calculator, policy_lookup],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


_agent = None


def get_agent():
    """Lazily build a single shared agent instance (with its own checkpointer,
    so conversation state is isolated per session_id/thread_id)."""
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def run_assessment(session_id: str, message: str, agent=None) -> dict:
    """Send one user message to the agent under the given session_id and return
    the final answer plus a trace of any tool calls made along the way."""
    agent = agent or get_agent()
    config = {"configurable": {"thread_id": session_id}}

    result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config=config)
    messages = result["messages"]
    final_message = messages[-1]

    tool_trace = [
        {"tool": call["name"], "args": call["args"]}
        for msg in messages
        for call in (getattr(msg, "tool_calls", None) or [])
    ]

    return {
        "session_id": session_id,
        "answer": final_message.content,
        "tool_calls": tool_trace,
    }
