"""Optional LangFuse tracing for the agent.

Enabled only when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set (e.g. a
free LangFuse Cloud account). With no credentials configured -- local dev,
CI, tests -- tracing is silently skipped and the agent behaves exactly as
before; nothing here should ever be able to break a request.
"""

import os


def get_langfuse_handler():
    """Return a LangChain-compatible LangFuse callback handler, or None if
    LangFuse isn't configured."""
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return None

    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        return None

    return CallbackHandler()
