const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// BANCO DE DADOS DE CLIENTES ATIVOS
const USUARIOS_REGISTRADOS = {
    "joao_consultor": { senha: "senha123", status: "pago", nome: "João Silva" },
    "maria_corretora": { senha: "456senha", status: "pago", nome: "Maria Souza" }
};

const sessoesOnline = {};

// ROTA DE LOGIN COM TRAVA DE DISPOSITIVO
app.post('/api/login', (req, res) => {
    const { usuario, senha } = req.body;
    const conta = USUARIOS_REGISTRADOS[usuario];
    const ipAtual = req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress;

    if (!conta || conta.senha !== String(senha)) {
        return res.status(401).json({ erro: "Usuário ou senha incorretos!" });
    }

    if (conta.status !== "pago") {
        return res.status(403).json({ erro: "Acesso suspenso. Verifique o pagamento!" });
    }

    if (sessoesOnline[usuario] && sessoesOnline[usuario].ip !== ipAtual) {
        console.log(`\n🚨 [ALERTA] Usuário [${usuario}] tentou login duplo!`);
        USUARIOS_REGISTRADOS[usuario].status = "bloqueado_por_compartilhamento";
        delete sessoesOnline[usuario];
        return res.status(403).json({ erro: "Conta bloqueada por múltiplos acessos simultâneos." });
    }

    const tokenUnico = `autorizado_${usuario}_${Math.random().toString(36).substr(2, 9)}`;
    sessoesOnline[usuario] = { token: tokenUnico, ip: ipAtual, loginEm: new Date() };

    res.json({ sucesso: true, token: tokenUnico, nome: conta.nome });
});

// ROTA DO CÁLCULO
app.post('/api/calcular-credito', (req, res) => {
    const { token, usuario, valorImovel, rendaBruta, rendaInformal, valorEntrada, valorFgts } = req.body;
    const ipAtual = req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress;
    const sessaoValida = sessoesOnline[usuario];

    if (!sessaoValida || sessaoValida.token !== token || sessaoValida.ip !== ipAtual) {
        return res.status(401).json({ erro: "Sessão expirada. Faça login novamente." });
    }

    var rendaTotal = rendaBruta + rendaInformal;
    var valorFinanciado = valorImovel - (valorEntrada + valorFgts);
    var parcelaMaxima = rendaTotal * 0.30;

    var taxaMensal = 0.008; 
    var meses = 360;
    var parcelaEstimada = valorFinanciado * ( (taxaMensal * Math.pow(1 + taxaMensal, meses)) / (Math.pow(1 + taxaMensal, meses) - 1) );

    if (valorFinanciado <= 0) {
        return res.status(400).json({ erro: "Erro: Entrada cobre o imóvel." });
    }

    if (parcelaEstimada > parcelaMaxima) {
        return res.json({
            tokenCertificado: "NEXUS-REJEITADO",
            statusOperacao: "REPROVADO",
            erro: "⚠️ Renda Insuficiente para o perfil solicitado."
        });
    }

    res.json({
        tokenCertificado: `NEXUS-${Math.floor(100000 + Math.random() * 900000)}`,
        valorFinanciado: valorFinanciado.toFixed(2),
        meses: meses,
        parcelaEstimada: parcelaEstimada.toFixed(2),
        statusOperacao: "PRE-APROVADO"
    });
});

// A Render configura a porta automaticamente usando process.env.PORT
const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`🛡️ Servidor rodando na porta ${PORT}`));
