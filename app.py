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

# Nota: As sessões agora são validadas via banco de dados para evitar perda de login no deploy.
# Mantida a estrutura de dicionário em memória apenas para compatibilidade legada se necessário.
TOKENS_VALIDOS = {}

# ===================================
# INTEGRAÇÃO COM O MAKE / TALLY (Novas Rotas)
# ===================================

@app.route('/api/webhook-registrar', methods=['POST'])
def webhook_registrar():
    """ Rota acionada pelo Módulo HTTP do Make após o preenchimento do Tally """
    dados = request.get_json() or {}
    
    email = dados.get('email')
    nome = dados.get('nome')
    senha = dados.get('senha')  # Senha padrão enviada pelo Make ou gerada temporariamente
    plano = dados.get('plano', 'Gratuito')
    corretores = dados.get('corretores', '1')

    if not email or not nome:
        return jsonify({"sucesso": False, "erro": "Dados obrigatórios ausentes (email/nome)."}), 400

    # Define créditos iniciais com base na resposta de corretores/plano
    creditos_iniciais = 100 if corretores == 'mais de 3' else 20

    try:
        conn = obter_conexao()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Insere ou atualiza o usuário imobiliário no PostgreSQL
        cursor.execute(
            """
            INSERT INTO usuarios (email, nome, senha, plano, corretores, creditos) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE 
            SET plano = EXCLUDED.plano, corretores = EXCLUDED.corretores, creditos = usuarios.creditos + EXCLUDED.creditos
            RETURNING *;
            """,
            (email, nome, senha, plano, corretores, creditos_iniciais)
        )
        
        usuario_salvo = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "mensagem": "Usuário sincronizado com o ecossistema Nexus.",
            "usuario": usuario_salvo
        }), 201

    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route('/api/atualizar-creditos', methods=['POST'])
def atualizar_creditos():
    """ Rota para o Make atualizar saldo após transações do Stripe ou consumo de IA """
    dados = request.get_json() or {}
    email = dados.get('email')
    quantidade = int(dados.get('creditos', 0))
    operacao = dados.get('operacao', 'adicionar') # adicionar ou remover

    if not email:
        return jsonify({"sucesso": False, "erro": "E-mail do usuário não informado."}), 400

    try:
        conn = obter_conexao()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if operacao == 'remover':
            quantidade = -abs(quantidade)

        cursor.execute(
            "UPDATE usuarios SET creditos = GREATEST(0, creditos + %s) WHERE email = %s RETURNING creditos;",
            (quantidade, email)
        )
        
        resultado = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        if resultado:
            return jsonify({"sucesso": True, "novos_creditos": resultado['creditos']}), 200
        else:
            return jsonify({"sucesso": False, "erro": "Usuário não encontrado."}), 404

    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


# ===================================
# LOGIN (Integrado ao CodePen)
# ===================================

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json() or {}
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

        if usuario_encontrado:
            token = str(uuid.uuid4())
            TOKENS_VALIDOS[token] = usuario

            # Salva o token ativo diretamente na tabela para segurança persistente
            cursor.execute(
                "UPDATE usuarios SET token_ativo = %s WHERE email = %s",
                (token, usuario)
            )
            conn.commit()

            cursor.close()
            conn.close()

            return jsonify({
                "sucesso": True,
                "token": token,
                "nome": usuario_encontrado['nome'],
                "creditos": usuario_encontrado.get('creditos', 0)
            })
        else:
            cursor.close()
            conn.close()
            return jsonify({
                "sucesso": False,
                "erro": "Usuário ou senha inválidos."
            }), 401

    except Exception as e:
        return jsonify({
            "sucesso": False,
            "erro": str(e)
        }), 500


# ===================================
# CALCULAR CRÉDITO IMOBILIÁRIO (Uso do Sistema)
# ===================================

@app.route('/api/calcular-credito', methods=['POST'])
def calcular_credito():
    dados = request.get_json() or {}
    token = dados.get('token')

    # Validação dupla: Memória RAM ou Banco de dados PostgreSQL
    usuario_valido = None
    if token in TOKENS_VALIDOS:
        usuario_valido = TOKENS_VALIDOS[token]
    else:
        try:
            conn = obter_conexao()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT email, creditos FROM usuarios WHERE token_ativo = %s", (token,))
            usuario_db = cursor.fetchone()
            if usuario_db:
                usuario_valido = usuario_db['email']
                # Atualiza cache em memória
                TOKENS_VALIDOS[token] = usuario_valido
                
                if usuario_db['creditos'] <= 0:
                    cursor.close()
                    conn.close()
                    return jsonify({"erro": "Créditos esgotados. Efetue uma recarga no Stripe."}), 403
                    
            cursor.close()
            conn.close()
        except:
            pass

    if not usuario_valido:
        return jsonify({"erro": "Sessão inválida ou expirada."}), 401

    # Consome 1 crédito pelo cálculo executado
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET creditos = GREATEST(0, creditos - 1) WHERE email = %s", (usuario_valido,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"erro": f"Erro ao processar consumo de créditos: {str(e)}"}), 500

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
        return jsonify({"mensagem": "Não há valor restante para financiar."})

    taxa_mensal = (taxa_juros / 100) / 12
    amortizacao = valor_financiar / prazo_meses
    juros = valor_financiar * taxa_mensal
    primeira_parcela = amortizacao + juros
    comprometimento = renda_total * 0.30

    if primeira_parcela <= comprometimento:
        mensagem = f'''🛡️ CERTIFICADO DE VIABILIDADE APROVADO

Valor financiado: R$ {valor_financiar:,.2f}
Primeira parcela: R$ {primeira_parcela:,.2f}
Limite de renda (30%): R$ {comprometimento:,.2f}'''
    else:
        mensagem = f'''⚠️ CRÉDITO NÃO RECOMENDADO

Parcela estimada: R$ {primeira_parcela:,.2f}
Limite máximo de comprometimento: R$ {comprometimento:,.2f}'''

    return jsonify({"mensagem": mensagem})


# ===================================
# INICIAR SERVIDOR
# ===================================

if __name__ == '__main__':
    app.run(debug=True)
