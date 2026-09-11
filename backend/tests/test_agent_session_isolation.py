"""Verifies that two concurrent sessions do not leak conversation context into
each other. Uses a fake chat model (see fake_chat_model.py) so this test costs
no real LLM API calls -- it exercises the LangGraph checkpointer/thread_id
wiring in agent.py, independent of actual reasoning quality.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import build_agent, run_assessment
from tests.fake_chat_model import CountingFakeChatModel


def test_two_concurrent_sessions_do_not_leak_message_history():
    agent = build_agent(model=CountingFakeChatModel())

    session_a_turn1 = run_assessment("session-A", "hello from A", agent=agent)
    session_b_turn1 = run_assessment("session-B", "hello from B", agent=agent)
    session_a_turn2 = run_assessment("session-A", "second message from A", agent=agent)

    assert "seen 1 human message" in session_a_turn1["answer"]
    assert "seen 1 human message" in session_b_turn1["answer"]
    assert "seen 2 human message" in session_a_turn2["answer"]


def test_same_session_id_accumulates_history_across_calls():
    agent = build_agent(model=CountingFakeChatModel())

    first = run_assessment("session-X", "first", agent=agent)
    second = run_assessment("session-X", "second", agent=agent)
    third = run_assessment("session-X", "third", agent=agent)

    assert "seen 1 human message" in first["answer"]
    assert "seen 2 human message" in second["answer"]
    assert "seen 3 human message" in third["answer"]
