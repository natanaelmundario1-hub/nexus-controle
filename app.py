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
    
    # 🏠 ESTEIRA: IMÓVEIS
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
    
    # 🚗 ESTEIRA: VEÍCULOS
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
    # ⚙️ ESTEIRA: MULTAS E DÉBITOS DETRAN
    elif tipo_simulacao == 'multas':
        valor_debitos = float(dados.get('valor_debitos', 0))
        forma_pagamento = dados.get('forma_pagamento', 'cartao')
        prazo_meses = int(dados.get('prazo_meses', 12))
        entrada_paga = float(dados.get('entrada', 0))

        taxa_anual = 0.198
        taxa_mensal = taxa_anual / 12
        
        valor_a_financiar = valor_debitos
        motivo_validacao = "Sucesso"
        viavel = True

        if forma_pagamento == 'boleto':
            entrada_minima = valor_debitos * 0.30
            if entrada_paga < entrada_minima:
                viavel = False
                motivo_validacao = f"Entrada insuficiente. Mínimo de 30% ({round(entrada_minima, 2)}) obrigatório para boleto."
            valor_a_financiar = valor_debitos - entrada_paga

        parcela_estimada = (valor_a_financiar * taxa_mensal) / (1 - (1 + taxa_mensal)**(-prazo_meses)) if prazo_meses > 0 else valor_a_financiar
        
        resposta_simulacao = {
            "tipo": "multas", "forma_pagamento": forma_pagamento, "valor_total_debitos": valor_debitos,
            "entrada_paga": entrada_paga, "valor_financiado": round(valor_a_financiar, 2),
            "parcela_estimada": round(parcela_estimada, 2), "aprovado_preliminar": viavel, "motivo": motivo_validacao
        }

    # 🌾 ESTEIRA: CRÉDITO AGRO (PLANO SAFRA)
    elif tipo_simulacao == 'agro':
        valor_projeto = float(dados.get('valor_projeto', 0))
        faturamento_anual = float(dados.get('faturamento_anual', 0))
        ciclos_meses = int(dados.get('prazo_meses', 12))
        categoria = dados.get('categoria_projeto', 'Maquinas')

        taxa_anual = 0.085  # Juros subsidiados Agro
        taxa_mensal = taxa_anual / 12
        viavel = faturamento_anual >= (valor_projeto * 0.40)
        
        parcela_estimada = (valor_projeto * taxa_mensal) / (1 - (1 + taxa_mensal)**(-ciclos_meses))

        resposta_simulacao = {
            "tipo": "agro", "banco_simulado": banco, "categoria": categoria,
            "valor_financiado": valor_projeto, "parcela_estimada_mensal": round(parcela_estimada, 2),
            "aprovado_preliminar": viavel, "motivo": "Sucesso" if viavel else "Faturamento anual abaixo da margem de garantia de 40%."
        }

    # 🌐 ESTEIRA: GLOBAL / CAPTAÇÃO OFFSHORE
    elif tipo_simulacao == 'global':
        montante_captacao = float(dados.get('valor_captacao', 0))
        moeda = dados.get('moeda', 'USD').upper()
        carencia_meses = int(dados.get('carencia_meses', 24))
        prazo_meses = int(dados.get('prazo_meses', 120))

        taxa_anual = 0.045  # Juros internacionais baixos
        taxa_mensal = taxa_anual / 12
        parcela_estimada = (montante_captacao * taxa_mensal) / (1 - (1 + taxa_mensal)**(-prazo_meses))

        resposta_simulacao = {
            "tipo": "global", "moeda_indexadora": moeda, "montante": montante_captacao,
            "carencia_meses": carencia_meses, "taxa_aplicada": "4.5% a.a.",
            "parcela_estimada_pos_carencia": round(parcela_estimada, 2),
            "aprovado_preliminar": True, "motivo": "Simulação Offshore gerada para Comitê Internacional."
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

if __name__ == '__main__':
    criar_tabelas()
    app.run(debug=True, port=5000)
