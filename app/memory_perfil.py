"""
Memory de Perfil - Indexação estruturada em MongoDB + Qdrant
Cada restrição é indexada individualmente para busca semântica.
"""

import uuid
from datetime import datetime, timezone
from app.llms import llm_rapido
from app.config import MONGODB_URI
from pymongo import MongoClient
from qdrant_client import models
from app.vectorstore import qdrant, gerar_embedding, COLLECTION_PERFIL

# ==============================================================================
# CONEXÃO
# ==============================================================================

_mongo      = MongoClient(MONGODB_URI)
db          = _mongo["assessor"]
col_perfil = db["perfil"]

# Índices
col_perfil.create_index("user_id")
col_perfil.create_index([("user_id", 1), ("criado_em", -1)])

# ==============================================================================
# SALVAR PERFIL - GRAVA MONGO + INDEXA QDRANT
# ==============================================================================

def salvar_perfil(
    user_id: str, 
    renda_mensal: float, 
    gasto_fixo_mensal: float, 
    horizonte_meses: float, 
    perfil_investidor: str, 
    restricoes: list[str]
) -> str:
    """
    Salva perfil no MongoDB e indexa cada restrição no Qdrant individualmente.
    Retorna o _id do documento criado.
    """
    doc_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)

    col_perfil.insert_one({
        "_id": doc_id,
        "user_id": user_id,
        "renda_mensal": renda_mensal,
        "gasto_fixo_mensal": gasto_fixo_mensal,
        "horizonte_meses": horizonte_meses,
        "perfil_investidor": perfil_investidor,
        "restricoes": restricoes,
        "criado_em": agora,
        "atualizado_em": agora,
    })

    _indexar_restricoes_qdrant(doc_id, user_id, restricoes)

    return doc_id


def _indexar_restricoes_qdrant(
    doc_id: str, 
    user_id: str, 
    restricoes: list[str]
) -> None:
    """
    Indexa cada restrição como um ponto separado no Qdrant.
    Isso permite busca semântica individual por cada restrição.
    """
    points = []

    for idx, restricao in enumerate(restricoes):
        restricao_id = hash(f"{doc_id}_{idx}") % (10**9)  

        vetor = gerar_embedding(restricao)

        # Criar ponto no Qdrant
        point = models.PointStruct(
            id=restricao_id,
            vector=vetor,
            payload={
                "doc_id": doc_id,
                "user_id": user_id,
                "restricao": restricao,  
                "indice_restricao": idx,
                "tipo": "restricao",
            },
        )
        points.append(point)

    if points:
        qdrant.upsert(
            collection_name=COLLECTION_PERFIL,
            points=points,
        )

# ==============================================================================
# RECUPERAR PERFIL
# ==============================================================================

def carregar_perfil(user_id: str) -> dict | None:
    """Carrega o perfil mais recente do usuário."""
    return col_perfil.find_one(
        {"user_id": user_id},
        sort=[("criado_em", -1)] 
    )


def buscar_restricoes_similares(query: str, user_id: str, top_k: int = 3) -> list[dict]:
    """
    Busca restrições similares por semântica.
    Cada restrição é encontrada individualmente.
    """
    vetor_query = gerar_embedding(query)

    resultados = qdrant.search(
        collection_name=COLLECTION_PERFIL,
        query_vector=vetor_query,
        query_filter=models.Filter(
            must=[
                models.HasIdCondition(
                    has_id=[user_id]
                )
            ]
        ),
        limit=top_k,
    )

    return [
        {
            "restricao": hit.payload["restricao"],
            "score": hit.score,
            "doc_id": hit.payload["doc_id"],
        }
        for hit in resultados
    ]