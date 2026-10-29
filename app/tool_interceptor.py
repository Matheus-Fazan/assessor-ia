"""Intercepção das tools de escrita usadas pelos agentes."""
from langchain_core.tools import StructuredTool
from app.tool_holder import current_holder

WRITE_TOOLS = {"add_transaction", "update_transaction", "add_event", "add_google_event"}


def interceptar_tools(tools):
    def envolver(original):
        def preparar(**kwargs):
            holder = current_holder()
            if holder is None:
                return {"status": "error", "message": "Escrita bloqueada: contexto do turno ausente."}
            operation = holder.prepare(original, kwargs)
            return {
                "status": "prepared",
                "operation_id": operation.operation_id,
                "tool": operation.tool_name,
                "arguments": operation.arguments,
                "message": "Operação preparada, ainda não executada. Aguarda o juiz.",
            }
        return StructuredTool.from_function(
            func=preparar, name=original.name, description=original.description,
            args_schema=original.args_schema, return_direct=original.return_direct,
        )
    return [envolver(tool) if tool.name in WRITE_TOOLS else tool for tool in tools]
