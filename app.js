import React, { useState, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import { 
  Chart as ChartJS, 
  LogarithmicScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip, 
  Legend 
} from 'chart.js';
import { Beaker, Download, Plus, Trash2, AlertTriangle, FileText, Image as ImageIcon } from 'lucide-react';
import jsPDF from 'jspdf';
import 'jspdf-autotable';

ChartJS.register(LogarithmicScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const PENEIRAS_INICIAIS = [
  { nome: '3"', abertura: 75, massaRetida: 0 },
  { nome: '1.1/2"', abertura: 37.5, massaRetida: 0 },
  { nome: '3/8"', abertura: 9.5, massaRetida: 0 },
  { nome: '#4', abertura: 4.75, massaRetida: 0 },
  { nome: '#10', abertura: 2.0, massaRetida: 0 },
  { nome: '#40', abertura: 0.425, massaRetida: 0 },
  { nome: '#200', abertura: 0.075, massaRetida: 0 },
];

export default function App() {
  const [dados, setDados] = useState(PENEIRAS_INICIAIS);
  const [massaTotal, setMassaTotal] = useState(1000);
  const chartRef = useRef(null);

  // --- LÓGICA DE CÁLCULOS ---
  const somaMassaRetida = dados.reduce((acc, item) => acc + parseFloat(item.massaRetida || 0), 0);
  const erroMassa = (((somaMassaRetida - massaTotal) / massaTotal) * 100).toFixed(2);
  const erroAceitavel = Math.abs(erroMassa) <= 2; // NBR permite pequena variação

  const calcularResultados = () => {
    let acumulado = 0;
    return dados
      .sort((a, b) => b.abertura - a.abertura) // Garante ordem decrescente de abertura
      .map(item => {
        acumulado += parseFloat(item.massaRetida || 0);
        const porcRetidaAcumulada = (acumulado / massaTotal) * 100;
        const porcPassante = Math.max(0, 100 - porcRetidaAcumulada);
        return { ...item, porcPassante: porcPassante.toFixed(2) };
      });
  };

  const resultados = calcularResultados();

  // --- FUNÇÕES ADICIONAIS ---
  const adicionarPeneira = () => {
    const nome = prompt("Nome da peneira (ex: #100):");
    const abertura = parseFloat(prompt("Abertura em mm:"));
    if (nome && abertura) {
      setDados([...dados, { nome, abertura, massaRetida: 0 }]);
    }
  };

  const removerPeneira = (index) => {
    setDados(dados.filter((_, i) => i !== index));
  };

  const baixarImagem = () => {
    const link = document.createElement('a');
    link.download = 'curva-granulometrica.png';
    link.href = chartRef.current.toBase64Image();
    link.click();
  };

  const gerarPDF = () => {
    const doc = new jsPDF();
    doc.setFont("helvetica", "bold");
    doc.text("RELATÓRIO DE ENSAIO GRANULOMÉTRICO", 105, 15, { align: "center" });
    
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`Massa Total: ${massaTotal}g | Erro de Massa: ${erroMassa}%`, 14, 25);

    const tableData = resultados.map(r => [r.nome, r.abertura, r.massaRetida, `${r.porcPassante}%`]);
    doc.autoTable({
      startY: 30,
      head: [['Peneira', 'Abertura (mm)', 'Massa Retida (g)', '% Passante']],
      body: tableData,
    });

    doc.text("Classificação: " + obterClassificacao(), 14, doc.lastAutoTable.finalY + 10);
    doc.save("ensaio-granulometrico.pdf");
  };

  const obterClassificacao = () => {
    const p200 = parseFloat(resultados.find(r => r.abertura <= 0.075)?.porcPassante || 0);
    if (p200 > 50) return "SOLO FINO (Silte/Argila)";
    return "SOLO GROSSO (Areia/Pedregulho)";
  };

  // --- CONFIGURAÇÃO DO GRÁFICO ---
  const chartData = {
    datasets: [{
      label: 'Curva Granulométrica (NBR 7181)',
      data: resultados.map(r => ({ x: r.abertura, y: r.porcPassante })),
      borderColor: '#2563eb',
      borderWidth: 3,
      pointRadius: 5,
      tension: 0.2,
      showLine: true
    }]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: 'logarithmic',
        reverse: true,
        min: 0.01,
        max: 100,
        title: { display: true, text: 'Diâmetro das Partículas (mm)' }
      },
      y: { min: 0, max: 100, title: { display: true, text: '% Passante Acumulado' } }
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 text-slate-800">
      <header className="max-w-6xl mx-auto mb-8 flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <h1 className="text-2xl font-black text-blue-700 flex items-center gap-2 uppercase tracking-tight">
            <Beaker className="text-blue-500" /> GranuloWeb BR
          </h1>
          <p className="text-slate-500 text-sm">Processamento de ensaios conforme NBR 7181</p>
        </div>
        <div className="flex gap-2 mt-4 md:mt-0">
          <button onClick={baixarImagem} className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 px-4 py-2 rounded-lg text-sm font-semibold transition">
            <ImageIcon size={16} /> Imagem
          </button>
          <button onClick={gerarPDF} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition shadow-md shadow-blue-200">
            <FileText size={16} /> Exportar PDF
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Painel de Dados */}
        <div className="lg:col-span-5 space-y-6">
          <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-bold text-lg">Entrada de Dados</h2>
              <button onClick={adicionarPeneira} className="text-blue-600 hover:bg-blue-50 p-2 rounded-full transition">
                <Plus size={20} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="p-3 bg-slate-50 rounded-xl">
                <label className="text-xs font-bold text-slate-500 uppercase">Massa Total (g)</label>
                <input type="number" value={massaTotal} onChange={(e) => setMassaTotal(e.target.value)} className="w-full bg-transparent text-lg font-bold outline-none" />
              </div>
              <div className={`p-3 rounded-xl ${erroAceitavel ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                <label className="text-xs font-bold uppercase opacity-70 flex items-center gap-1">
                  Erro de Massa {!erroAceitavel && <AlertTriangle size={12} />}
                </label>
                <span className="text-lg font-bold">{erroMassa}%</span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs font-bold text-slate-400 uppercase border-b">
                    <th className="pb-2">Peneira</th>
                    <th className="pb-2">Massa (g)</th>
                    <th className="pb-2">% Passante</th>
                    <th className="pb-2 text-right">Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {resultados.map((item, index) => (
                    <tr key={index} className="border-b border-slate-50 last:border-0">
                      <td className="py-3 font-semibold text-slate-700">{item.nome} <span className="text-xs font-normal text-slate-400">({item.abertura}mm)</span></td>
                      <td>
                        <input 
                          type="number" 
                          className="w-20 p-1 border-b-2 border-transparent focus:border-blue-500 outline-none transition"
                          value={item.massaRetida}
                          onChange={(e) => {
                            const newDados = [...dados];
                            newDados[index].massaRetida = e.target.value;
                            setDados(newDados);
                          }}
                        />
                      </td>
                      <td className="font-bold text-blue-600">{item.porcPassante}%</td>
                      <td className="text-right">
                        <button onClick={() => removerPeneira(index)} className="text-slate-300 hover:text-red-500 transition"><Trash2 size={16}/></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        {/* Painel do Gráfico */}
        <div className="lg:col-span-7 space-y-6">
          <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 h-[500px] flex flex-col">
            <h2 className="font-bold text-lg mb-4">Curva Granulométrica</h2>
            <div className="flex-grow">
              <Line ref={chartRef} data={chartData} options={chartOptions} />
            </div>
          </section>

          <section className="bg-blue-900 text-white p-6 rounded-2xl shadow-lg">
            <h3 className="text-blue-300 text-xs font-bold uppercase tracking-widest mb-1">Classificação Preliminar</h3>
            <p className="text-2xl font-bold">{obterClassificacao()}</p>
            <p className="text-blue-400 text-sm mt-2 font-medium">Nota: Classificação baseada na passagem pela peneira #200 (0.075mm).</p>
          </section>
        </div>
      </main>
    </div>
  );
}
