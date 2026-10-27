"""Servidor MCP das ferramentas financeiras do Assessor."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from app.tools.financeiro import add_transaction as _add_transaction, saldo_diario as _saldo_diario, saldo_total as _saldo_total, search_transactions as _search_transactions, update_transaction as _update_transaction

mcp = FastMCP("assessor-financeiro", instructions="Servidor MCP financeiro do Assessor; use leitura antes de escrita quando precisar confirmar registros.")
LEITURA = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
ESCRITA = ToolAnnotations(readOnlyHint=False, destructiveHint=False)

@mcp.tool(name="saldo_total", description="Retorna o saldo de todo o histórico: receitas menos despesas.", annotations=LEITURA)
def saldo_total() -> dict[str, Any]:
    return _saldo_total.invoke({})

@mcp.tool(name="saldo_diario", description="Retorna o saldo de um dia local YYYY-MM-DD em America/Sao_Paulo.", annotations=LEITURA)
def saldo_diario(dia_informado: str) -> dict[str, Any]:
    return _saldo_diario.invoke({"dia_informado": dia_informado})

@mcp.tool(name="search_transaction", description="Consulta transações por texto e/ou intervalo de datas locais.", annotations=LEITURA)
def search_transaction(
    texto: Optional[str] = None, 
    inicio_intervalo: Optional[str] = None, 
    fim_intervalo: Optional[str] = None) -> dict[str, Any]:

    return _search_transactions.invoke({
        "texto": texto, 
        "inicio_intervalo": inicio_intervalo, 
        "fim_intervalo": fim_intervalo
    })


@mcp.tool(name="add_transaction", description="Registra uma nova transação na tabela transactions.", annotations=ESCRITA)
def add_transaction(
    amount: float, 
    source_text: str, 
    type_id: Optional[int] = None, 
    type_name: Optional[str] = None, 
    category_id: Optional[int] = None, 
    category_name: Optional[str] = None, 
    description: Optional[str] = None, 
    payment_method: Optional[str] = None, 
    occurred_at: Optional[str] = None) -> dict[str, Any]:
    
    return _add_transaction.invoke({
        "amount": amount, 
        "source_text": source_text, 
        "type_id": type_id, 
        "type_name": type_name, 
        "category_id": category_id, 
        "category_name": category_name, 
        "description": description, 
        "payment_method": payment_method,
        "occurred_at": occurred_at
    })


@mcp.tool(name="update_transaction", description="Atualiza uma transação por id ou por match_text + date_local.", annotations=ESCRITA)
def update_transaction(
    id: Optional[int] = None, 
    match_text: Optional[str] = None, 
    date_local: Optional[str] = None, 
    amount: Optional[float] = None, 
    type_id: Optional[int] = None, 
    type_name: Optional[str] = None, 
    category_id: Optional[int] = None, 
    category_name: Optional[str] = None, 
    description: Optional[str] = None, 
    payment_method: Optional[str] = None,
    occurred_at: Optional[str] = None) -> dict[str, Any]:

    return _update_transaction.invoke({
        "id": id, 
        "match_text": match_text, 
        "date_local": date_local, 
        "amount": amount, 
        "type_id": type_id, 
        "type_name": type_name, 
        "category_id": category_id, 
        "category_name": category_name, 
        "description": description, 
        "payment_method": payment_method, 
        "occurred_at": occurred_at
    })


if __name__ == "__main__":
    from app.config import DATABASE_URL
    if not DATABASE_URL:
        print("[assessor-financeiro] DATABASE_URL ausente no .env", file=sys.stderr)
    mcp.run(transport="stdio")
