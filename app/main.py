from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import validar_config
from fastapi.middleware.cors import CORSMiddleware
from app.config import BASE_DIR, FRONTEND_DIR
from app.routes import chat, session, perfil, monitor

# python -m uvicorn app.main:app --reload
 
for _problema in validar_config():       
    print(f"[config] ATENÇÃO: {_problema}")
 
app = FastAPI( 
    title="Assessor IA ", 
    description="Assessor financeiro e de agenda com LangChain e LangGraph",
    version="0.1.0",
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
@app.get("/health")
def health() -> dict:
    problemas = validar_config()
   
    return {
        "status": "ok" if not problemas else "atencao",
        "problemas_de_configuracao": problemas,
    }
 
app.include_router(chat.router)
app.include_router(session.router)
app.include_router(perfil.router)
app.include_router(monitor.router)

# A biblioteca que formata as respostas Markdown é uma dependência local do
# projeto. Servi-la daqui evita depender de uma CDN no navegador.
MARKDOWN_LIB_DIR = BASE_DIR / "node_modules" / "marked" / "lib"
if MARKDOWN_LIB_DIR.exists():
    app.mount("/vendor", StaticFiles(directory=MARKDOWN_LIB_DIR), name="vendor")
 
if (FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/", tags=["infra"])
    def raiz() -> dict:
        return {
            "mensagem": "API do Assessor no ar. O frontend ainda não foi criado",
        }
