from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """O que o navegador envia no POST /chat."""

    session_id: str = Field(
        ...,
        description="Identifica a conversa (UUID gerado pelo front a cada sessão).",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    user_id: str = Field(
        default="usuario_teste",
        description="Identifica o usuário de forma estável entre sessões. "
                    "É o que permite a memória de longo prazo funcionar.",
        examples=["usuario_teste"],
    )
    pergunta: str = Field(
        ...,
        min_length=1,
        description="A mensagem do usuário — o que antes vinha do input().",
        examples=["gastei 50 reais no mercado hoje"],
    )

class ChatResponse(BaseModel) :
    resposta : str 

class SessionResponse(BaseModel) :
    session_id : str 
    resumo : str | None = None

class PerfilRequest(BaseModel):
    """O que o navegador envia no POST /chat."""
    user_id: str = Field(
        default="usuario_teste",
        description="Identifica o usuário de forma estável entre sessões. "
                    "É o que permite a memória de longo prazo funcionar.",
        examples=["usuario_teste"],
    )
    renda_mensal: float = Field(
        ...,
        description="Qual a renda mensal do usuário",
        examples=[6000],
        gt=0
    )
    gasto_fixo_mensal: float = Field(
        ...,
        description="O quanto da verba é destinado a gastos mensais fixos",
        examples=[3800],
        ge=0
    )
    horizonte_meses: int = Field(
        description="Margem de tempo para investimento.",
        examples=[18],
        gt=0,
        lt=120
    )
    perfil_investidor: str = Field(
        description="Como o usuário considera riscos para investimento.",
        examples=["conservador/moderado/arrojado"],
    )

    restricoes: str = Field(
        description="Frases do usuário que indicam como ele gosta de lidar com suas finanças.",
        examples=["não quero nada muito arriscado, prefiro dormir tranquilo",
    "preciso deixar uma reserva para consertar o carro",
    "quero trocar de apartamento no meio do ano que vem"],
    )


