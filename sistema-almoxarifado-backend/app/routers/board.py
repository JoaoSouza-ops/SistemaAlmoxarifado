# Arquivo: app/routers/board.py
from fastapi import APIRouter, Depends, HTTPException
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

# ─── ROTA PARA EDITAR NOTA (PUT) ─────────────────────────────────────────────
@router.put("/notas/{nota_id}", status_code=200)
def editar_nota(nota_id: int, nota: NotaBoard, db: Session = Depends(get_db)):
    """Atualiza os campos de uma nota existente pelo ID."""
    
    # 1. Busca a nota no banco. Se não achar, retorna 404.
    nota_existente = db.query(NotaBoardModel).filter(NotaBoardModel.id == nota_id).first()
    if not nota_existente:
        raise HTTPException(status_code=404, detail=f"Nota {nota_id} não encontrada.")
    
    # 2. Atualiza os campos com os valores recebidos
    nota_existente.titulo    = nota.titulo
    nota_existente.descricao = nota.descricao
    nota_existente.categoria = nota.categoria.value
    nota_existente.fixado    = nota.fixado
    
    # 3. Salva no banco e retorna o objeto atualizado
    db.commit()
    db.refresh(nota_existente)
    return nota_existente


# ─── ROTA PARA EXCLUIR NOTA (DELETE) ─────────────────────────────────────────
@router.delete("/notas/{nota_id}", status_code=204)
def excluir_nota(nota_id: int, db: Session = Depends(get_db)):
    """Remove uma nota pelo ID. Retorna 204 (sem conteúdo) em caso de sucesso."""
    
    nota_existente = db.query(NotaBoardModel).filter(NotaBoardModel.id == nota_id).first()
    if not nota_existente:
        raise HTTPException(status_code=404, detail=f"Nota {nota_id} não encontrada.")
    
    db.delete(nota_existente)
    db.commit()
    # Retorno vazio — status 204 não tem body
    return