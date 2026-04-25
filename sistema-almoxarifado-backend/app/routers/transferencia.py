# Arquivo: app/routers/transferencia.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db

from app.models.patrimonio import PatrimonioModel, HistoricoModel
from app.models.transferencia import TransferenciaModel
from app.schemas.transferencia import SolicitacaoTransferencia, AprovacaoTransferencia, SolicitacaoTransferencia, AprovacaoTransferencia, EdicaoTransferencia
from app.auth import verificar_permissao, obter_usuario_atual

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

# ─── GET /transferencias/{id} ─────────────────────────────────────────────────
@router.get("/{id}", status_code=200)
def buscar_transferencia(
    id: int, 
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(["patrimonio:read"]))
    
    ):


    transferencia = db.query(TransferenciaModel).filter(TransferenciaModel.id == id).first()
    if not transferencia:
        return problem(404, "Não encontrada", "A transferência solicitada não existe.", instance=f"/transferencias/{id}")
    
    # Devolvemos no formato do schema para o Pydantic converter para camelCase
    return SolicitacaoTransferencia(
        patrimonio_id=transferencia.patrimonio_numero,
        setor_destino=transferencia.setor_destino,
        responsavel_recebimento=transferencia.responsavel_recebimento,
        justificativa=transferencia.justificativa,
        numero_movimento=transferencia.numero_movimento
    )


# ─── GET /transferencias/ ─────────────────────────────────────────────────
@router.get("/transferencias/")
async def listar_transferencias():
    # TODO: Implementar busca real no banco depois
    return []

# ─── PATCH /transferencias/{id} ───────────────────────────────────────────────
@router.patch("/{id}", status_code=200)
def editar_transferencia(
    id: int,
    edicao: EdicaoTransferencia,
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: dict = Depends(obter_usuario_atual) # Pegamos o usuário para ler os escopos
):
    # Validamos se o usuário tem a permissão base de escrita
    if "transferencia:write" not in usuario_atual.get("escopos", []):
        return problem(403, "Acesso Negado", "Você não tem permissão para editar transferências.", instance=str(request.url))

    transferencia = db.query(TransferenciaModel).filter(TransferenciaModel.id == id).first()
    if not transferencia:
        return problem(404, "Não encontrada", "A transferência solicitada não existe.", instance=str(request.url))

    # Verifica se houve tentativa de mudar campos estruturais
    mudanca_estrutural = any([edicao.setor_destino, edicao.responsavel_recebimento, edicao.justificativa])

    if mudanca_estrutural:
        # REGRA 409: Se não está mais pendente, bloqueia campos estruturais
        if transferencia.status != "PENDENTE":
            return problem(409, "Conflito de Estado", "Transferência já efetivada. Apenas o numeroMovimento pode ser alterado.", instance=str(request.url))
        
        # REGRA 403/422: Validar o Override Administrativo
        if not edicao.override_admin:
            return problem(403, "Acesso Negado", "Alterações em campos estruturais exigem overrideAdmin=true.", instance=str(request.url))
            
        if "admin:override" not in usuario_atual.get("escopos", []):
            return problem(403, "Acesso Negado", "Escopo 'admin:override' necessário para forçar alterações.", instance=str(request.url))
            
        if not edicao.motivo_override or len(edicao.motivo_override) < 15:
            return problem(422, "Erro de Validação", "O motivoOverride deve ter pelo menos 15 caracteres.", instance=str(request.url))
            
        # ✨ CORREÇÃO AQUI: Indentação puxada para fora do 'if' do erro 422!
        # Registra o override
        transferencia.override_admin = True
        transferencia.motivo_override = edicao.motivo_override

    # Aplica as alterações permitidas
    if edicao.setor_destino:
        transferencia.setor_destino = edicao.setor_destino
    if edicao.responsavel_recebimento:
        transferencia.responsavel_recebimento = edicao.responsavel_recebimento
    if edicao.justificativa is not None:
        transferencia.justificativa = edicao.justificativa
    if edicao.numero_movimento is not None:
        transferencia.numero_movimento = edicao.numero_movimento

    db.commit()
    
    # Retorna o objeto atualizado
    return SolicitacaoTransferencia(
        patrimonio_id=transferencia.patrimonio_numero,
        setor_destino=transferencia.setor_destino,
        responsavel_recebimento=transferencia.responsavel_recebimento,
        justificativa=transferencia.justificativa,
        numero_movimento=transferencia.numero_movimento
    )