# Arquivo: app/routers/patrimonio.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request, Query
from fastapi.responses import Response, JSONResponse
import pandas as pd
import io
import uuid
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.patrimonio import PatrimonioCriar, PatrimonioDetalhe, SolicitacaoBaixa, PaginatedPatrimonios
from app.auth import verificar_permissao
from app.models.patrimonio import PatrimonioModel, HistoricoModel
from app.models.setor import SetorModel          # ← necessário para resolver sigla → ID
from app.services.job_store import criar_job, atualizar_job, StatusEnum

router = APIRouter(prefix="/patrimonios", tags=["Patrimonios"])

ADMIN_ONLY = ["patrimonio:write"]
ALL_STAFF  = ["patrimonio:read"]


# ─── HELPER: ProblemDetails (RFC 7807) ───────────────────────────────────────
def problem(status: int, title: str, detail: str, instance: str = None) -> JSONResponse:
    body = {"type": f"https://api.almoxarifado.gov.br/erros/{status}",
            "title": title, "status": status, "detail": detail}
    if instance:
        body["instance"] = instance
    return JSONResponse(status_code=status, media_type="application/problem+json", content=body)


# ─── FUNÇÃO DE PROCESSAMENTO (background task) ───────────────────────────────
def processar_planilha_bg(conteudo: bytes, db: Session, job_id: str):
    try:
        atualizar_job(job_id, status=StatusEnum.PROCESSANDO, progresso=0)
        df = pd.read_csv(io.BytesIO(conteudo))
        total = len(df)

        for i, (_, linha) in enumerate(df.iterrows()):
            # No seu banco o campo "setor" do CSV já é o ID direto do setor
            setor_id = str(linha["setor"]).strip()

            item = db.query(PatrimonioModel).filter(
                PatrimonioModel.numero == str(linha["numero"])
            ).first()

            if item:
                item.descricao   = linha["descricao"]
                item.setor_atual = setor_id
            else:
                db.add(PatrimonioModel(
                    numero=str(linha["numero"]),
                    descricao=linha["descricao"],
                    setor_atual=setor_id,
                ))
                db.add(HistoricoModel(
                    patrimonio_numero=str(linha["numero"]),
                    acao="IMPORTACAO_LOTE",
                    destino=setor_id,
                ))

            atualizar_job(job_id, status=StatusEnum.PROCESSANDO, progresso=int((i + 1) / total * 100))

        db.commit()
        atualizar_job(job_id, status=StatusEnum.CONCLUIDO, progresso=100)

    except Exception as e:
        import traceback; traceback.print_exc()
        db.rollback()
        atualizar_job(job_id, status=StatusEnum.ERRO)


# ─── GET /patrimonios/ — Listagem paginada por setor ─────────────────────────
# FIX 1: esta rota estava ausente. O frontend chama listarPatrimoniosPorSetor()
# que precisa de um endpoint GET com filtro por setor_id e paginação.
# Retorna o mesmo shape { data, meta } que o frontend já espera.
@router.get("/", dependencies=[Depends(verificar_permissao(ALL_STAFF))])
def listar_patrimonios(
    request: Request,
    setor_id: str = Query(..., description="ID do setor para filtrar"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit

    base_query = db.query(PatrimonioModel).filter(
        PatrimonioModel.setor_atual == setor_id
    )

    total_count = base_query.count()

    items = base_query.order_by(PatrimonioModel.numero).offset(offset).limit(limit).all()

    # next_cursor: indica se há uma próxima página
    has_next = (offset + limit) < total_count
    next_cursor = str(page + 1) if has_next else None

    return {
        "data": items,
        "meta": {
            "totalCount":  total_count,
            "currentPage": page,
            "nextCursor":  next_cursor,
        },
    }


# ─── POST /patrimonios/importacoes ───────────────────────────────────────────
@router.post("/importacoes", status_code=202,
             dependencies=[Depends(verificar_permissao(ADMIN_ONLY))])
async def importar_patrimonios(
    request: Request,
    background_tasks: BackgroundTasks,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not arquivo.filename.endswith(".csv"):
        return problem(400, "Formato inválido", "Apenas arquivos .csv são aceitos.",
                       instance=str(request.url))

    conteudo = await arquivo.read()
    novo_job  = criar_job()
    job_id    = novo_job["id"]

    background_tasks.add_task(processar_planilha_bg, conteudo, db, job_id)

    return Response(
        status_code=202,
        headers={"Location": f"/jobs/{job_id}"},
        content=None,
    )


# ─── POST /patrimonios/ — Cadastro individual ─────────────────────────────────
@router.post("/", status_code=201, response_model=PatrimonioDetalhe,
             dependencies=[Depends(verificar_permissao(ADMIN_ONLY))])
def cadastrar_patrimonio(patrimonio: PatrimonioCriar, request: Request,
                         db: Session = Depends(get_db)):
    if db.query(PatrimonioModel).filter(
            PatrimonioModel.numero == patrimonio.numero).first():
        return problem(409, "Conflito", "Número de patrimônio já cadastrado.",
                       instance=str(request.url))

    novo = PatrimonioModel(numero=patrimonio.numero, descricao=patrimonio.descricao,
                           setor_atual=patrimonio.setor_atual)
    db.add(novo)
    db.add(HistoricoModel(patrimonio_numero=patrimonio.numero,
                          acao="CADASTRO_INICIAL", destino=patrimonio.setor_atual))
    db.commit()
    db.refresh(novo)
    return novo


# ─── GET /patrimonios/{numero} ────────────────────────────────────────────────
# ATENÇÃO: esta rota deve ficar APÓS o GET "/" e o POST "/importacoes",
# caso contrário o FastAPI interpreta "importacoes" como um {numero}.
@router.get("/{numero}", response_model=PatrimonioDetalhe,
            dependencies=[Depends(verificar_permissao(ALL_STAFF))])
def buscar_patrimonio(numero: str, request: Request, db: Session = Depends(get_db)):
    patrimonio = db.query(PatrimonioModel).filter(
        PatrimonioModel.numero == numero).first()
    if not patrimonio:
        return problem(404, "Não encontrado", f"Patrimônio {numero} não existe.",
                       instance=str(request.url))
    return patrimonio


# ─── POST /patrimonios/{numero}/baixas ───────────────────────────────────────
@router.post("/{numero}/baixas", status_code=200,
             dependencies=[Depends(verificar_permissao(ADMIN_ONLY))])
def realizar_baixa(numero: str, baixa: SolicitacaoBaixa, request: Request,
                   db: Session = Depends(get_db)):
    patrimonio = db.query(PatrimonioModel).filter(
        PatrimonioModel.numero == numero).first()

    if not patrimonio:
        return problem(404, "Não encontrado", f"Patrimônio {numero} não existe.",
                       instance=str(request.url))
    if patrimonio.status == "BAIXADO":
        return problem(422, "Regra de negócio violada",
                       "Este patrimônio já foi baixado anteriormente.",
                       instance=str(request.url))

    patrimonio.status = "BAIXADO"
    db.add(HistoricoModel(patrimonio_numero=patrimonio.numero, acao="BAIXA",
                          origem=patrimonio.setor_atual, destino="DESCARTE/ARQUIVO"))
    db.commit()
    db.refresh(patrimonio)
    return {"mensagem": f"Patrimônio {numero} baixado com sucesso.",
            "justificativa": baixa.justificativa}


# ─── GET /patrimonios/{numero}/relatorio-pdf ─────────────────────────────────
@router.get("/{numero}/relatorio-pdf",
            dependencies=[Depends(verificar_permissao(ALL_STAFF))])
def gerar_relatorio(numero: str, request: Request, db: Session = Depends(get_db)):
    patrimonio = db.query(PatrimonioModel).filter(
        PatrimonioModel.numero == numero).first()
    if not patrimonio:
        return problem(404, "Não encontrado", f"Patrimônio {numero} não existe.",
                       instance=str(request.url))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(190, 15, "SGM - SISTEMA DE GESTÃO MUNICIPAL", ln=True, align="C", fill=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, f"PATRIMÔNIO: {patrimonio.numero}", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(190, 8, f"Descrição: {patrimonio.descricao}", ln=True)
    pdf.cell(95, 8, f"Setor: {patrimonio.setor_atual}")
    pdf.cell(95, 8, f"Status: {patrimonio.status}", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    for col, w in [("DATA/HORA", 35), ("AÇÃO", 50), ("ORIGEM", 50), ("DESTINO", 55)]:
        pdf.cell(w, 8, col, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for h in patrimonio.historicos:
        pdf.cell(35, 8, h.data_hora.strftime("%d/%m/%Y %H:%M"), border=1, align="C")
        pdf.cell(50, 8, h.acao, border=1)
        pdf.cell(50, 8, h.origem or "---", border=1)
        pdf.cell(55, 8, h.destino or "---", border=1)
        pdf.ln()

    return Response(content=bytes(pdf.output()), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=relatorio-{numero}.pdf"})