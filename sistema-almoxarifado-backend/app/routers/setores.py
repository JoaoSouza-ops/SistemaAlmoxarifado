# Arquivo: app/routers/setores.py
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.patrimonio import PatrimonioModel
from app.schemas.patrimonio import PatrimonioDetalhe, PaginatedPatrimonios, PaginacaoMeta
from app.auth import verificar_permissao

router = APIRouter(prefix="/setores", tags=["Patrimonios"])

ALL_STAFF = ["patrimonio:read"]


def problem(status: int, title: str, detail: str, instance: str = None) -> JSONResponse:
    body = {"type": f"https://api.almoxarifado.gov.br/erros/{status}",
            "title": title, "status": status, "detail": detail}
    if instance:
        body["instance"] = instance
    return JSONResponse(status_code=status, media_type="application/problem+json", content=body)


# ─── GET /setores/{id}/patrimonios ────────────────────────────────────────────
# CORREÇÃO: endpoint ausente no backend original — adicionado conforme contrato v2
# Suporta paginação (page, limit) e format (json/pdf/xlsx — PDF/XLSX a implementar)
@router.get(
    "/{id}/patrimonios",
    response_model=PaginatedPatrimonios,
    dependencies=[Depends(verificar_permissao(ALL_STAFF))],
)
def listar_patrimonios_por_setor(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    page:   int = Query(default=1,  ge=1,  description="Página atual"),
    limit:  int = Query(default=20, ge=1, le=100, description="Itens por página"),
    format: Optional[str] = Query(default="json", pattern="^(json|pdf|xlsx)$"),
):
    # format != json → avisa que PDF/XLSX ainda não estão implementados nesta rota
    if format in ("pdf", "xlsx"):
        return problem(501, "Não implementado",
                       f"Exportação '{format}' para esta rota ainda não está disponível.",
                       instance=str(request.url))

    query = db.query(PatrimonioModel).filter(PatrimonioModel.setor_atual == id)
    total = query.count()

    offset = (page - 1) * limit
    itens  = query.offset(offset).limit(limit).all()

    # nextCursor: retorna o número do próximo item para cursor-based pagination
    next_cursor = None
    if offset + limit < total:
        next_cursor = str(offset + limit)

    return PaginatedPatrimonios(
        data=[PatrimonioDetalhe.model_validate(i) for i in itens],
        meta=PaginacaoMeta(totalCount=total, currentPage=page, nextCursor=next_cursor),
    )