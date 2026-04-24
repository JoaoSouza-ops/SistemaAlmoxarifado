"""
══════════════════════════════════════════════════════════════════════════════
#ARQUIVO 2: seed.py  (na raiz do backend — atualizar as senhas para bater
#com o que o frontend usa no login de teste)
══════════════════════════════════════════════════════════════════════════════
"""
from app.database import SessionLocal, engine
from app.models.usuario import UsuarioModel
from app.models import board, patrimonio, transferencia, usuario as m_usuario
from app.auth import hash_senha

board.Base.metadata.create_all(bind=engine)
patrimonio.Base.metadata.create_all(bind=engine)
transferencia.Base.metadata.create_all(bind=engine)
m_usuario.Base.metadata.create_all(bind=engine)

db = SessionLocal()

usuarios = [
    UsuarioModel(
        nome_completo="Admin SGM",
        email="admin@sgm.gov.br",
        senha_hash=hash_senha("Adm2026@"),    #← senha para teste no frontend
        cargo="ADMIN",
        ativo=True,
    ),
    UsuarioModel(
        nome_completo="Operador Silva",
        email="operador@sgm.gov.br",
        senha_hash=hash_senha("Op2026@"),     #← senha para teste no frontend
        cargo="OPERADOR",
        ativo=True,
    ),
    UsuarioModel(
        nome_completo="Auditor Externo",
        email="auditor@sgm.gov.br",
        senha_hash=hash_senha("Vis2026@"),    #← senha para teste no frontend
        cargo="VISUALIZADOR",
        ativo=True,
    ),
]

for u in usuarios:
    if not db.query(UsuarioModel).filter(UsuarioModel.email == u.email).first():
        db.add(u)

db.commit()
print("Seed concluído:")
for u in usuarios:
    print(f"  {u.cargo:12} | {u.email}")
db.close()