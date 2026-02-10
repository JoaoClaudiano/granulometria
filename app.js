import React, { useState, useEffect } from 'react';
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
import { Beaker, Download, Plus, Trash2 } from 'lucide-react';
import jsPDF from 'jspdf';
import 'jspdf-autotable';

ChartJS.register(LogarithmicScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const PENEIRAS_PADRAO = [
  { nome: '3"', abertura: 75 },
  { nome: '2"', abertura: 50 },
  { nome: '1"', abertura: 25 },
  { nome: '3/8"', abertura: 9.5 },
  { nome: '#4', abertura: 4.75 },
  { nome: '#10', abertura: 2.0 },
  { nome: '#40', abertura: 0.425 },
  { nome: '#200', abertura: 0.075 },
];

function App() {
  const [dados, setDados] = useState(
    PENEIRAS_PADRAO.map(p => ({ ...p, massaRetida: 0 }))
  );
  const [massaTotal, setMassaTotal] = useState(1000);

  // Cálculos de Granulometria
  const calcularResultados = () => {
    let acumulado = 0;
    return dados.map(item => {
      acumulado += parseFloat(item.massaRetida || 0);
      const porcRetidaAcumulada = (acumulado / massaTotal) * 100;
      const porcPassante = 100 - porcRetidaAcumulada;
      return { ...item, porcPassante: porcPassante.toFixed(2) };
    });
  };

  const resultados = calcularResultados();

  // Configuração do Gráfico
  const chartData = {
    datasets: [{
      label: 'Curva Granulométrica (NBR 7181)',
      data: resultados.map(r => ({ x: r.abertura, y: r.porcPassante })),
      borderColor: '#2563eb',
      backgroundColor: '#2563eb',
      tension: 0.3,
      showLine: true
    }]
  };

  const chartOptions = {
    scales: {
      x: {
        type: 'logarithmic',
        position: 'bottom',
        title: { display: true, text: 'Abertura das Peneiras (mm)', color: '#374151', font: { weight: 'bold' } },
        reverse: true, // Padrão geotécnico: maiores aberturas à esquerda
        min: 0.01,
        max: 100,
      },
      y: {
        min: 0,
        max: 100,
        title: { display: true, text: '% Passante Acumulado', color: '#374151', font: { weight: 'bold' } }
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans">
      <header className="max-w-6xl mx-auto mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-blue-900 flex items-center gap-2">
            <Beaker /> GranuloWeb BR
          </h1>
          <p className="text-gray-600">Análise Granulométrica de Solos - NBR 7181</p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Lado Esquerdo: Entrada de Dados */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold mb-4 border-b pb-2">Dados do Ensaio</h2>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">Massa Total da Amostra (g)</label>
            <input 
              type="number" 
              value={massaTotal} 
              onChange={(e) => setMassaTotal(e.target.value)}
              className="mt-1 block w-full p-2 border rounded-md bg-blue-50 border-blue-200"
            />
          </div>

          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-sm text-gray-500 uppercase">
                <th className="py-2">Peneira</th>
                <th className="py-2">Abertura (mm)</th>
                <th className="py-2">Massa Retida (g)</th>
                <th className="py-2">% Passante</th>
              </tr>
            </thead>
            <tbody>
              {resultados.map((item, index) => (
                <tr key={index} className="border-t">
                  <td className="py-2 font-medium">{item.nome}</td>
                  <td className="py-2 text-gray-600">{item.abertura}</td>
                  <td className="py-2">
                    <input 
                      type="number"
                      className="w-24 p-1 border rounded"
                      value={item.massaRetida}
                      onChange={(e) => {
                        const novosDados = [...dados];
                        novosDados[index].massaRetida = e.target.value;
                        setDados(novosDados);
                      }}
                    />
                  </td>
                  <td className="py-2 font-bold text-blue-600">{item.porcPassante}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Lado Direito: Gráfico */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold mb-4 border-b pb-2">Curva Granulométrica</h2>
          <div className="h-80">
            <Line data={chartData} options={chartOptions} />
          </div>
          <div className="mt-8 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-bold text-gray-700 mb-2">Classificação Estimada (SUCS)</h3>
            <p className="text-sm text-gray-600">
              {parseFloat(resultados.find(r => r.nome === '#200')?.porcPassante) > 50 
                ? "Solo Fino (Silte ou Argila)" 
                : "Solo Grosso (Pedregulho ou Areia)"}
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
