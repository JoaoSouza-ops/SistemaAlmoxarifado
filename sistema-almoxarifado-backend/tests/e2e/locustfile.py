# Arquivo: tests/e2e/locustfile.py
from locust import HttpUser, task, between
import random

class UtilizadorSGM(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Autenticação Centralizada"""
        response = self.client.post("/auth/login", data={
            "username": "admin@almoxarifado.gov.br",
            "password": "senha_admin_123"
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
            print("✅ Login efetuado. Iniciando simulação real.")
        else:
            self.headers = {}

    # --- CONSULTAS (As rotas GET que realmente existem) ---

    @task(4)
    def buscar_patrimonio_especifico(self):
        """GET /patrimonios/{numero}"""
        # IDs criados pelo nosso seed.py
        numero_real = f"MOV-{random.randint(1001, 1200)}"
        self.client.get(f"/patrimonios/{numero_real}", headers=self.headers, name="GET /patrimonios/{numero}")

    @task(1)
    def gerar_relatorio_pdf(self):
        """GET /patrimonios/{numero}/relatorio-pdf"""
        # Teste de stress: Gerar PDF exige mais da CPU e do Banco
        numero_real = f"MOV-{random.randint(1001, 1200)}"
        self.client.get(f"/patrimonios/{numero_real}/relatorio-pdf", headers=self.headers, name="GET /relatorio-pdf")

    # --- OPERAÇÕES (As rotas POST e PATCH) ---

    @task(2)
    def solicitar_transferencia(self):
        """POST /transferencias/"""
        numero_real = f"MOV-{random.randint(1001, 1200)}"
        payload = {
            "patrimonioId": numero_real,
            "setorDestino": "ALMOX-TESTE",
            "responsavelRecebimento": "Operador Locust",
            "justificativa": "Carga de stress PostgreSQL"
        }
        with self.client.post("/transferencias/", json=payload, headers=self.headers, catch_response=True, name="POST /transferencias/") as resp:
            # 201: Criado | 400/422: Regra de negócio (Patrimônio já em trânsito ou não ativo)
            if resp.status_code in [201, 400, 422]:
                resp.success()
            else:
                resp.failure(f"Erro inesperado: {resp.status_code}")

    @task(1)
    def criar_nota_board(self):
        """POST /board/notas - Sincronizado com o Schema NotaBoard"""
        
        payload = {
            "titulo": f"Nota de Stress {random.randint(1, 9999)}",
            "descricao": "Simulação de carga para validar a performance do Board no PostgreSQL.",
            "categoria": "AVISO", # Aqui deve ser um valor válido do seu Enum (ex: 'Geral', 'Aviso', 'Urgente')
            "fixado": False
        }
        
        with self.client.post("/board/notas", json=payload, headers=self.headers, catch_response=True, name="POST /board/notas") as response:
            if response.status_code == 201:
                response.success()
            else:
                # Se der 422 aqui, o terminal vai imprimir o que o Pydantic está reclamando
                print(f"❌ Erro 422 no Board: {response.text}")
                response.failure(f"Erro de validação: {response.status_code}")

    @task(1)
    def buscar_transferencia_por_id(self):
        """GET /transferencias/{id}"""
        # Simulando busca por IDs sequenciais (ajuste se seus IDs forem UUID)
        id_aleatorio = random.randint(1, 50)
        self.client.get(f"/transferencias/{id_aleatorio}", headers=self.headers, name="GET /transferencias/{id}")