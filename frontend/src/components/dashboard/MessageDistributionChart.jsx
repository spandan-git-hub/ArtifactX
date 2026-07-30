import { useMemo } from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import { PieChart } from 'lucide-react';

ChartJS.register(ArcElement, Tooltip, Legend);

const MessageDistributionChart = ({ stats }) => {
  const waCount = stats?.whatsapp?.message_count ?? stats?.whatsapp?.total_messages ?? 0;
  const tgCount = stats?.telegram?.message_count ?? stats?.telegram?.total_messages ?? 0;
  const total = waCount + tgCount;

  const data = useMemo(
    () => ({
      labels: ['WhatsApp', 'Telegram'],
      datasets: [
        {
          data: [waCount, tgCount],
          backgroundColor: ['#10b981', '#3b82f6'],
          hoverBackgroundColor: ['#059669', '#2563eb'],
          borderColor: '#0f172a',
          borderWidth: 3,
        },
      ],
    }),
    [waCount, tgCount]
  );

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '72%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#cbd5e1',
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 16,
          font: {
            family: 'Inter, sans-serif',
            size: 12,
            weight: '500',
          },
        },
      },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 12,
        boxPadding: 6,
        usePointStyle: true,
        callbacks: {
          label: (context) => {
            const value = context.raw || 0;
            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
            return ` ${context.label}: ${value.toLocaleString()} (${percentage}%)`;
          },
        },
      },
    },
  };

  const waPct = total > 0 ? Math.round((waCount / total) * 100) : 0;
  const tgPct = total > 0 ? Math.round((tgCount / total) * 100) : 0;

  return (
    <div className="card h-full flex flex-col">
      <div className="section-header mb-4">
        <div className="section-icon">
          <PieChart className="h-5 w-5 text-accent-cyan" />
        </div>
        <div>
          <h2 className="section-title">Message Share</h2>
          <p className="text-xs text-forensic-500">Distribution across platforms</p>
        </div>
      </div>

      <div className="flex-1 min-h-[220px] relative flex items-center justify-center">
        {total > 0 ? (
          <>
            <Doughnut data={data} options={options} />
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-8">
              <span className="text-2xl font-bold font-mono text-forensic-50">{total.toLocaleString()}</span>
              <span className="text-xs text-forensic-500 uppercase tracking-wider">Total</span>
            </div>
          </>
        ) : (
          <div className="text-sm text-forensic-500">No message data available</div>
        )}
      </div>

      {total > 0 && (
        <div className="pt-4 border-t border-forensic-700/60 grid grid-cols-2 gap-2 text-center text-xs">
          <div>
            <span className="text-accent-emerald font-semibold">{waPct}%</span>
            <span className="text-forensic-400 block">WhatsApp</span>
          </div>
          <div>
            <span className="text-accent-blue font-semibold">{tgPct}%</span>
            <span className="text-forensic-400 block">Telegram</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageDistributionChart;
