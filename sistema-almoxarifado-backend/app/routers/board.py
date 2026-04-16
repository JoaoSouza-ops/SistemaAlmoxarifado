# Arquivo: app/routers/board.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Importamos nossa conexão com o banco e nossos modelos/schemas
from app.database import get_db
from app.schemas.board import NotaBoard
from app.models.board import NotaBoardModel

router = APIRouter(
    prefix="/board",
    tags=["Board"]
)

# --- ROTA PARA CRIAR NOTA (POST) ---
# Adicionamos 'db: Session = Depends(get_db)' para o FastAPI injetar o banco aqui
@router.post("/notas", status_code=201)
def criar_nota(nota: NotaBoard, db: Session = Depends(get_db)):
    
    # 1. Transformamos o Schema (Pydantic) no Model (SQLAlchemy)
    nova_nota = NotaBoardModel(
        titulo=nota.titulo,
        descricao=nota.descricao,
        categoria=nota.categoria.value, # .value extrai a string do nosso Enum
        fixado=nota.fixado
    )
    
    # 2. Preparamos para salvar (Insert)
    db.add(nova_nota)
    
    # 3. Executamos a ação de fato no banco de dados
    db.commit()
    
    # 4. Atualizamos a variável com o 'id' que o banco acabou de gerar
    db.refresh(nova_nota)
    
    return nova_nota


# --- ROTA PARA LISTAR NOTAS (GET) ---
# Vamos criar essa rota nova para podermos ver o que foi salvo
@router.get("/notas")
def listar_notas(db: Session = Depends(get_db)):
    
    # Faz um SELECT * FROM notas_board;
    notas = db.query(NotaBoardModel).all()
    
    return notas