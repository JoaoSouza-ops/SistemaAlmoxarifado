# app/models/setor.py
from sqlalchemy import Column, String
from app.database import Base

class SetorModel(Base):
    __tablename__ = "setores"

    id = Column(String, primary_key=True, index=True) # Ex: "SETOR-ADM", "SETOR-TI"
    nome = Column(String, nullable=False)             # Ex: "Administrativo"
    sigla = Column(String, nullable=False, unique=True) # Ex: "ADM"