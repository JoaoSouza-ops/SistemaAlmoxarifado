# app/routers/setores.py
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from typing import List
from fastapi.responses import JSONResponse

from app.database import get_db
from app.models.setor import SetorModel
from app.schemas.setor import SetorCriar, SetorRead, SetorAtualizar
from app.auth import verificar_permissao

def problem(status: int, title: str, detail: str, instance: str = None) -> JSONResponse:
    body = {"type": f"https://api.almoxarifado.gov.br/erros/{status}",
            "title": title, "status": status, "detail": detail}
    if instance:
        body["instance"] = instance
    return JSONResponse(status_code=status,
                        media_type="application/problem+json", content=body)

router = APIRouter(prefix="/setores", tags=["Setores"])

@router.get("/", response_model=List[SetorRead])
def listar_setores(db: Session = Depends(get_db)):
    return db.query(SetorModel).all()

@router.post("/", response_model=SetorRead, status_code=status.HTTP_201_CREATED)
def criar_setor(
    setor: SetorCriar, 
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(["admin:override"])) # Apenas admins criam setores
):
    if db.query(SetorModel).filter(SetorModel.id == setor.id).first():
        return problem(409, "Conflito",
                       "Um setor com este ID já existe.",
                       instance=str(request.url))
    
    if db.query(SetorModel).filter(SetorModel.sigla == setor.sigla).first():
        return problem(409, "Conflito",
                       "Esta sigla já está em uso.",
                       instance=str(request.url))

    novo_setor = SetorModel(**setor.model_dump())
    db.add(novo_setor)
    db.commit()
    db.refresh(novo_setor)
    return novo_setor

@router.put("/{id}", response_model=SetorRead)
def atualizar_setor(
    id: str, 
    edicao: SetorAtualizar, 
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(["admin:override"]))
):
    setor = db.query(SetorModel).filter(SetorModel.id == id).first()
    if not setor:
        return problem(404, "Não Encontrado",
                       "Setor não encontrado.",
                       instance=str(request.url))

    if edicao.nome:
        setor.nome = edicao.nome
    if edicao.sigla:
        setor.sigla = edicao.sigla

    db.commit()
    db.refresh(setor)
    return setor

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_setor(
    id: str, 
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_permissao(["admin:override"]))
):
    setor = db.query(SetorModel).filter(SetorModel.id == id).first()
    if not setor:
        return problem(404, "Não Encontrado",
                       "Setor não encontrado.",
                       instance=str(request.url))
    
    db.delete(setor)
    db.commit()
    return None