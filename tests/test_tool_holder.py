import concurrent.futures
import contextvars
import unittest
from uuid import uuid4
from app.tool_holder import ToolHolder, current_holder, holder_context, juiz_aprovou


class FakeTool:
    def __init__(self, name, store, fail=False):
        self.name, self.store, self.fail = name, store, fail

    def invoke(self, arguments):
        if self.fail:
            return {"status": "error"}
        self.store.append((self.name, arguments))
        return {"status": "ok"}


class HolderTests(unittest.TestCase):
    def test_three_writes_discarded_and_approved_once(self):
        for name in ("add_transaction", "update_transaction", "add_event"):
            with self.subTest(name=name):
                store, marker = [], uuid4().hex
                tool = FakeTool(name, store)
                with holder_context() as holder:
                    op = holder.prepare(tool, {"marker": marker})
                    self.assertTrue(op.operation_id)
                    holder.discard()
                    self.assertEqual(store, [])
                with holder_context() as holder:
                    holder.prepare(tool, {"marker": marker})
                    self.assertEqual(len(holder.commit()), 1)
                    with self.assertRaises(RuntimeError):
                        holder.commit()
                self.assertEqual(store, [(name, {"marker": marker})])

    def test_failure_stops_following_and_reports_partial(self):
        store = []
        holder = ToolHolder()
        holder.prepare(FakeTool("add_event", store), {})
        holder.prepare(FakeTool("update_transaction", store, fail=True), {})
        holder.prepare(FakeTool("add_google_event", store), {})
        results = holder.commit()
        self.assertEqual([r["result"]["status"] for r in results], ["ok", "error", "skipped"])
        self.assertEqual(len(store), 1)

    def test_context_isolation_and_propagation(self):
        with holder_context() as first:
            ctx = contextvars.copy_context()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                self.assertIs(pool.submit(ctx.run, current_holder).result(), first)
            with holder_context() as second:
                self.assertIs(current_holder(), second)
            self.assertIs(current_holder(), first)
        self.assertIsNone(current_holder())

    def test_only_current_turn_explicit_approval(self):
        for label in ("", "juiz:apoiada:abaixo_do_limiar noul=0.69", "juiz:erro", "juiz:apoiada noul=0.20", "juiz:apoiada noul=nan"):
            self.assertFalse(juiz_aprovou(label))
        self.assertTrue(juiz_aprovou("juiz:apoiada noul=0.70"))
        self.assertTrue(juiz_aprovou("juiz:apoiada noul=1.00"))



class InterceptorTests(unittest.TestCase):
    def test_intercepts_writes_and_leaves_reads_immediate(self):
        import importlib
        import sys
        import types
        from unittest.mock import patch

        class FakeStructuredTool:
            @staticmethod
            def from_function(**kwargs):
                return types.SimpleNamespace(**kwargs)

        tools_module = types.ModuleType("langchain_core.tools")
        tools_module.StructuredTool = FakeStructuredTool
        package = types.ModuleType("langchain_core")
        package.tools = tools_module
        with patch.dict(sys.modules, {"langchain_core": package, "langchain_core.tools": tools_module}):
            sys.modules.pop("app.tool_interceptor", None)
            interceptor = importlib.import_module("app.tool_interceptor")
            store = []
            write = FakeTool("add_transaction", store)
            write.description, write.args_schema, write.return_direct = "description", object(), False
            read = FakeTool("search_transaction", store)
            wrapped, unchanged = interceptor.interceptar_tools([write, read])
            self.assertIs(unchanged, read)
            self.assertIs(wrapped.args_schema, write.args_schema)
            self.assertEqual(wrapped.name, write.name)
            self.assertEqual(wrapped.func(value=1)["status"], "error")
            with holder_context() as holder:
                result = wrapped.func(value=1)
                self.assertEqual(result["status"], "prepared")
                self.assertEqual(store, [])
                holder.commit()
            self.assertEqual(store, [("add_transaction", {"value": 1})])
            sys.modules.pop("app.tool_interceptor", None)

if __name__ == "__main__":
    unittest.main()
