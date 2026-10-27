# gemini-3-flash-preview
# gemini-2.5-flash
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnableConfig        
from app.tools.mongo import TOOLS_MEMORIA, TOOL_PERFIL                
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
import operator
import re
from typing import Annotated
from app.llms import llm_rapido, llm_especialista
from app.tools.financeiro import TOOLS
from langgraph.graph import StateGraph, END, START, MessagesState
from app.prompts import (
    ROUTER_PROMPT_COMPLETO,
    FINANCEIRO_PROMPT_COMPLETO,
    AGENDA_PROMPT_COMPLETO,
    ORQUESTRADOR_PROMPT_COMPLETO,
    FAQ_PROMPT
)
from app.tools.faq import faq_retriever
from app.guardrail import guardrail_entrada, guardrail_saida, anonimizar_entrada
from langchain_core.messages import RemoveMessage
from app.memory import iniciar_sessao, salvar_mensagem, encerrar_sessao, _sessoes_ativas
from app.tools.agenda import TOOLS_AGENDA
from app.tools.calendario_google import TOOLS_GOOGLE
from app.memory import salvar_mensagem
from app.observabilidade import abrir_turno, fechar_turno, status_do_estado
from app.juiz import no_juiz

router_memory = MemorySaver()

agenda_app = create_agent(
    model=llm_especialista,
    tools=TOOLS_AGENDA + TOOLS_GOOGLE + TOOLS_MEMORIA,
    system_prompt=AGENDA_PROMPT_COMPLETO,
)

router_app = create_agent(
    model=llm_rapido,
    system_prompt=ROUTER_PROMPT_COMPLETO,
    tools=TOOLS_MEMORIA,
    checkpointer=router_memory
)

financeiro_app = create_agent(
    model=llm_especialista,
    tools=TOOLS + TOOLS_MEMORIA + TOOL_PERFIL,
    system_prompt=FINANCEIRO_PROMPT_COMPLETO
)

orquestrador_app = create_agent(
    model=llm_rapido,
    system_prompt=ORQUESTRADOR_PROMPT_COMPLETO
)

faq_app = create_agent(
    model=llm_rapido,
    tools=[faq_retriever],
    system_prompt=FAQ_PROMPT
)

# ==============================================================================
# ESTADO
# ==============================================================================
class Estado(MessagesState):
    agentes_chamados:   Annotated[list[str], operator.add]   
    rota:               str                               
    mapa_pii:           dict[str, str]                         



def no_guardrail_entrada(estado: Estado) -> dict:
    mensagem_original = list(estado["messages"])[-1]
    
    texto_anonimizado, mapa = anonimizar_entrada(mensagem_original.text)

    resultado = guardrail_entrada(texto_anonimizado)

    if (resultado["bloqueado"]):
        return {
            "agentes_chamados": ["guardrail_entrada"],
            "rota":             "fim",
            "messages":         [{"role": "assistant", "content": resultado["mensagem"]}],
            "mapa_pii":         {}
        }
    
    # Esse remove vai pegar a lista de tuplas messages e excluir a passada e adicionar uma nova
    # porque se a pessoa passou algum dado pessoal isso vai pecorrer por todo sistema, então todos os 
    # agentes vão ter conciencia desses dados quebrando a ideia da anonomização
    return {
        "agentes_chamados": ["guardrail_entrada:aprovado"],
        "messages":         [RemoveMessage(id=mensagem_original.id), {"role": "human", "content": texto_anonimizado}],
        "mapa_pii":         mapa,
        "rota":             "roteador"
    }

def no_guardrail_saida(estado: Estado) -> dict:
    ultima_especialista = estado["messages"][-1].content

    resposta_revisada = guardrail_saida(ultima_especialista, estado["mapa_pii"])

    return {
        "agentes_chamados": ["guardrail_saida"],
        "messages":         [{"role": "assistant", "content": resposta_revisada["conteudo"]}],
    }

def no_roteador(estado: Estado, config: RunnableConfig) -> dict:
    saida = router_app.invoke({"messages": list(estado["messages"])}, config=config)
    texto = saida["messages"][-1].content

    # Aceita somente rotas conhecidas e uma linha de protocolo inteira. Se o
    # modelo produzir um protocolo inválido, encerra com uma resposta clara em
    # vez de deixar o grafo terminar sem mensagem para o usuário.
    correspondencia = re.search(
        r"(?im)^\s*ROUTE\s*=\s*(financeiro|agenda|faq)\s*$",
        texto,
    )
    if correspondencia:
        return {
            "agentes_chamados": ["roteador"],
            "rota":             correspondencia.group(1).lower(),
        }

    tem_protocolo_invalido = re.search(r"(?i)\bROUTE\s*=", texto)
    resposta_direta = (
        "Não consegui identificar para qual área encaminhar sua pergunta. "
        "Você pode reformulá-la?"
        if tem_protocolo_invalido or not texto.strip()
        else texto.strip()
    )

    return {
        "agentes_chamados": ["roteador"],
        "rota":             "fim",
        "messages":         [{"role": "assistant", "content": resposta_direta}],
    }

# ── Orquestrador (wrapper) ─────────────────────────────────────────────
# Pega a última resposta do especialista para formatar

def no_orquestrador(estado: Estado, config: RunnableConfig) -> dict:
    ultima_especialista = estado["messages"][-1].content

    saida = orquestrador_app.invoke({
        "messages": [{"role": "human", "content": ultima_especialista}]
    }, config=config)
    return {
        "agentes_chamados": [estado["rota"], "orquestrador"],
        "messages":         [{"role": "assistant", "content": saida["messages"][-1].content}],
    }

# ── Grafo ──────────────────────────────────────────────────────────────

grafo = StateGraph(Estado)

grafo.add_edge(START, "guardrail_entrada")  

def decidir_rota(estado):
    return estado["rota"] if estado["rota"] in ("financeiro", "agenda", "faq") else "fim"

def decidir_pos_guardrail_entrada(estado):
    return estado["rota"]

grafo.add_conditional_edges(
    "roteador",
    decidir_rota,
    {
        "financeiro": "financeiro",
        "agenda": "agenda",
        "faq": "faq",
        "fim": END,
    }
)

grafo.add_conditional_edges(
    "guardrail_entrada", 
    decidir_pos_guardrail_entrada,
    {
        "roteador": "roteador",
        "fim": END
    }
)

grafo.add_node("guardrail_entrada", no_guardrail_entrada)
grafo.add_node("roteador",     no_roteador)
grafo.add_node("financeiro",   financeiro_app)   
grafo.add_node("agenda",       agenda_app)      
grafo.add_node("faq",          faq_app)           
grafo.add_node("orquestrador", no_orquestrador)
grafo.add_node("guardrail_saida", no_guardrail_saida)
grafo.add_node("juiz", no_juiz)

grafo.add_edge("financeiro",      "orquestrador")
grafo.add_edge("agenda",          "orquestrador")
grafo.add_edge("orquestrador",    "guardrail_saida")
grafo.add_edge("guardrail_saida", "juiz")
grafo.add_edge("faq",             "juiz") 
grafo.add_edge("juiz",            END)

memory = MemorySaver() 
fluxo_agentes = grafo.compile(checkpointer=memory)


# ==============================================================================
# FLUXO PRINCIPAL
# ==============================================================================
def executar_fluxo_assessor(
    pergunta_usuario: str, session_id: str, user_id: str = "usuario_teste"
) -> str:
    pergunta_usuario_anonimizado, _ = anonimizar_entrada(pergunta_usuario)
    estado_inicial = {
        "messages":         [{"role": "human", "content": pergunta_usuario}],
        "agentes_chamados": [],
        "rota":             "",
        "mapa_pii":         {},
        "session_id":       session_id,
    }
    turno_id = abrir_turno()

    status = "erro"
    rota = ""
    try:
        estado_final = fluxo_agentes.invoke(
            estado_inicial,
            config={"configurable": {"thread_id": session_id, "user_id": user_id}},
        )

        resposta = estado_final["messages"][-1].text

        salvar_mensagem(session_id, "human",     pergunta_usuario_anonimizado, user_id=user_id)
        salvar_mensagem(session_id, "assistant", resposta, user_id=user_id)

        status = status_do_estado(estado_final)
        rota = estado_final.get("rota") or ""
        return resposta
    finally:
        fechar_turno(turno_id, session_id=session_id, rota=rota, status=status)
