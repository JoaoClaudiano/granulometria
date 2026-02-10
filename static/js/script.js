function adicionarLinha() {
    const table = document.getElementById('tabela-peneiras').getElementsByTagName('tbody')[0];
    const newRow = table.insertRow();
    newRow.innerHTML = `<td><input type="number" class="abertura"></td>
                        <td><input type="number" class="peso"></td>
                        <td><button onclick="removerLinha(this)">×</button></td>`;
}

function removerLinha(btn) {
    btn.closest('tr').remove();
}

async function processarDados() {
    const dados = {
        ll: document.getElementById('ll').value,
        lp: document.getElementById('lp').value,
        ip: document.getElementById('ll').value - document.getElementById('lp').value,
        passa_200: 40 // Valor exemplo para teste
    };

    const response = await fetch('/calcular', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(dados)
    });

    const result = await response.json();
    document.getElementById('resultados').style.display = 'block';
    document.getElementById('res-sucs').innerText = result.sucs;
    document.getElementById('res-aashto').innerText = result.aashto;
    document.getElementById('res-mct').innerText = result.mct;
}
