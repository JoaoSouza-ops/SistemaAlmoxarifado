# Arquivo: app/routers/transferencia.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db

from app.models.patrimonio import PatrimonioModel, HistoricoModel
from app.models.transferencia import TransferenciaModel
from app.schemas.transferencia import SolicitacaoTransferencia, AprovacaoTransferencia

router = APIRouter(prefix="/transferencias", tags=["Transferencias"])

# --- SOLICITAR TRANSFERÊNCIA ---
@router.post("/", status_code=201)
def solicitar_transferencia(solicitacao: SolicitacaoTransferencia, db: Session = Depends(get_db)):
    # 1. Achamos o patrimônio
    patrimonio = db.query(PatrimonioModel).filter(PatrimonioModel.numero == solicitacao.patrimonio_numero).first()
    
    if not patrimonio:
        raise HTTPException(status_code=404, detail="Patrimônio não encontrado")
    if patrimonio.status != "ATIVO":
        raise HTTPException(status_code=400, detail="Apenas patrimônios ATIVOS podem ser transferidos.")

    # 2. Bloqueamos o patrimônio para ele não sofrer baixa ou outra transferência junto
    patrimonio.status = "TRANSFERENCIA_PENDENTE"

    # 3. Criamos o registro na sala de espera
    nova_transferencia = TransferenciaModel(
        patrimonio_numero=patrimonio.numero,
        setor_origem=patrimonio.setor_atual,
        setor_destino=solicitacao.setor_destino,
        responsavel_recebimento=solicitacao.responsavel_recebimento,
        justificativa=solicitacao.justificativa
    )
    db.add(nova_transferencia)
    db.commit()
    db.refresh(nova_transferencia)
    
    return nova_transferencia


# --- APROVAR / REJEITAR TRANSFERÊNCIA ---
@router.post("/{id}/aprovacoes", status_code=200)
def processar_aprovacao(id: int, aprovacao: AprovacaoTransferencia, db: Session = Depends(get_db)):
    transferencia = db.query(TransferenciaModel).filter(TransferenciaModel.id == id).first()
    
    if not transferencia or transferencia.status != "PENDENTE":
        raise HTTPException(status_code=400, detail="Transferência não encontrada ou já processada.")

    patrimonio = db.query(PatrimonioModel).filter(PatrimonioModel.numero == transferencia.patrimonio_numero).first()

    # Se REJEITAR, destravamos o item e fim de papo
    if aprovacao.decisao == "REJEITADA":
        transferencia.status = "REJEITADA"
        patrimonio.status = "ATIVO" 
        db.commit()
        return {"mensagem": "Transferência rejeitada. O item foi destravado."}

    # Se APROVAR, validamos a regra de Override para Administrador Sênior
    if aprovacao.decisao == "APROVADA":
        if aprovacao.override_admin and not aprovacao.motivo_override:
            raise HTTPException(status_code=400, detail="Override Administrativo exige justificativa obrigatória.")

        # Atualizamos os status e movemos o item de setor
        transferencia.status = "APROVADA"
        patrimonio.status = "ATIVO"
        patrimonio.setor_atual = transferencia.setor_destino

        # REGISTRO DE AUDITORIA NO HISTÓRICO!
        acao_texto = "TRANSFERENCIA_FORCADA_ADMIN" if aprovacao.override_admin else "TRANSFERENCIA_APROVADA"
        
        novo_historico = HistoricoModel(
            patrimonio_numero=patrimonio.numero,
            acao=acao_texto,
            origem=transferencia.setor_origem,
            destino=transferencia.setor_destino
        )
        db.add(novo_historico)
        db.commit()
        
        return {"mensagem": "Transferência concluída e registrada no histórico!"}