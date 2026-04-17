# Arquivo: app/routers/patrimonio.py
from fastapi.responses import Response
from fpdf import FPDF

import pandas as pd
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.patrimonio import PatrimonioCriar, PatrimonioDetalhe, SolicitacaoBaixa
from app.auth import obter_usuario_atual
from app.auth import verificar_permissao

from app.models.patrimonio import PatrimonioModel, HistoricoModel

router = APIRouter(
    prefix="/patrimonios",
    tags=["Patrimonios"]
)

# --- PERFIS DE ACESSO RBAC ---
ADMIN_ONLY = ["ADMIN"]
ALL_STAFF   = ["ADMIN", "OPERADOR"]


# --- FUNÇÃO AUXILIAR DE PROCESSAMENTO (Não é um endpoint) ---
def processar_planilha_bg(conteudo_arquivo: bytes, db: Session):
    # Lemos os bytes do arquivo como se fosse um arquivo real usando o io.BytesIO
    df = pd.read_csv(io.BytesIO(conteudo_arquivo)) # Para Excel seria pd.read_excel
    
    for _, linha in df.iterrows():
        # Buscamos se o patrimônio já existe
        item = db.query(PatrimonioModel).filter(PatrimonioModel.numero == str(linha['numero'])).first()
        
        if item:
            # Se existe, apenas atualizamos a descrição (sem mudar setor ou número)
            item.descricao = linha['descricao']
        else:
            # Se não existe, criamos um novo
            novo_item = PatrimonioModel(
                numero=str(linha['numero']),
                descricao=linha['descricao'],
                setor_atual=linha['setor']
            )
            db.add(novo_item)
            
            # Geramos o histórico inicial automático
            historico = HistoricoModel(
                patrimonio_numero=str(linha['numero']),
                acao="IMPORTACAO_LOTE",
                destino=linha['setor']
            )
            db.add(historico)
    
    db.commit()


# --- ENDPOINT DE IMPORTAÇÃO ---
# POST /importar → ADMIN_ONLY (risco alto de corrupção de dados em lote)
@router.post("/importar", status_code=202, dependencies=[Depends(verificar_permissao(ADMIN_ONLY))])
async def importar_patrimonios(
    background_tasks: BackgroundTasks, 
    arquivo: UploadFile = File(...), 
    db: Session = Depends(get_db),
):
    # Validamos a extensão
    if not arquivo.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Apenas arquivos .csv são aceitos no momento.")

    # Lemos o conteúdo
    conteudo = await arquivo.read()
    
    # Adicionamos a tarefa para rodar "escondido" enquanto respondemos ao usuário
    background_tasks.add_task(processar_planilha_bg, conteudo, db)
    
    return {"mensagem": "O processamento do arquivo foi iniciado em segundo plano."}


# --- CADASTRAR PATRIMÔNIO ---
# POST / → ADMIN_ONLY (cadastro de novos bens patrimoniais)
@router.post("/", status_code=201, response_model=PatrimonioDetalhe, dependencies=[Depends(verificar_permissao(ADMIN_ONLY))])
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
# GET /{numero} → ALL_STAFF (consulta padrão)
@router.get("/{numero}", response_model=PatrimonioDetalhe, dependencies=[Depends(verificar_permissao(ALL_STAFF))])
def buscar_patrimonio(numero: str, db: Session = Depends(get_db)):
    # Faz o SELECT e automaticamente traz o relacionamento de histórico
    patrimonio = db.query(PatrimonioModel).filter(PatrimonioModel.numero == numero).first()
    
    if not patrimonio:
        raise HTTPException(status_code=404, detail="Patrimônio não encontrado.")
        
    return patrimonio


# --- REALIZAR BAIXA PATRIMONIAL ---
# POST /{numero}/baixas → ADMIN_ONLY (destrutivo; exige alta responsabilidade)
@router.post("/{numero}/baixas", status_code=200, dependencies=[Depends(verificar_permissao(ADMIN_ONLY))])
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
    )
    db.add(nova_acao)
    
    # 5. Salva a transação completa
    db.commit()
    db.refresh(patrimonio)
    
    return {"mensagem": f"Patrimônio {numero} baixado com sucesso.", "justificativa": baixa.justificativa}


# --- RELATÓRIO PDF ---
# GET /{numero}/relatorio-pdf → ALL_STAFF (consulta padrão)
@router.get("/{numero}/relatorio-pdf", dependencies=[Depends(verificar_permissao(ALL_STAFF))])
def gerar_relatorio_patrimonio(numero: str, db: Session = Depends(get_db)):
    # 1. Busca os dados no banco
    patrimonio = db.query(PatrimonioModel).filter(PatrimonioModel.numero == numero).first()
    if not patrimonio:
        raise HTTPException(status_code=404, detail="Patrimônio não encontrado")

    # 2. Configura o PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho Principal com fundo cinza
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 15, "SGM - SISTEMA DE GESTÃO MUNICIPAL", ln=True, align="C", fill=True)
    pdf.ln(5)

    # Detalhes do Patrimônio
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, f"DETALHES DO PATRIMÔNIO: {patrimonio.numero}", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(190, 8, f"Descrição: {patrimonio.descricao}", ln=True)
    pdf.cell(95, 8, f"Setor Atual: {patrimonio.setor_atual}", border=0)
    pdf.cell(95, 8, f"Status: {patrimonio.status}", ln=True)
    pdf.ln(10)

    # Tabela de Histórico - Cabeçalho
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(35, 8, "DATA/HORA", border=1, fill=True, align="C")
    pdf.cell(50, 8, "AÇÃO", border=1, fill=True, align="C")
    pdf.cell(50, 8, "ORIGEM", border=1, fill=True, align="C")
    pdf.cell(55, 8, "DESTINO", border=1, fill=True, align="C")
    pdf.ln()

    # Tabela de Histórico - Linhas (Auditória)
    pdf.set_font("Arial", "", 9)
    for h in patrimonio.historicos:
        data_formatada = h.data_hora.strftime("%d/%m/%Y %H:%M")
        pdf.cell(35, 8, data_formatada, border=1, align="C")
        pdf.cell(50, 8, h.acao, border=1)
        pdf.cell(50, 8, h.origem or "---", border=1)
        pdf.cell(55, 8, h.destino or "---", border=1)
        pdf.ln()

    # Rodapé para Assinatura
    pdf.ln(20)
    y_atual = pdf.get_y()
    pdf.line(10, y_atual, 80, y_atual)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(70, 5, "Responsável pelo Patrimônio / Almoxarifado", ln=True, align="C")

    # 3. Preparação do binário para retorno
    pdf_bytes = bytes(pdf.output()) 
    
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf", 
        headers={
            "Content-Disposition": f"attachment; filename=relatorio-{numero}.pdf"
        }
    )