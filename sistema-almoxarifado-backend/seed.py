# Arquivo: seed.py
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.usuario import UsuarioModel
from app.models.patrimonio import PatrimonioModel
from app.auth import hash_senha
import sys

def seed_database():
    # 1. CRIAÇÃO DE TABELAS (A "Migração" Automática)
    # No Postgres, isto vai ler todos os ficheiros em app/models/ e criar as tabelas
    print("🚀 Iniciando criação de tabelas no PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas/verificadas com sucesso.")

    db: Session = SessionLocal()

    try:
        # 2. CRIAR UTILIZADOR ADMIN
        admin_email = "admin@almoxarifado.gov.br"
        admin_existe = db.query(UsuarioModel).filter(UsuarioModel.email == admin_email).first()

        if not admin_existe:
            print(f"👤 Criando utilizador administrador: {admin_email}...")
            novo_admin = UsuarioModel(
                nome_completo="Administrador Geral",
                email=admin_email,
                senha_hash=hash_senha("senha_admin_123"),
                cargo="ADMIN",
                ativo=True
            )
            db.add(novo_admin)
            print("✅ Administrador criado.")
        else:
            print("ℹ️ Administrador já existe no PostgreSQL.")

        # 3. CRIAR UTILIZADOR OPERADOR (Para os seus testes do Locust)
        op_email = "operador@almoxarifado.gov.br"
        op_existe = db.query(UsuarioModel).filter(UsuarioModel.email == op_email).first()

        if not op_existe:
            print(f"👤 Criando utilizador operador: {op_email}...")
            novo_op = UsuarioModel(
                nome_completo="Operador de Almoxarifado",
                email=op_email,
                senha_hash=hash_senha("senha_op_123"),
                cargo="OPERADOR",
                ativo=True
            )
            db.add(novo_op)
            print("✅ Operador criado.")

        # 4. CRIAR PATRIMÓNIOS DE TESTE (Essencial para a rota de transferência não dar 404)
        print("📦 Gerando patrimônios de teste para o Locust...")
        for i in range(1, 201): # Criamos 200 itens
            pat_num = f"MOV-{1000 + i}"
            existe = db.query(PatrimonioModel).filter(PatrimonioModel.numero == pat_num).first()
            if not existe:
                novo_pat = PatrimonioModel(
                    numero=pat_num,
                    descricao=f"Item de Teste de Carga #{i}",
                    setor_atual="ALMOX-CENTRAL",
                    status="ATIVO"
                )
                db.add(novo_pat)
        
        db.commit()
        print("🏁 Seed finalizado com sucesso no PostgreSQL!")

    except Exception as e:
        print(f"❌ ERRO NO SEED: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()