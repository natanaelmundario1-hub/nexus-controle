import os
import uuid
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')

def obter_conexao():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

TOKENS_VALIDOS = {}

# ===================================
# LOGIN
# ===================================

@app.route('/api/login', methods=['POST'])
def login():

    dados = request.get_json()

    usuario = dados.get('usuario')
    senha = dados.get('senha')

    try:

        conn = obter_conexao()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            "SELECT * FROM usuarios WHERE email = %s AND senha = %s",
            (usuario, senha)
        )

        usuario_encontrado = cursor.fetchone()

        cursor.close()
        conn.close()

        if usuario_encontrado:

            token = str(uuid.uuid4())
            TOKENS_VALIDOS[token] = usuario

            return jsonify({
                "sucesso": True,
                "token": token,
                "nome": usuario_encontrado['nome']
            })

        else:
            return jsonify({
                "sucesso": False,
                "erro": "Usuário ou senha inválidos."
            })

    except Exception as e:
        return jsonify({
            "sucesso": False,
            "erro": str(e)
        })

# ===================================
# CALCULAR CRÉDITO IMOBILIÁRIO
# ===================================

@app.route('/api/calcular-credito', methods=['POST'])
def calcular_credito():

    dados = request.get_json()

    token = dados.get('token')

    if token not in TOKENS_VALIDOS:
        return jsonify({
            "erro": "Sessão inválida."
        }), 401

    valor_imovel = float(dados.get('valorImovel', 0))
    renda_bruta = float(dados.get('rendaBruta', 0))
    renda_informal = float(dados.get('rendaInformal', 0))
    entrada = float(dados.get('valorEntrada', 0))
    fgts = float(dados.get('valorFgts', 0))
    prazo_meses = int(dados.get('prazoMeses', 360))
    taxa_juros = float(dados.get('taxaJuros', 9.5))

    renda_total = renda_bruta + renda_informal

    valor_financiar = valor_imovel - entrada - fgts

    if valor_financiar <= 0:
        return jsonify({
            "mensagem": "Não há valor restante para financiar."
        })

    taxa_mensal = (taxa_juros / 100) / 12

    amortizacao = valor_financiar / prazo_meses

    juros = valor_financiar * taxa_mensal

    primeira_parcela = amortizacao + juros

    comprometimento = renda_total * 0.30

    if primeira_parcela <= comprometimento:

        mensagem = f'''
🛡️ CERTIFICADO DE VIABILIDADE APROVADO

Valor financiado:
R$ {valor_financiar:,.2f}

Primeira parcela:
R$ {primeira_parcela:,.2f}

Limite de renda:
R$ {comprometimento:,.2f}
'''

    else:

        mensagem = f'''
⚠️ CRÉDITO NÃO RECOMENDADO

Parcela estimada:
R$ {primeira_parcela:,.2f}

Limite máximo:
R$ {comprometimento:,.2f}
'''

    return jsonify({
        "mensagem": mensagem
    })

# ===================================
# INICIAR SERVIDOR
# ===================================

if __name__ == '__main__':
    app.run(debug=True)
