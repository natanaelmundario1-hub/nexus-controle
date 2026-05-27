import os
import uuid
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# Criação obrigatória da instância do servidor Flask
app = Flask(__name__)
CORS(app)

TOKENS_VALIDOS = {}

def criar_tabelas():
    print("==================================================")
    print("🛡️ NEXUS | BANCO DE DADOS EM MODO DEMONSTRAÇÃO ATIVO")
    print("Tabelas estruturadas e prontas com histórico.")
    print("==================================================")

@app.route('/')
def home():
    return "Mesa de Crédito Nexus Operacional. Acesse via Frontend ou /dashboard."

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json() or {}
    usuario = dados.get('usuario', '').strip().lower()
    senha = dados.get('senha', '').strip()

    if usuario == "natanael@email.com" and senha == "nexus2026":
        token = str(uuid.uuid4())
        TOKENS_VALIDOS[token] = usuario
        return jsonify({"sucesso": True, "token": token, "nome": "Natanael Mundarlo", "creditos": 9999})
    elif usuario == "jhonn@email.com" and senha == "filhoDoNata123":
        token = str(uuid.uuid4())
        TOKENS_VALIDOS[token] = usuario
        return jsonify({"sucesso": True, "token": token, "nome": "Jhonn", "creditos": 500})
    else:
        return jsonify({"sucesso": False, "erro": "Usuário ou senha inválidos."}), 401

@app.route('/api/calcular-credito', methods=['POST'])
def calcular_credito():
    dados = request.get_json() or {}
    token = dados.get('token')
    tipo_simulacao = dados.get('tipo_simulacao')
    banco = dados.get('banco', 'caixa').lower()

    if not token:
        return jsonify({"sucesso": False, "erro": "Token obrigatório."}), 400

    resposta_simulacao = {}
    
    if tipo_simulacao == 'imovel':
        valor_imovel = float(dados.get('valor_imovel', 0))
        renda_mensal = float(dados.get('renda_mensal', 0))
        prazo_meses = int(dados.get('prazo_meses', 360))
        tipo_imovel = dados.get('tipo_imovel', 'Residencial')
        status_ocupacao = dados.get('status_ocupacao', 'Usado')
        cep = dados.get('cep', '')

        parcela_maxima = renda_mensal * 0.30
        taxa_mensal = 0.105 / 12
        valor_financiado = valor_imovel * 0.80
        parcela_estimada = (valor_financiado * taxa_mensal) / (1 - (1 + taxa_mensal)**(-prazo_meses))
        viavel = parcela_estimada <= parcela_maxima
        
        resposta_simulacao = {
            "tipo": "imovel", "banco_simulado": banco, "tipo_imovel": tipo_imovel,
            "status_ocupacao": status_ocupacao, "cep": cep, "valor_financiado": valor_financiado,
            "parcela_estimada": round(parcela_estimada, 2), "parcela_maxima_permitida": round(parcela_maxima, 2),
            "aprovado_preliminar": viavel, "motivo": "Sucesso" if viavel else "Parcela ultrapassa 30% da renda."
        }
    elif tipo_simulacao == 'veiculo':
        valor_veiculo = float(dados.get('valor_veiculo', 0))
        ano_veiculo = int(dados.get('ano_veiculo', 2024))
        renda_mensal = float(dados.get('renda_mensal', 0))
        prazo_meses = int(dados.get('prazo_meses', 60))

        taxa_anual = 0.14 if ano_veiculo >= 2020 else 0.19
        taxa_mensal = taxa_anual / 12
        valor_financiado = valor_veiculo * 0.90
        parcela_estimada = (valor_financiado * taxa_mensal) / (1 - (1 + taxa_mensal)**(-prazo_meses))
        viavel = parcela_estimada <= (renda_mensal * 0.30)
        
        resposta_simulacao = {
            "tipo": "veiculo", "banco_simulado": banco, "valor_financiado": valor_financiado, 
            "parcela_estimada": round(parcela_estimada, 2), "aprovado_preliminar": viavel, 
            "motivo": "Sucesso" if viavel else "Parcela muito alta."
        }
    elif tipo_simulacao == 'multas':
        valor_debitos = float(dados.get('valor_debitos', 0))
        prazo_meses = int(dados.get('prazo_meses', 12))
        resposta_simulacao = {
            "tipo": "multas", "valor_financiado": valor_debitos, "prazo_meses": prazo_meses,
            "parcela_estimada": round(valor_debitos / prazo_meses, 2), "aprovado_preliminar": True, "motivo": "Sucesso"
        }
    elif tipo_simulacao == 'agro':
        valor_projeto = float(dados.get('valor_projeto', 0))
        resposta_simulacao = {
            "tipo": "agro", "valor_financiado": valor_projeto, "parcela_estimada": round(valor_projeto / 12, 2),
            "aprovado_preliminar": True, "motivo": "Sucesso"
        }
    elif tipo_simulacao == 'global':
        valor_captacao = float(dados.get('valor_captacao', 0))
        resposta_simulacao = {
            "tipo": "global", "valor_financiado": valor_captacao, "parcela_estimada": round(valor_captacao / 24, 2),
            "aprovado_preliminar": True, "motivo": "Sucesso"
        }

    return jsonify({"sucesso": True, "resultado": resposta_simulacao, "creditos_restantes": 9999})
@app.route('/api/consultar-score', methods=['POST'])
def consultar_score():
    dados = request.get_json() or {}
    cpf = dados.get('cpf')
    cpf_limpo = "".join([c for c in str(cpf) if c.isdigit()])
    ultimo_digito = int(cpf_limpo[-1]) if cpf_limpo else 5
    
    if ultimo_digito in [1, 2, 3]:
        score = 320
        classificacao = "Ruim"
        recomendacao = "Alto risco. Não recomendado sem avalista estruturado."
    elif ultimo_digito in [4, 5, 6]:
        score = 610
        classificacao = "Bom"
        recomendacao = "Risco moderado. Viável com entrada padrão."
    else:
        score = 890
        classificacao = "Excelente"
        recomendacao = "Baixo risco. Cliente qualificado para melhores taxas."

    return jsonify({
        "sucesso": True, "cpf": cpf, "score": score, "classificacao": classificacao,
        "recomendacao": recomendacao, "creditos_restantes": 9999
    })

# O uso do prefixo r""" corrige de forma cega os avisos de escape sequence (\D) no terminal
html_dashboard = r"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>NEXUS | Dashboard Comercial</title>
    <link href="https://googleapis.com" rel="stylesheet">
    <style>
        body { background-color: #020617; color: white; font-family: 'Inter', sans-serif; padding: 40px; margin: 0; }
        .container-dash { max-width: 1100px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
        h2 { color: #0284c7; margin-top: 0; font-weight: 800; }
        #status-conexao { color: #10b981; font-weight: 600; margin-bottom: 20px; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { background-color: #1e293b; color: #94a3b8; text-align: left; padding: 12px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        td { padding: 14px 12px; border-bottom: 1px solid #1e293b; font-size: 14px; color: #e2e8f0; }
        .status-aprovado { color: #10b981; font-weight: 700; background: rgba(16,185,129,0.1); padding: 4px 8px; border-radius: 4px; }
        .status-recusado { color: #ef4444; font-weight: 700; background: rgba(239,68,68,0.1); padding: 4px 8px; border-radius: 4px; }
        .btn-whats { display: inline-block; background-color: #25d366; color: white; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container-dash">
        <h2>🛡️ NEXUS | Painel de Controle Comercial</h2>
        <div id="status-conexao">Autenticando na Mesa de Crédito...</div>
        <table>
            <thead>
                <tr>
                    <th>Data/Hora</th>
                    <th>Cliente</th>
                    <th>Esteira</th>
                    <th>Valor Proposto</th>
                    <th>Prazo</th>
                    <th>Status Mesa</th>
                    <th>Ação Comercial</th>
                </tr>
            </thead>
            <tbody id="corpo-tabela"></tbody>
        </table>
    </div>
"""

script_dashboard = r"""
    <script>
        var senhaMaster = prompt("Digite a Senha Master da Nexus:");
        fetch('/api/propostas?senha=' + encodeURIComponent(senhaMaster))
        .then(res => res.json())
        .then(dados => {
            if (!dados) return;
            document.getElementById('status-conexao').innerText = "Conectado. Exibindo atendimentos.";
        }).catch(err => {
            document.getElementById('status-conexao').innerText = "Pronto para receber dados da mesa.";
        });
    </script>
</body>
</html>
"""

@app.route('/dashboard')
def dashboard():
    return render_template_string(html_dashboard + script_dashboard)

if __name__ == '__main__':
    criar_tabelas()
    app.run(debug=True, host='0.0.0.0', port=5000)
