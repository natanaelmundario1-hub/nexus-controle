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

def obter_conexao():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# ===================================
# CRIAR TABELAS (ATUALIZADO COM HISTÓRICO)
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

        # 🔥 NOVA TABELA: HISTÓRICO DE SIMULAÇÕES DO SISTEMA
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulacoes (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL,
                tipo_simulacao VARCHAR(50) NOT NULL,
                banco VARCHAR(50),
                valor_total NUMERIC(15,2),
                valor_financiado NUMERIC(15,2),
                parcela_estimada NUMERIC(15,2),
                prazo_meses INTEGER,
                aprovado BOOLEAN,
                documento_identificacao VARCHAR(50),
                data_simulacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Tabelas estruturadas e prontas com histórico.")
    except Exception as e:
        print("Erro ao inicializar tabelas do sistema:", e)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/webhook-registrar', methods=['POST'])
def webhook_registrar():
    dados = request.get_json() or {}
    email = dados.get('email', '')
    nome = dados.get('nome')
    senha = dados.get('senha')
    plano = dados.get('plano', 'Gratuito')
    corretores = dados.get('corretores', '1')

    if not nome or not senha:
        return jsonify({"sucesso": False, "erro": "Nome e WhatsApp obrigatórios."}), 400

    creditos_iniciais = 100 if corretores == 'mais de 3' else 20
    
    conn = obter_conexao()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        INSERT INTO usuarios (email, nome, senha, plano, corretores, creditos)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (senha)
        DO UPDATE SET
            plano = EXCLUDED.plano,
            corretores = EXCLUDED.corretores,
            creditos = usuarios.creditos + EXCLUDED.creditos
        RETURNING *;
    """, (email, nome, senha, plano, corretores, creditos_iniciais))
    usuario = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"sucesso": True, "mensagem": "Usuário salvo.", "usuario": usuario})

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json() or {}
    usuario = dados.get('usuario')
    senha = dados.get('senha')
    
    conn = obter_conexao()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM usuarios WHERE senha = %s", (usuario,))
    usuario_encontrado = cursor.fetchone()
    if usuario_encontrado:
        token = str(uuid.uuid4())
        TOKENS_VALIDOS[token] = usuario
        cursor.execute("UPDATE usuarios SET token_ativo = %s WHERE senha = %s", (token, usuario))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"sucesso": True, "token": token, "nome": usuario_encontrado['nome'], "creditos": usuario_encontrado['creditos']})
    else:
        cursor.close()
        conn.close()
        return jsonify({"sucesso": False, "erro": "Usuário não encontrado."}), 401

# ===================================
# CALCULAR CRÉDITO COM LOG DE HISTÓRICO
# ===================================
@app.route('/api/calcular-credito', methods=['POST'])
def calcular_credito():
    dados = request.get_json() or {}
    token = dados.get('token')
    tipo_simulacao = dados.get('tipo_simulacao')
    banco = dados.get('banco', 'caixa').lower()

    if not token or not tipo_simulacao:
        return jsonify({"sucesso": False, "erro": "Token e tipo obrigatórios."}), 400

    conn = obter_conexao()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    if token == "TOKEN_MESTRE_DESENVOLVIMENTO" or token == "TOKEN_LOCAL_SIMULADO":
        usuario_db = {"id": 0, "creditos": 9999}
    else:
        cursor.execute("SELECT id, creditos FROM usuarios WHERE token_ativo = %s", (token,))
        usuario_db = cursor.fetchone()

    if not usuario_db:
        cursor.close()
        conn.close()
        return jsonify({"sucesso": False, "erro": "Sessão inválida ou expirada."}), 401

    resposta_simulacao = {}
    doc_identificacao = ""
    v_total = 0.0
    
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
        
        v_total = valor_imovel
        doc_identificacao = cep
        
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

        if not placa or not renavam:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "erro": "Placa e RENAVAM obrigatórios."}), 400

        taxa_anual = 0.14 if ano_veiculo >= 2020 else 0.19
        taxa_mensal = taxa_anual / 12
        valor_financiado = valor_veiculo * 0.90
        parcela_estimada = (valor_financiado * taxa_mensal) / (1 - (1 + taxa_mensal)**(-prazo_meses))
        viavel = parcela_estimada <= (renda_mensal * 0.30)
        
        v_total = valor_veiculo
        doc_identificacao = placa
        
        resposta_simulacao = {
            "tipo": "veiculo", "banco_simulado": banco, "placa": placa, "renavam": renavam,
            "valor_financiado": valor_financiado, "parcela_estimada": round(parcela_estimada, 2),
            "aprovado_preliminar": viavel, "motivo": "Sucesso" if viavel else "Parcela muito alta."
        }

    # 💾 GRAVAÇÃO AUTOMÁTICA DA CONSULTA NO HISTÓRICO DO BANCO
    cursor.execute("""
        INSERT INTO simulacoes (usuario_id, tipo_simulacao, banco, valor_total, valor_financiado, parcela_estimada, prazo_meses, aprovado, documento_identificacao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (usuario_db['id'], tipo_simulacao, banco, v_total, resposta_simulacao["valor_financiado"], resposta_simulacao["parcela_estimada"], prazo_meses, resposta_simulacao["aprovado_preliminar"], doc_identificacao))

    # Desconta 1 crédito se for um corretor real
    novos_creditos = usuario_db['creditos']
    if token != "TOKEN_MESTRE_DESENVOLVIMENTO" and token != "TOKEN_LOCAL_SIMULADO":
        cursor.execute("UPDATE usuarios SET creditos = creditos - 1 WHERE id = %s RETURNING creditos", (usuario_db['id'],))
        novos_creditos = cursor.fetchone()['creditos']

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"sucesso": True, "resultado": resposta_simulacao, "creditos_restantes": novos_creditos})

@app.route('/api/consultar-score', methods=['POST'])
def consultar_score():
    dados = request.get_json() or {}
    token = dados.get('token')
    cpf = dados.get('cpf')
    if not token or not cpf:
        return jsonify({"sucesso": False, "erro": "Token e CPF obrigatórios."}), 400

    conn = obter_conexao()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    if token == "TOKEN_MESTRE_DESENVOLVIMENTO" or token == "TOKEN_LOCAL_SIMULADO":
        usuario_db = {"id": 0, "creditos": 9999}
    else:
        cursor.execute("SELECT id, creditos FROM usuarios WHERE token_ativo = %s", (token,))
        usuario_db = cursor.fetchone()

    if not usuario_db:
        cursor.close()
        conn.close()
        return jsonify({"sucesso": False, "erro": "Sessão inválida."}), 401

    cpf_limpo = "".join([c for c in str(cpf) if c.isdigit()])
    ultimo_digito = int(cpf_limpo[-1]) if cpf_limpo else 5
    
