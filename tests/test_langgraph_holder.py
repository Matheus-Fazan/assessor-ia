import unittest
from uuid import uuid4

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from app.tool_holder import holder_context
from app.tool_interceptor import interceptar_tools


class Args(BaseModel):
    marker: str


class LangGraphIntegrationTests(unittest.TestCase):
    def test_real_toolnode_propagates_holder_and_defers_write(self):
        writes = []

        @tool("add_event", args_schema=Args)
        def add_event(marker: str) -> dict:
            """Store an event marker."""
            writes.append(marker)
            return {"status": "ok"}

        wrapped = interceptar_tools([add_event])[0]
        graph = StateGraph(MessagesState)
        graph.add_node("tools", ToolNode([wrapped]))
        graph.add_edge(START, "tools")
        graph.add_edge("tools", END)
        graph = graph.compile()
        marker = uuid4().hex
        message = AIMessage(content="", tool_calls=[{"name": "add_event", "args": {"marker": marker}, "id": uuid4().hex, "type": "tool_call"}])
        with holder_context() as holder:
            state = graph.invoke({"messages": [message]})
            self.assertIn('prepared', str(state["messages"][-1].content))
            self.assertEqual(writes, [])
            holder.commit()
        self.assertEqual(writes, [marker])


if __name__ == "__main__":
    unittest.main()
