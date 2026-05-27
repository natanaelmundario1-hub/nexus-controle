import os
import uuid
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TOKENS_VALIDOS = {}
HISTORICO_PROPOSTAS = []

def criar_tabelas():
    print("--------------------------------------------------")
    print("     NEXUS | BANCO DE DADOS EM MODO DEMONSTRACAO")
    print("      Estrutura operacional pronta para uso.")
    print("--------------------------------------------------")

@app.route('/')
def home():
    return "Mesa de Credito Nexus Operacional. Acesse via Frontend ou /dashboard."

@app.route('/api/login', methods=['POST'])
def login():
    try:
        dados = request.get_json() or {}
        usuario = dados.get('usuario', '').strip().lower()
        senha = dados.get('senha', '').strip()

        if usuario == "natan@gmail.com" and senha == "nexus2026":
            token = str(uuid.uuid4())
            TOKENS_VALIDOS[token] = usuario
            return jsonify({"status": "sucesso", "token": token, "operador": "NATANAEL MUNDARIO"})
            
        elif usuario == "natan@nexus.com" and senha == "NNDefend2026!":
            token = str(uuid.uuid4())
            TOKENS_VALIDOS[token] = usuario
            return jsonify({"status": "sucesso", "token": token, "operador": "NATANAEL MUNDARIO"})
        
        return jsonify({"status": "erro", "mensagem": "Credenciais invalidas de mesa"}), 401
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route('/api/simular', methods=['POST'])
def simular_proposta():
    try:
        dados = request.get_json() or {}
        nome_cliente = dados.get('nome', 'Cliente Executivo')
        whatsapp = dados.get('whatsapp', '')
        valor = dados.get('valor', 'R$ 0,00')
        prazo = dados.get('prazo', 'N/A')
        modalidade = dados.get('modalidade', 'IMOVEL').upper()
        documento = dados.get('documento', 'Nao Informado')
        data_emissao = dados.get('data', '')
        hora_emissao = dados.get('hora', '')
        
        protocolo = f"NX.{uuid.uuid4().hex[:6].upper()}"
        
        proposta = {
            "id_auditoria": protocolo,
            "data_emissao": data_emissao,
            "hora_emissao": hora_emissao,
            "operador": "NATANAEL MUNDARIO",
            "cliente": nome_cliente,
            "whatsapp": whatsapp,
            "modalidade": modalidade,
            "documento": documento,
            "valor": valor,
            "prazo": prazo,
            "status_mesa": "AGUARDANDO LIBERACAO DE ALCANCE" if modalidade == "SCORE" else "APROVADO PRE-ANALISE"
        }
        
        HISTORICO_PROPOSTAS.append(proposta)
        
        return jsonify({
            "status": "sucesso",
            "mensagem": "Simulacao registrada na mesa core",
            "proposta": proposta
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route('/api/historico', methods=['GET'])
def obter_historico():
    return jsonify({"status": "sucesso", "propostas": HISTORICO_PROPOSTAS})

criar_tabelas()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
