from app.database import SessionLocal, engine, Base
from app.models.usuario import UsuarioModel
from app.auth import hash_senha

def criar_operador():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        operador_existente = db.query(UsuarioModel).filter(
            UsuarioModel.email == "operador2@embu.sp.gov.br"
        ).first()
        
        if not operador_existente:
            print("Criando usuário operador...")
            novo_operador = UsuarioModel(
                nome_completo="Operador SGM",
                email="operador@embu.sp.gov.br",
                senha_hash=hash_senha("operador123"),
                cargo="OPERADOR",
                ativo=True
            )
            db.add(novo_operador)  # ← bug corrigido aqui
            db.commit()
            print("✅ Operador criado com sucesso!")
        else:
            print("⚠️ O usuário operador já existe no banco.")
            
    except Exception as e:
        print(f"❌ Erro ao criar operador: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    criar_operador()