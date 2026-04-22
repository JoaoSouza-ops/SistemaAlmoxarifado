# Arquivo: app/routers/transferencia.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db

from app.models.patrimonio import PatrimonioModel, HistoricoModel
from app.models.transferencia import TransferenciaModel
from app.schemas.transferencia import SolicitacaoTransferencia, AprovacaoTransferencia
from app.auth import verificar_permissao

router = APIRouter(prefix="/transferencias", tags=["Transferencias"])

PODE_OPERAR  = ["transferencia:write"]
PODE_APROVAR = ["transferencia:approve", "admin:override"]


def problem(status: int, title: str, detail: str, instance: str = None) -> JSONResponse:
    body = {"type": f"https://api.almoxarifado.gov.br/erros/{status}",
            "title": title, "status": status, "detail": detail}
    if instance:
        body["instance"] = instance
    return JSONResponse(status_code=status, media_type="application/problem+json", content=body)


# ─── POST /transferencias ─────────────────────────────────────────────────────
# CORREÇÃO: usa 'patrimonioId' (uuid) e 'setorDestino' (uuid) do contrato v2
@router.post("/", status_code=201)
def solicitar_transferencia(
    solicitacao: SolicitacaoTransferencia,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(PODE_OPERAR)),
):
    # patrimonioId no contrato é uuid do patrimônio — buscamos pelo campo 'numero'
    # que é o identificador natural do domínio. Ajuste conforme seu modelo de dados.
    patrimonio = db.query(PatrimonioModel).filter(
        PatrimonioModel.numero == solicitacao.patrimonio_id
    ).first()

    if not patrimonio:
        return problem(404, "Não encontrado", "Patrimônio não encontrado.",
                       instance=str(request.url))
    if patrimonio.status != "ATIVO":
        return problem(422, "Regra de negócio violada",
                       "Apenas patrimônios ATIVOS podem ser transferidos.",
                       instance=str(request.url))

    patrimonio.status = "TRANSFERENCIA_PENDENTE"

    nova_transferencia = TransferenciaModel(
        patrimonio_numero=patrimonio.numero,
        setor_origem=patrimonio.setor_atual,
        setor_destino=solicitacao.setor_destino,
        responsavel_recebimento=solicitacao.responsavel_recebimento,
        justificativa=solicitacao.justificativa,
    )
    db.add(nova_transferencia)
    db.commit()
    db.refresh(nova_transferencia)
    return nova_transferencia


# ─── POST /transferencias/{id}/aprovacoes ─────────────────────────────────────
# CORREÇÃO: usa 'overrideAdmin' e 'motivoOverride' (camelCase)
@router.post("/{id}/aprovacoes", status_code=200)
def processar_aprovacao(
    id: int,
    aprovacao: AprovacaoTransferencia,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(PODE_APROVAR)),
):
    transferencia = db.query(TransferenciaModel).filter(
        TransferenciaModel.id == id
    ).first()

    if not transferencia or transferencia.status != "PENDENTE":
        return problem(422, "Estado inválido",
                       "Transferência não encontrada ou já processada.",
                       instance=str(request.url))

    patrimonio = db.query(PatrimonioModel).filter(
        PatrimonioModel.numero == transferencia.patrimonio_numero
    ).first()

    if aprovacao.decisao == "REJEITADA":
        transferencia.status = "REJEITADA"
        patrimonio.status = "ATIVO"
        db.commit()
        return {"mensagem": "Transferência rejeitada. O item foi destravado."}

    # Aprovação — valida regra de override
    if aprovacao.override_admin and not aprovacao.motivo_override:
        return problem(422, "Regra de negócio violada",
                       "Override administrativo exige 'motivoOverride' (mínimo 15 caracteres).",
                       instance=str(request.url))

    transferencia.status = "APROVADA"
    patrimonio.status = "ATIVO"
    patrimonio.setor_atual = transferencia.setor_destino

    acao_texto = "TRANSFERENCIA_FORCADA_ADMIN" if aprovacao.override_admin else "TRANSFERENCIA_APROVADA"
    db.add(HistoricoModel(
        patrimonio_numero=patrimonio.numero,
        acao=acao_texto,
        origem=transferencia.setor_origem,
        destino=transferencia.setor_destino,
    ))
    db.commit()
    return {"mensagem": "Transferência concluída e registrada no histórico."}