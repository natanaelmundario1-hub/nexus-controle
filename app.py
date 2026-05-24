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
# CONEXÃO COM O BANCO
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicadores_mercado (
                chave VARCHAR(50) PRIMARY KEY,
                valor TEXT NOT NULL,
                fonte VARCHAR(100),
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()

        cursor.close()
        conn.close()

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

            VALUES (%s, %s, %s, %s, %s, %s)

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
            "mensagem": "Usuário salvo com sucesso.",
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
            "SELECT * FROM usuarios WHERE senha = %s",
            (usuario,)
        )

        usuario_encontrado = cursor.fetchone()

        if usuario_encontrado:

            token = str(uuid.uuid4())

            TOKENS_VALIDOS[token] = usuario

            cursor.execute(
                """
                UPDATE usuarios
                SET token_ativo = %s
                WHERE senha = %s
                """,
                (token, usuario)
            )

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
# INICIAR SERVIDOR
# ===================================

if __name__ == '__main__':

    criar_tabelas()

    app.run(debug=True)
