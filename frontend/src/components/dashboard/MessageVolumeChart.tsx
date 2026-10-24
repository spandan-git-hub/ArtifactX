import { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { TrendingUp } from 'lucide-react';
import { format, parseISO, isValid } from 'date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

/**
 * Groups events by date and source_app to build chart dataset
 */
export const buildVolumeData = (events = []) => {
  if (!events || events.length === 0) {
    return {
      labels: [],
      whatsappData: [],
      telegramData: [],
    };
  }

  const countsByDate = {}; // { 'YYYY-MM-DD': { whatsapp: N, telegram: M, rawDate: Date } }

  events.forEach((evt) => {
    if (!evt) return;

    let dateObj;
    if (evt.normalized_timestamp) {
      dateObj = typeof evt.normalized_timestamp === 'string'
        ? parseISO(evt.normalized_timestamp)
        : new Date(evt.normalized_timestamp);
    } else if (evt.timestamp) {
      const ts = typeof evt.timestamp === 'number' && evt.timestamp > 1e11
        ? evt.timestamp
        : evt.timestamp * 1000;
      dateObj = new Date(ts);
    }

    if (!dateObj || !isValid(dateObj)) return;

    const dateKey = format(dateObj, 'yyyy-MM-dd');
    if (!countsByDate[dateKey]) {
      countsByDate[dateKey] = { whatsapp: 0, telegram: 0, rawDate: dateObj };
    }

    const app = (evt.source_app || '').toLowerCase();
    if (app === 'whatsapp') {
      countsByDate[dateKey].whatsapp += 1;
    } else if (app === 'telegram') {
      countsByDate[dateKey].telegram += 1;
    }
  });

  const sortedKeys = Object.keys(countsByDate).sort((a, b) =>
    countsByDate[a].rawDate.getTime() - countsByDate[b].rawDate.getTime()
  );

  const labels = sortedKeys.map((key) => format(countsByDate[key].rawDate, 'MMM d'));
  const whatsappData = sortedKeys.map((key) => countsByDate[key].whatsapp);
  const telegramData = sortedKeys.map((key) => countsByDate[key].telegram);

  return { labels, whatsappData, telegramData };
};

const MessageVolumeChart = ({ events = [] }) => {
  const { labels, whatsappData, telegramData } = useMemo(() => buildVolumeData(events), [events]);

  const data = {
    labels,
    datasets: [
      {
        label: 'WhatsApp',
        data: whatsappData,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.12)',
        fill: true,
        tension: 0.35,
        borderWidth: 2,
        pointBackgroundColor: '#10b981',
        pointBorderColor: '#0f172a',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
      {
        label: 'Telegram',
        data: telegramData,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.12)',
        fill: true,
        tension: 0.35,
        borderWidth: 2,
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#0f172a',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        align: 'end',
        labels: {
          color: '#cbd5e1',
          usePointStyle: true,
          pointStyle: 'circle',
          boxWidth: 8,
          boxHeight: 8,
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
        displayColors: true,
        boxPadding: 6,
        usePointStyle: true,
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(255, 255, 255, 0.05)',
          drawBorder: false,
        },
        ticks: {
          color: '#64748b',
          font: {
            family: 'Inter, sans-serif',
            size: 11,
          },
        },
      },
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(255, 255, 255, 0.05)',
          drawBorder: false,
        },
        ticks: {
          color: '#64748b',
          precision: 0,
          font: {
            family: 'Inter, sans-serif',
            size: 11,
          },
        },
      },
    },
  };

  return (
    <div className="card h-full flex flex-col">
      <div className="section-header mb-4">
        <div className="section-icon">
          <TrendingUp className="h-5 w-5 text-accent-cyan" />
        </div>
        <div>
          <h2 className="section-title">Message Volume Trend</h2>
          <p className="text-xs text-forensic-500">Daily message activity across platforms</p>
        </div>
      </div>

      <div className="flex-1 min-h-[240px] relative">
        {labels.length > 0 ? (
          <Line data={data} options={options} />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-forensic-500">
            No volume data available for the timeline
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageVolumeChart;
