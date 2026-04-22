# Arquivo: seed.py
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
    UsuarioModel(nome_completo="Admin SGM",      email="admin@sgm.gov.br",
                 senha_hash=hash_senha("admin123"),  cargo="ADMIN",        ativo=True),
    UsuarioModel(nome_completo="Operador Silva",  email="operador@sgm.gov.br",
                 senha_hash=hash_senha("op123"),     cargo="OPERADOR",     ativo=True),
    UsuarioModel(nome_completo="Auditor Externo", email="auditor@sgm.gov.br",
                 senha_hash=hash_senha("audit123"),  cargo="VISUALIZADOR", ativo=True),
]

for u in usuarios:
    if not db.query(UsuarioModel).filter(UsuarioModel.email == u.email).first():
        db.add(u)

db.commit()

# Print ANTES do db.close() — objetos ainda estão vinculados à sessão
print("Seed concluído. Usuários criados:")
for u in usuarios:
    print(f"  {u.cargo:12} | {u.email}")

db.close()