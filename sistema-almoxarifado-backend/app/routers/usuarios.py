from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from app.database import get_db
from app.models.usuario import UsuarioModel
from app.schemas.usuario import UsuarioCriar, UsuarioEditar, UsuarioResposta
from app.auth import verificar_permissao, hash_senha, ESCOPOS_POR_CARGO

def problem(status: int, title: str, detail: str, instance: str = None) -> JSONResponse:
    body = {"type": f"https://api.almoxarifado.gov.br/erros/{status}",
            "title": title, "status": status, "detail": detail}
    if instance:
        body["instance"] = instance
    return JSONResponse(status_code=status,
                        media_type="application/problem+json", content=body)

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

# Apenas o cargo ADMIN pode acessar essas rotas
APENAS_MASTER = ["admin:override"]

# ─── ROTAS ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[UsuarioResposta],
            dependencies=[Depends(verificar_permissao(APENAS_MASTER))])
def listar_usuarios(db: Session = Depends(get_db)):
    """Lista todos os usuários do sistema (apenas admins)."""
    return db.query(UsuarioModel).all()


@router.post("/", response_model=UsuarioResposta, status_code=201,
             dependencies=[Depends(verificar_permissao(APENAS_MASTER))])
def criar_usuario(dados: UsuarioCriar, request: Request, db: Session = Depends(get_db)):
    """Cria um novo usuário no sistema."""
    
    # Verifica se o cargo informado é válido
    if dados.cargo not in ESCOPOS_POR_CARGO:
        return problem(
            422, "Cargo inválido",
            f"O cargo '{dados.cargo}' não existe. Valores aceitos: "
            f"{', '.join(ESCOPOS_POR_CARGO.keys())}",
            instance=str(request.url)
        )
    
    # Verifica se o e-mail já existe
    if db.query(UsuarioModel).filter(UsuarioModel.email == dados.email).first():
        return problem(409, "Conflito", "E-mail já cadastrado.", instance=str(request.url))
    
    novo = UsuarioModel(
        nome_completo = dados.nome_completo,
        email         = dados.email,
        senha_hash    = hash_senha(dados.senha),
        cargo         = dados.cargo,
        ativo         = True,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.put("/{usuario_id}", response_model=UsuarioResposta,
            dependencies=[Depends(verificar_permissao(APENAS_MASTER))])
def editar_usuario(usuario_id: int, dados: UsuarioEditar, request: Request, db: Session = Depends(get_db)):
    """Edita cargo, nome, senha ou status de um usuário existente."""
    
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not usuario:
        return problem(404, "Não Encontrado", "Usuário não encontrado.", instance=str(request.url))
    
    if dados.nome_completo is not None:
        usuario.nome_completo = dados.nome_completo
    if dados.cargo is not None:
        if dados.cargo not in ESCOPOS_POR_CARGO:
            return problem(
                422, "Cargo inválido",
                f"O cargo '{dados.cargo}' não existe. Valores aceitos: "
                f"{', '.join(ESCOPOS_POR_CARGO.keys())}",
                instance=str(request.url)
            )
        usuario.cargo = dados.cargo
    if dados.nova_senha is not None:
        usuario.senha_hash = hash_senha(dados.nova_senha)
    if dados.ativo is not None:
        usuario.ativo = dados.ativo
    
    db.commit()
    db.refresh(usuario)
    return usuario