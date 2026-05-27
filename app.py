import os
import uuid
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# Inicialização do servidor executivo Flask
app = Flask(__name__)
CORS(app)

# Banco de dados simulado em memória temporária para a esteira comercial
TOKENS_VALIDOS = {}
HISTORICO_PROPOSTAS = []

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
        renda_mensal = float(dados.get('renda_mensal', 0))
        prazo_meses = int(dados.get('prazo_meses', 60))

        taxa_anual = 0.145
        taxa_mensal = taxa_anual / 12
        valor_financiado = valor_veiculo * 0.90
        parcela_estimada = (valor_financiado * taxa_mensal) / (1 - (1 + taxa_mensal)**(-prazo_meses))
        viavel = parcela_estimada <= (renda_mensal * 0.30)
        
        resposta_simulacao = {
            "tipo": "veiculo", "banco_simulado": banco, "valor_financiado": valor_financiado, 
            "parcela_estimada": round(parcela_estimada, 2), "aprovado_preliminar": viavel, 
            "motivo": "Sucesso" if viavel else "Parcela ultrapassa margem consignável."
        }
        
    # ⚙️ ESTEIRA: MULTAS DETRAN
    elif tipo_simulacao == 'multas':
        valor_debitos = float(dados.get('valor_debitos', 0))
        prazo_meses = int(dados.get('prazo_meses', 12))
        resposta_simulacao = {
            "tipo": "multas", "valor_financiado": valor_debitos, "prazo_meses": prazo_meses,
            "parcela_estimada": round(valor_debitos / prazo_meses, 2), "aprovado_preliminar": True, "motivo": "Aprovado via Mesa Reguladora"
        }
        
    # 🌾 ESTEIRA: AGRO / PLANO SAFRA
    elif tipo_simulacao == 'agro':
        valor_projeto = float(dados.get('valor_projeto', 0))
        resposta_simulacao = {
            "tipo": "agro", "valor_financiado": valor_projeto, "prazo_meses": 12,
            "parcela_estimada": round(valor_projeto / 12, 2), "aprovado_preliminar": True, "motivo": "Subsídio Plano Safra Ativo"
        }
        
    # 🌐 ESTEIRA: GLOBAL OFFSHORE
    elif tipo_simulacao == 'global':
        valor_captacao = float(dados.get('valor_captacao', 0))
        resposta_simulacao = {
            "tipo": "global", "valor_financiado": valor_captacao, "prazo_meses": 24,
            "parcela_estimada": round(valor_captacao / 24, 2), "aprovado_preliminar": True, "motivo": "Aprovado para Comitê Offshore"
        }

    # Registra a proposta estruturada no histórico para alimentar o Dashboard automaticamente
    proposta_registro = {
        "nome_cliente": dados.get('nome_cliente', 'Cliente Anonimo'),
        "whatsapp_cliente": dados.get('whatsapp_cliente', '00000000000'),
        "tipo_simulacao": tipo_simulacao,
        "resultado": resposta_simulacao
    }
    HISTORICO_PROPOSTAS.append(proposta_registro)

    return jsonify({"sucesso": True, "resultado": resposta_simulacao, "creditos_restantes": 9999})
@app.route('/api/consultar-score', methods=['POST'])
def consultar_score():
    dados = request.get_json() or {}
    cpf = dados.get('cpf', '')
    nome_cliente = dados.get('nome_cliente', 'Cliente Score')
    whatsapp_cliente = dados.get('whatsapp_cliente', '00000000000')
    
    cpf_limpo = "".join([c for c in str(cpf) if c.isdigit()])
    ultimo_digito = int(cpf_limpo[-1]) if cpf_limpo else 5
    
    # Correção cirúrgica da tupla de checagem do último dígito
    if ultimo_digito in (1, 2, 3):
        score = 320
        classificacao = "Ruim"
        recomendacao = "Alto risco. Não recomendado sem avalista estruturado."
    elif ultimo_digito in (4, 5, 6):
        score = 610
        classificacao = "Bom"
        recomendacao = "Risco moderado. Viável com entrada padrão."
    else:
        score = 890
        classificacao = "Excelente"
        recomendacao = "Baixo risco. Cliente qualificado para melhores taxas."

    resposta_score = {
        "aprovado_preliminar": score > 400,
        "valor_financiado": score,
        "motivo": classificacao,
        "prazo_meses": 0
    }

    # Salva a consulta de score no histórico comercial do painel
    HISTORICO_PROPOSTAS.append({
        "nome_cliente": nome_cliente,
        "whatsapp_cliente": whatsapp_cliente,
        "tipo_simulacao": "score",
        "resultado": resposta_score
    })

    return jsonify({
        "sucesso": True, "cpf": cpf, "score": score, "classificacao": classificacao,
        "recomendacao": recomendacao, "creditos_restantes": 9999
    })

@app.route('/api/propostas', methods=['GET'])
def listar_propostas():
    senha = request.args.get('senha', '')
    if senha == "nexus2026":
        return jsonify(HISTORICO_PROPOSTAS)
    return jsonify({"erro": "Não autorizado"}), 401

# Uso de r""" blinda strings longas contra avisos de escape do console
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
    </style>
</head>
<body>
    <div class="container-dash">
        <h2>🛡️ NEXUS | Painel de Controle Comercial</h2>
        <div id="status-conexao">Autenticando na Mesa de Crédito...</div>
        <table>
            <thead>
                <tr>
                    <th>Cliente</th>
                    <th>Esteira</th>
                    <th>Valor Analisado</th>
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
            document.getElementById('status-conexao').innerText = "Conectado. Exibindo atendimentos em tempo real.";
            var corpo = document.getElementById('corpo-tabela');
            corpo.innerHTML = "";
            dados.forEach(p => {
                var vBruto = p.resultado?.valor_financiado || 0;
                var valorExibir = p.tipo_simulacao === 'score' ? vBruto + " PTS" : p.resultado?.valor_financiado.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
                var classStatus = p.resultado?.aprovado_preliminar ? 'status-aprovado' : 'status-recusado';
                var textoStatus = p.resultado?.aprovado_preliminar ? 'APROVADO' : 'RECUSADO';
                
                var textoWhats = "Olá " + p.nome_cliente + ", vi seu atendimento na esteira Nexus. Vamos fechar o contrato?";
                var linkWhats = "https://whatsapp.com" + p.whatsapp_cliente.replace(/\D/g, "") + "&text=" + encodeURIComponent(textoWhats);

                var tr = document.createElement('tr');
                tr.innerHTML = "<td><strong>" + p.nome_cliente + "</strong></td>" +
                               "<td>" + p.tipo_simulacao.toUpperCase() + "</td>" +
                               "<td>" + valorExibir + "</td>" +
                               "<td><span class='" + classStatus + "'>" + textoStatus + "</span></td>" +
                               "<td><a href='" + linkWhats + "' target='_blank' style='display:inline-block; background:#25d366; color:white; text-decoration:none; padding:6px 12px; border-radius:4px; font-weight:600; font-size:12px;'>Chamar no Whats</a></td>";
                corpo.appendChild(tr);
            });
        }).catch(err => {
            document.getElementById('status-conexao').innerText = "Acesso restrito.";
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
