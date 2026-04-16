# Arquivo: app/routers/patrimonio.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.patrimonio import PatrimonioCriar, PatrimonioDetalhe, SolicitacaoBaixa

from app.models.patrimonio import PatrimonioModel, HistoricoModel
router = APIRouter(
    prefix="/patrimonios",
    tags=["Patrimonios"]
)

# --- CADASTRAR PATRIMÔNIO ---
@router.post("/", status_code=201, response_model=PatrimonioDetalhe)
def cadastrar_patrimonio(patrimonio: PatrimonioCriar, db: Session = Depends(get_db)):
    
    # 1. Verifica se o número já existe no banco
    item_existente = db.query(PatrimonioModel).filter(PatrimonioModel.numero == patrimonio.numero).first()
    if item_existente:
        raise HTTPException(status_code=400, detail="Este número de patrimônio já está cadastrado.")

    # 2. Cria o patrimônio principal
    novo_patrimonio = PatrimonioModel(
        numero=patrimonio.numero,
        descricao=patrimonio.descricao,
        setor_atual=patrimonio.setor_atual
    )
    db.add(novo_patrimonio)

    # 3. Cria a trilha de auditoria inicial (Obrigatório para GovTech)
    historico_inicial = HistoricoModel(
        patrimonio_numero=patrimonio.numero,
        acao="CADASTRO_INICIAL",
        destino=patrimonio.setor_atual
    )
    db.add(historico_inicial)
    
    # Salva as duas tabelas ao mesmo tempo no banco
    db.commit()
    db.refresh(novo_patrimonio)
    
    return novo_patrimonio

# --- BUSCAR PATRIMÔNIO (COM HISTÓRICO) ---
@router.get("/{numero}", response_model=PatrimonioDetalhe)
def buscar_patrimonio(numero: str, db: Session = Depends(get_db)):
    # Faz o SELECT e automaticamente traz o relacionamento de histórico
    patrimonio = db.query(PatrimonioModel).filter(PatrimonioModel.numero == numero).first()
    
    if not patrimonio:
        raise HTTPException(status_code=404, detail="Patrimônio não encontrado.")
        
    return patrimonio

# --- REALIZAR BAIXA PATRIMONIAL ---
@router.post("/{numero}/baixas", status_code=200)
def realizar_baixa(numero: str, baixa: SolicitacaoBaixa, db: Session = Depends(get_db)):
    
    # 1. Busca o patrimônio no banco
    patrimonio = db.query(PatrimonioModel).filter(PatrimonioModel.numero == numero).first()
    
    # 2. Validações de negócio
    if not patrimonio:
        raise HTTPException(status_code=404, detail="Patrimônio não encontrado.")
    
    if patrimonio.status == "BAIXADO":
        raise HTTPException(status_code=400, detail="Este patrimônio já foi baixado anteriormente.")

    # 3. Atualiza o status do item principal
    patrimonio.status = "BAIXADO"
    
    # 4. Registra a trilha de auditoria
    nova_acao = HistoricoModel(
        patrimonio_numero=patrimonio.numero,
        acao="BAIXA",
        origem=patrimonio.setor_atual,
        destino="DESCARTE/ARQUIVO",
        # Podemos usar o destino ou um campo de observação para guardar a justificativa
    )
    db.add(nova_acao)
    
    # 5. Salva a transação completa
    db.commit()
    db.refresh(patrimonio)
    
    return {"mensagem": f"Patrimônio {numero} baixado com sucesso.", "justificativa": baixa.justificativa}