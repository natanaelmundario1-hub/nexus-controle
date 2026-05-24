import os
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

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
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json() or {}
    usuario = dados.get('usuario', '').strip().lower()
    senha = dados.get('senha', '').strip()

    if usuario == "natanael@email.com" and senha == "nexus2026":
        token = str(uuid.uuid4())
        TOKENS_VALIDOS[token] = usuario
        return jsonify({
            "sucesso": True,
            "token": token,
            "nome": "Natanael Mundarlo",
            "creditos": 9999
        })
    elif usuario == "jhonn@email.com" and senha == "filhoDoNata123":
        token = str(uuid.uuid4())
        TOKENS_VALIDOS[token] = usuario
        return jsonify({
            "sucesso": True,
            "token": token,
            "nome": "Jhonn",
            "creditos": 500
        })
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
        placa = dados.get('placa', '').strip().upper()
        renavam = dados.get('renavam', '').strip()

        taxa_anual = 0.14 if ano_veiculo >= 2020 else 0.19
        taxa_mensal = taxa_anual / 12
        valor_financiado = valor_veiculo * 0.90
        parcela_estimada = (valor_financiado * taxa_mensal) / (1 - (1 + taxa_mensal)**(-prazo_meses))
        viavel = parcela_estimada <= (renda_mensal * 0.30)
        
        resposta_simulacao = {
            "tipo": "veiculo", "banco_simulado": banco, "placa": placa, "renavam": renavam,
            "valor_financiado": valor_financiado, "parcela_estimada": round(parcela_estimada, 2),
            "aprovado_preliminar": viavel, "motivo": "Sucesso" if viavel else "Parcela muito alta."
        }

    return jsonify({"sucesso": True, "resultado": resposta_simulacao, "creditos_restantes": 9999})

@app.route('/api/consultar-score', methods=['POST'])
def consultar_score():
    dados = request.get_json() or {}
    cpf = dados.get('cpf')
    
    cpf_limpo = "".join([c for c in str(cpf) if c.isdigit()])
    ultimo_digito = int(cpf_limpo[-1]) if cpf_limpo else 5
    
    if ultimo_digito == 1 or ultimo_digito == 2 or ultimo_digito == 3:
        score = 320
        classificacao = "Ruim"
        recomendacao = "Alto risco. Não recomendado sem avalista estruturado."
    elif ultimo_digito == 4 or ultimo_digito == 5 or ultimo_digito == 6:
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

if __name__ == '__main__':
    criar_tabelas()
    app.run(debug=True, port=5000)
