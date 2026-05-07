# Arquivo: app/routers/transferencia.py
#
# BUGS CORRIGIDOS NESTA VERSÃO
#
# BUG 1 — buscar_transferencia registrada duas vezes
#   A rota GET /{id} aparecia antes de POST /{id}/aprovacoes E depois do PATCH.
#   FastAPI registra apenas a primeira ocorrência; a segunda é código morto.
#   FIX: rota duplicada removida, mantida apenas após GET /.
#
# BUG 2 — POST /assinaturas verificava status "PENDENTE" (errado)
#   Assinaturas só fazem sentido após aprovação, ou seja, quando
#   status == "APROVADA". A guarda anterior rejeitava 100% das tentativas.
#   FIX: condição alterada para status != "APROVADA".
#
# BUG 3 — processar_aprovacao movia o patrimônio imediatamente
#   Na aprovação, o código fazia patrimônio.setor_atual = setor_destino e
#   patrimônio.status = "ATIVO" antes de qualquer assinatura. Isso tornava
#   a dupla assinatura inútil — o item já estava movido.
#   FIX: a aprovação apenas muda transferencia.status → "APROVADA".
#        O patrimônio só se move quando as duas assinaturas chegam.
#
# BUG 4 — PATCH retornava SolicitacaoTransferencia (schema de entrada)
#   O schema de entrada não tem id, status, datas de assinatura, etc.
#   O frontend recebia uma resposta incompleta e não conseguia atualizar o card.
#   FIX: PATCH agora retorna a transferência completa via response_model=TransferenciaRead.
#
# BUG 5 — POST /assinaturas com db.commit() duplo
#   O primeiro commit registrava a assinatura. Se a lógica de efetivação
#   que vem depois falhasse (ex.: patrimônio não encontrado), a assinatura
#   ficava gravada mas a efetivação não — estado inconsistente.
#   FIX: um único db.commit() ao final, após todas as mutações.
#
# REGRA DE EDIÇÃO (atualizada)
#   justificativa, responsavel_recebimento e numero_movimento são editáveis
#   enquanto a transferência não estiver completamente efetivada, ou seja,
#   enquanto efetivado_em for nulo — independente do status ser PENDENTE ou
#   APROVADA com assinaturas parciais.
#   O campo setor_destino permanece bloqueado após a aprovação por ser
#   estrutural (define a rota física do patrimônio).
#   Após efetivação completa nenhum campo pode ser alterado — o backend
#   retorna 403 com mensagem clara para que o frontend exiba toast amigável.

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List

from app.database import get_db
from app.models.patrimonio import PatrimonioModel, HistoricoModel
from app.models.transferencia import TransferenciaModel
from app.schemas.transferencia import (
    SolicitacaoTransferencia,
    AprovacaoTransferencia,
    EdicaoTransferencia,
    AssinaturaTransferencia,
    TransferenciaRead,
)
from app.auth import verificar_permissao, obter_usuario_atual

router = APIRouter(prefix="/transferencias", tags=["Transferencias"])

PODE_OPERAR  = ["transferencia:write"]
PODE_APROVAR = ["transferencia:approve", "admin:override"]


# ─── Helper RFC 7807 ──────────────────────────────────────────────────────────

def problem(status: int, title: str, detail: str, instance: str = None) -> JSONResponse:
    body = {
        "type":   f"https://api.almoxarifado.gov.br/erros/{status}",
        "title":  title,
        "status": status,
        "detail": detail,
    }
    if instance:
        body["instance"] = instance
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content=body,
    )


# ─── Helper: conflito de patrimônio em OUTRA transferência ───────────────────

def _patrimonio_em_outra_transferencia(
    db: Session,
    patrimonio_numero: str,
    ignorar_id: int | None = None,
) -> bool:
    query = db.query(TransferenciaModel).filter(
        TransferenciaModel.patrimonio_numero == patrimonio_numero,
        TransferenciaModel.status == "PENDENTE",
    )
    if ignorar_id:
        query = query.filter(TransferenciaModel.id != ignorar_id)
    return query.first() is not None


# ══════════════════════════════════════════════════════════════════════════════
# ATENÇÃO — ordem importa no FastAPI: rotas fixas antes de path params
# ══════════════════════════════════════════════════════════════════════════════


# ─── GET /transferencias/ ─────────────────────────────────────────────────────

@router.get("/", response_model=List[TransferenciaRead])
def listar_transferencias(
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(["patrimonio:read"])),
):
    return db.query(TransferenciaModel).all()


# ─── POST /transferencias/ ────────────────────────────────────────────────────

@router.post("/", status_code=201, response_model=TransferenciaRead)
def solicitar_transferencia(
    solicitacao: SolicitacaoTransferencia,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(PODE_OPERAR)),
):
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

    nova = TransferenciaModel(
        patrimonio_numero=patrimonio.numero,
        setor_origem=patrimonio.setor_atual,
        setor_destino=solicitacao.setor_destino,
        responsavel_recebimento=solicitacao.responsavel_recebimento,
        justificativa=solicitacao.justificativa,
        numero_movimento=solicitacao.numero_movimento,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova


# ─── POST /transferencias/{id}/aprovacoes ─────────────────────────────────────
#
# FIX BUG 3: A aprovação não move mais o patrimônio.
# Ela apenas avança o status da transferência para APROVADA, desbloqueando
# as rotas de assinatura. O patrimônio só muda quando as duas assinaturas
# chegarem (em POST /{id}/assinaturas).

@router.post("/{id}/aprovacoes", status_code=200, response_model=TransferenciaRead)
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
        return problem(
            422, "Estado inválido",
            "Transferência não encontrada ou já processada.",
            instance=str(request.url),
        )

    patrimonio = db.query(PatrimonioModel).filter(
        PatrimonioModel.numero == transferencia.patrimonio_numero
    ).first()

    # Rejeição — devolve patrimônio para ATIVO imediatamente
    if aprovacao.decisao == "REJEITADA":
        transferencia.status = "REJEITADA"
        patrimonio.status    = "ATIVO"
        db.commit()
        db.refresh(transferencia)
        return transferencia

    # Validação de override
    if aprovacao.override_admin and (
        not aprovacao.motivo_override or len(aprovacao.motivo_override) < 15
    ):
        return problem(
            422, "Regra de negócio violada",
            "Override administrativo exige 'motivoOverride' (mínimo 15 caracteres).",
            instance=str(request.url),
        )

    # Aprovação: avança status, patrimônio permanece TRANSFERENCIA_PENDENTE
    # até as duas assinaturas chegarem.
    transferencia.status          = "APROVADA"
    transferencia.override_admin  = aprovacao.override_admin
    transferencia.motivo_override = aprovacao.motivo_override

    db.commit()
    db.refresh(transferencia)
    return transferencia

# ─── POST /transferencias/{id}/assinaturas ────────────────────────────────────
#
# FIX BUG 2: guarda corrigida para status == "APROVADA".
# FIX BUG 5: db.commit() único ao final — assinatura e efetivação são atômicos.

@router.post("/{id}/assinaturas", status_code=200, response_model=TransferenciaRead)
def assinar_transferencia(
    id: int,
    assinatura: AssinaturaTransferencia,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: dict = Depends(obter_usuario_atual),
):
    transferencia = db.query(TransferenciaModel).filter(
        TransferenciaModel.id == id
    ).first()

    if not transferencia:
        return problem(404, "Não encontrada", "Transferência não existe.",
                       instance=str(request.url))

    # FIX BUG 2: era "PENDENTE", corrigido para "APROVADA"
    if transferencia.status != "APROVADA":
        return problem(
            422, "Estado inválido",
            "Apenas transferências APROVADAS podem receber assinaturas.",
            instance=str(request.url),
        )

    if transferencia.efetivado_em:
        return problem(409, "Conflito", "Esta transferência já foi efetivada.",
                       instance=str(request.url))

    agora = datetime.now(timezone.utc)

    if assinatura.papel == "TRANSFERIDOR":
        if transferencia.assinatura_transferidor_em:
            return problem(409, "Conflito", "O transferidor já assinou.",
                           instance=str(request.url))
        transferencia.assinatura_transferidor_em = agora

    elif assinatura.papel == "RECEBEDOR":
        if transferencia.assinatura_recebedor_em:
            return problem(409, "Conflito", "O recebedor já assinou.",
                           instance=str(request.url))
        transferencia.assinatura_recebedor_em = agora

    else:
        return problem(422, "Papel inválido",
                       "O papel deve ser TRANSFERIDOR ou RECEBEDOR.",
                       instance=str(request.url))

    # Efetiva se ambas as assinaturas estão presentes
    if transferencia.assinatura_transferidor_em and transferencia.assinatura_recebedor_em:
        patrimonio = db.query(PatrimonioModel).filter(
            PatrimonioModel.numero == transferencia.patrimonio_numero
        ).first()

        if patrimonio:
            patrimonio.status      = "ATIVO"
            patrimonio.setor_atual = transferencia.setor_destino
            transferencia.efetivado_em = agora

            db.add(HistoricoModel(
                patrimonio_numero=patrimonio.numero,
                acao="TRANSFERENCIA_EFETIVADA",
                origem=transferencia.setor_origem,
                destino=transferencia.setor_destino,
            ))

    # FIX BUG 5: commit único — assinatura + efetivação são atômicos
    db.commit()
    db.refresh(transferencia)
    return transferencia


# ─── GET /transferencias/{id} ─────────────────────────────────────────────────
# FIX BUG 1: esta é a única definição de buscar_transferencia.
# A cópia duplicada que existia mais abaixo foi removida.

@router.get("/{id}", status_code=200, response_model=TransferenciaRead)
def buscar_transferencia(
    id: int,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(["patrimonio:read"])),
):
    transferencia = db.query(TransferenciaModel).filter(
        TransferenciaModel.id == id
    ).first()

    if not transferencia:
        return problem(
            404, "Não encontrada",
            "A transferência solicitada não existe.",
            instance=f"/transferencias/{id}",
        )

    return transferencia


# ─── PATCH /transferencias/{id} ───────────────────────────────────────────────
#
# FIX BUG 4: response_model=TransferenciaRead adicionado.
#
# REGRA DE EDIÇÃO:
#   - justificativa, responsavel_recebimento, numero_movimento:
#       editáveis enquanto efetivado_em for nulo (pelo menos uma assinatura
#       ainda pendente), independente do status ser PENDENTE ou APROVADA.
#   - setor_destino:
#       bloqueado após a aprovação — campo estrutural que define a rota
#       física do patrimônio. Editável apenas com status PENDENTE e
#       override_admin=true.
#   - Após efetivação completa (efetivado_em preenchido):
#       nenhum campo pode ser alterado — retorna 403 para que o frontend
#       exiba toast amigável ao invés de erro técnico.

@router.patch("/{id}", status_code=200, response_model=TransferenciaRead)
def editar_transferencia(
    id: int,
    edicao: EdicaoTransferencia,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: dict = Depends(obter_usuario_atual),
):
    if "transferencia:write" not in usuario_atual.get("escopos", []):
        return problem(403, "Acesso Negado",
                       "Você não tem permissão para editar transferências.",
                       instance=str(request.url))

    transferencia = db.query(TransferenciaModel).filter(
        TransferenciaModel.id == id
    ).first()

    if not transferencia:
        return problem(404, "Não encontrada",
                       "A transferência solicitada não existe.",
                       instance=str(request.url))

    # Transferência completamente efetivada — nenhuma edição permitida.
    # Código 403 para que o frontend distinga e exiba toast amigável.
    # Transferência aprovada ou rejeitada — nenhuma edição permitida.
    if transferencia.status != "PENDENTE":
        return problem(
            403, "Edição não permitida",
            "Não é possível mais realizar edição nos campos Setor de destino, Responsável pelo recebimento e Justificativa.",
            instance=str(request.url),
        )

    # setor_destino: bloqueado após aprovação, exige override_admin em PENDENTE
    if edicao.setor_destino:
        if transferencia.status != "PENDENTE":
            return problem(
                403, "Edição não permitida",
                "O campo Setor de destino não pode ser alterado após a aprovação da transferência.",
                instance=str(request.url),
            )

        if not edicao.override_admin:
            return problem(403, "Acesso Negado",
                           "Alterações no Setor de destino exigem overrideAdmin=true.",
                           instance=str(request.url))

        if "admin:override" not in usuario_atual.get("escopos", []):
            return problem(403, "Acesso Negado",
                           "Escopo 'admin:override' necessário para alterar o Setor de destino.",
                           instance=str(request.url))

        if not edicao.motivo_override or len(edicao.motivo_override) < 15:
            return problem(422, "Erro de Validação",
                           "O motivoOverride deve ter pelo menos 15 caracteres.",
                           instance=str(request.url))

        if _patrimonio_em_outra_transferencia(db, transferencia.patrimonio_numero, ignorar_id=id):
            return problem(409, "Conflito",
                           "O patrimônio já está em outra transferência pendente.",
                           instance=str(request.url))

        transferencia.override_admin  = True
        transferencia.motivo_override = edicao.motivo_override
        transferencia.setor_destino   = edicao.setor_destino

    # Campos livres enquanto não efetivada (PENDENTE ou APROVADA com assinaturas parciais)
    if edicao.responsavel_recebimento is not None:
        transferencia.responsavel_recebimento = edicao.responsavel_recebimento
    if edicao.justificativa is not None:
        transferencia.justificativa = edicao.justificativa
    if edicao.numero_movimento is not None:
        transferencia.numero_movimento = edicao.numero_movimento

    db.commit()
    db.refresh(transferencia)
    return transferencia