from fastapi import APIRouter
from app.schemas import PerfilRequest
from app.memory_perfil import salvar_perfil

router = APIRouter(tags=["chat"])

@router.post("/perfil", response_model=PerfilRequest)
def cadastrar_perfil(requisicao: PerfilRequest) -> PerfilRequest:
    """Formulário para persistência de perfil do usuário"""
    salvar_perfil(
        requisicao.user_id,
        requisicao.renda_mensal, 
        requisicao.gasto_fixo_mensal, 
        requisicao.horizonte_meses, 
        requisicao.perfil_investidor, 
        requisicao.restricoes
    )
