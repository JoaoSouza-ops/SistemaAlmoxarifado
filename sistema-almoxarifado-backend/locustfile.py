from locust import HttpUser, task, between
import random
import uuid

class TesteDeStressTransferencias(HttpUser):
    # Tempo de espera curto (10 a 500ms) para gerar CAOS e concorrência máxima
    wait_time = between(0.01, 0.5) 
    
    def on_start(self):
        """Executa quando o utilizador virtual 'nasce'. Ideal para Login."""
        
        # Tentativa de Login
        response = self.client.post("/auth/login", data={
            "username": "operador@almoxarifado.gov.br", # Ajuste para o seu usuário
            "password": "sua_senha_aqui"                # Ajuste para a sua senha
        })
        
        # Programação Defensiva: Só tenta ler o JSON se o servidor responder 200 OK
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            print(f"✅ Login Locust com Sucesso! Token obtido.")
        else:
            # Se falhar, imprimimos o verdadeiro motivo do erro no terminal!
            print(f"❌ FALHA NO LOGIN DO LOCUST!")
            print(f"❌ Status Code: {response.status_code}")
            print(f"❌ Resposta da API: {response.text}")
            
            # Evita que os próximos testes quebrem por falta de header
            self.token = None
            self.headers = {}
            
    @task
    def bombardear_transferencias(self):
        """Dispara requisições de criação de transferência sem parar"""
        
        # Geramos dados aleatórios para simular pedidos distintos
        payload = {
            "patrimonioId": f"MOV-{random.randint(1000, 9999)}",
            "setorDestino": str(uuid.uuid4()),
            "responsavelRecebimento": f"Responsável {random.randint(1, 100)}",
            "justificativa": "Teste de carga massivo - precisamos de transferir urgente!"
        }
        
        # Fazemos o POST e agrupamos os resultados na métrica "/transferencias/"
        with self.client.post("/transferencias/", json=payload, headers=self.headers, name="POST /transferencias", catch_response=True) as response:
            # Como geramos IDs aleatórios, muitos vão dar 404 (património não existe). 
            # Para o teste de I/O e gargalo do banco, isso não importa, queremos ver se o servidor trava!
            # Se der 500, o servidor quebrou.
            if response.status_code == 500:
                response.failure(f"O SERVIDOR QUEBROU! Status: {response.status_code}")
            elif response.status_code in [201, 404, 422]:
                response.success() # Consideramos sucesso se a API conseguiu processar a regra de negócio