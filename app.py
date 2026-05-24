import os
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')

TOKENS_VALIDOS = {}

# ===================================
# CONEXÃO COM BANCO
# ===================================

def obter_conexao():

    return psycopg2.connect(
        DATABASE_URL,
        sslmode='require'
    )

# ===================================
# CRIAR TABELAS
# ===================================

def criar_tabelas():

    try:

        conn = obter_conexao()
        cursor = conn.cursor()

        # TABELA DE USUÁRIOS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255),
                nome VARCHAR(255),
                senha VARCHAR(255) UNIQUE,
                plano VARCHAR(100),
                corretores VARCHAR(50),
                creditos INTEGER DEFAULT 0,
                token_ativo TEXT
            );
        """)

        # TABELA DE INDICADORES
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicadores_mercado (
                chave VARCHAR(100) PRIMARY KEY,
                valor TEXT NOT NULL,
                fonte VARCHAR(100),
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()

        cursor.close()
        conn.close()

        print("Tabelas criadas com sucesso.")

    except Exception as e:

        print("Erro ao criar tabelas:", e)

# ===================================
# HOME
# ===================================

@app.route('/')
def home():

    return render_template('index.html')

# ===================================
# WEBHOOK MAKE / TALLY
# ===================================

@app.route('/api/webhook-registrar', methods=['POST'])
def webhook_registrar():

    dados = request.get_json() or {}

    email = dados.get('email', '')
    nome = dados.get('nome')
    senha = dados.get('senha')
    plano = dados.get('plano', 'Gratuito')
    corretores = dados.get('corretores', '1')

    if not nome or not senha:

        return jsonify({
            "sucesso": False,
            "erro": "Nome e WhatsApp obrigatórios."
        }), 400

    creditos_iniciais = 100 if corretores == 'mais de 3' else 20

    try:

        conn = obter_conexao()

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute("""
            INSERT INTO usuarios
            (
                email,
                nome,
                senha,
                plano,
                corretores,
                creditos
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )

            ON CONFLICT (senha)

            DO UPDATE SET
                plano = EXCLUDED.plano,
                corretores = EXCLUDED.corretores,
                creditos = usuarios.creditos + EXCLUDED.creditos

            RETURNING *;
        """, (
            email,
            nome,
            senha,
            plano,
            corretores,
            creditos_iniciais
        ))

        usuario = cursor.fetchone()

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "mensagem": "Usuário salvo.",
            "usuario": usuario
        })

    except Exception as e:

        return jsonify({
            "sucesso": False,
            "erro": str(e)
        }), 500

# ===================================
# LOGIN
# ===================================

@app.route('/api/login', methods=['POST'])
def login():

    dados = request.get_json() or {}

    usuario = dados.get('usuario')
    senha = dados.get('senha')

    try:

        conn = obter_conexao()

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute(
            """
            SELECT *
            FROM usuarios
            WHERE senha = %s
            """,
            (usuario,)
        )

        usuario_encontrado = cursor.fetchone()

        if usuario_encontrado:

            token = str(uuid.uuid4())

            TOKENS_VALIDOS[token] = usuario

            cursor.execute("""
                UPDATE usuarios
                SET token_ativo = %s
                WHERE senha = %s
            """, (
                token,
                usuario
            ))

            conn.commit()

            cursor.close()
            conn.close()

            return jsonify({
                "sucesso": True,
                "token": token,
                "nome": usuario_encontrado['nome'],
                "creditos": usuario_encontrado['creditos']
            })

        else:

            cursor.close()
            conn.close()

            return jsonify({
                "sucesso": False,
                "erro": "Usuário não encontrado."
            }), 401

    except Exception as e:

        return jsonify({
            "sucesso": False,
            "erro": str(e)
        }), 500

# ===================================
# ATUALIZAR INDICADORES
# ===================================

@app.route('/api/atualizar-indicadores', methods=['POST'])
def atualizar_indicadores():

    dados = request.get_json() or {}

    chave = dados.get('chave')
    valor = dados.get('valor')
    fonte = dados.get('fonte')

    try:

        conn = obter_conexao()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO indicadores_mercado
            (
                chave,
                valor,
                fonte,
                ultima_atualizacao
            )

            VALUES
            (
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP
            )

            ON CONFLICT (chave)

            DO UPDATE SET
                valor = EXCLUDED.valor,
                fonte = EXCLUDED.fonte,
                ultima_atualizacao = CURRENT_TIMESTAMP;
        """, (
            chave,
            str(valor),
            fonte
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "mensagem": "Indicador atualizado."
        })

    except Exception as e:

        return jsonify({
            "sucesso": False,
            "erro": str(e)
        }), 500

# ===================================
# OBTER INDICADORES
# ===================================

@app.route('/api/obter-indicadores', methods=['GET'])
def obter_indicadores():

    try:

        conn = obter_conexao()

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute("""
            SELECT *
            FROM indicadores_mercado;
        """)

        indicadores = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "indicadores": indicadores
        })

    except Exception as e:

        return jsonify({
            "sucesso": False,
            "erro": str(e)
        }), 500

# ===================================
# CALCULAR CRÉDITO
# ===================================

@app.route('/api/calcular-credito', methods=['POST'])
def calcular_credito():

    dados = request.get_json() or {}

    token = dados.get('token')
    tipo_simulacao = dados.get('tipo_simulacao')
    banco = dados.get('banco', 'caixa').lower()

    if not token or not tipo_simulacao:

        return jsonify({
            "sucesso": False,
            "erro": "Token e tipo obrigatórios."
        }), 400

    try:

        conn = obter_conexao()

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute("""
            SELECT id, creditos
            FROM usuarios
            WHERE token_ativo = %s
        """, (token,))

        usuario_db = cursor.fetchone()

        if not usuario_db:

            cursor.close()
            conn.close()

            return jsonify({
                "sucesso": False,
                "erro": "Sessão inválida."
            }), 401

        if usuario_db['creditos'] <= 0:

            cursor.close()
            conn.close()

            return jsonify({
                "sucesso": False,
                "erro": "Sem créditos."
            }), 402

        # ===================================
        # TAXAS BANCÁRIAS
        # ===================================

        taxas_imovel = {
            "caixa": 0.105,
            "itau": 0.118,
            "bradesco": 0.122,
            "santander": 0.119
        }

        taxas_veiculo = {
            "caixa": 0.018,
            "itau": 0.021,
            "bradesco": 0.023,
            "santander": 0.022
        }

        resposta_simulacao = {}

        # ===================================
        # IMÓVEL
        # ===================================

        if tipo_simulacao == 'imovel':

            valor_imovel = float(
                dados.get('valor_imovel', 0)
            )

            renda_mensal = float(
                dados.get('renda_mensal', 0)
            )

            entrada = float(
                dados.get('entrada', 0)
            )

            prazo_meses = int(
                dados.get('prazo_meses', 360)
            )

            valor_financiado = (
                valor_imovel - entrada
            )

            parcela_maxima = (
                renda_mensal * 0.30
            )

            taxa_anual = taxas_imovel.get(
                banco,
                0.105
            )

            taxa_mensal = taxa_anual / 12

            parcela_estimada = (
                valor_financiado * taxa_mensal
            ) / (
                1 - (
                    1 + taxa_mensal
                ) ** (-prazo_meses)
            )

            aprovado = (
                parcela_estimada <= parcela_maxima
            )

            resposta_simulacao = {

                "tipo": "imovel",

                "banco": banco,

                "taxa_anual": round(
                    taxa_anual * 100,
                    2
                ),

                "valor_financiado": round(
                    valor_financiado,
                    2
                ),

                "parcela_estimada": round(
                    parcela_estimada,
                    2
                ),

                "parcela_maxima_permitida": round(
                    parcela_maxima,
                    2
                ),

                "aprovado_preliminar": aprovado
            }

        # ===================================
        # VEÍCULO
        # ===================================

        elif tipo_simulacao == 'veiculo':

            valor_veiculo = float(
                dados.get('valor_veiculo', 0)
            )

            entrada = float(
                dados.get('entrada', 0)
            )

            renda_mensal = float(
                dados.get('renda_mensal', 0)
            )

            prazo_meses = int(
                dados.get('prazo_meses', 60)
            )

            valor_financiado = (
                valor_veiculo - entrada
            )

            parcela_maxima = (
                renda_mensal * 0.30
            )

            taxa_mensal = taxas_veiculo.get(
                banco,
                0.018
            )

            parcela_estimada = (
                valor_financiado * taxa_mensal
            ) / (
                1 - (
                    1 + taxa_mensal
                ) ** (-prazo_meses)
            )

            aprovado = (
                parcela_estimada <= parcela_maxima
            )

            resposta_simulacao = {

                "tipo": "veiculo",

                "banco": banco,

                "taxa_mensal": round(
                    taxa_mensal * 100,
                    2
                ),

                "valor_financiado": round(
                    valor_financiado,
                    2
                ),

                "parcela_estimada": round(
                    parcela_estimada,
                    2
                ),

                "parcela_maxima_permitida": round(
                    parcela_maxima,
                    2
                ),

                "aprovado_preliminar": aprovado
            }

        else:

            cursor.close()
            conn.close()

            return jsonify({
                "sucesso": False,
                "erro": "Tipo inválido."
            }), 400

        # ===================================
        # REMOVER 1 CRÉDITO
        # ===================================

        cursor.execute("""
            UPDATE usuarios
            SET creditos = creditos - 1
            WHERE id = %s
        """, (
            usuario_db['id'],
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "resultado": resposta_simulacao
        })

    except Exception as e:

        return jsonify({
            "sucesso": False,
            "erro": str(e)
        }), 500

# ===================================
# INICIAR SERVIDOR
# ===================================

if __name__ == '__main__':

    criar_tabelas()

    app.run(debug=True)
