from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.patrimonio import PatrimonioModel
from app.models.transferencia import TransferenciaModel
from app.models.board import NotaBoardModel as NotaBoard
from app.auth import verificar_permissao
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metricas")
def obter_metricas(db: Session = Depends(get_db), usuario=Depends(verificar_permissao(["patrimonio:read"]))):
    # Conta patrimônios por status
    ativos = db.query(func.count(PatrimonioModel.numero)).filter(PatrimonioModel.status == "ATIVO").scalar()
    baixados = db.query(func.count(PatrimonioModel.numero)).filter(PatrimonioModel.status == "BAIXADO").scalar()
    
    # Conta transferências pendentes
    transferencias_pendentes = db.query(func.count(TransferenciaModel.id)).filter(TransferenciaModel.status == "PENDENTE").scalar()
    
    # Conta notas do board
    notas = db.query(func.count(NotaBoard.id)).scalar()

    return {
        "patrimonios_ativos": ativos or 0,
        "patrimonios_baixados": baixados or 0,
        "transferencias_pendentes": transferencias_pendentes or 0,
        "notas_board": notas or 0
    }