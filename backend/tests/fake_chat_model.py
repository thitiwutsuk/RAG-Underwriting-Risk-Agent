"""A minimal fake chat model for testing agent wiring (session memory, graph
structure) without spending real LLM API calls."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class CountingFakeChatModel(BaseChatModel):
    """Replies with how many human messages it has seen so far in the message
    list passed to it -- enough to prove whether two sessions share history."""

    @property
    def _llm_type(self) -> str:
        return "counting-fake"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        # create_agent always binds tools onto the model; this fake ignores
        # them and never emits tool calls, which is fine for tests that only
        # exercise session/thread memory rather than tool-calling behavior.
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        human_count = sum(1 for m in messages if m.type == "human")
        content = f"seen {human_count} human message(s) in this thread"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])
