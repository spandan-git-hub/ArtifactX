import { Link, useLocation } from 'react-router-dom';
import { Database, MessageSquare, GitFork, FileText, CheckCircle2, ChevronRight } from 'lucide-react';

const STAGES = [
  {
    step: 1,
    id: 'ingest',
    label: 'Ingest & Hash',
    desc: 'Evidence Upload & SHA-256 Manifest',
    icon: Database,
    route: (caseId) => `/cases/${caseId}/evidence`,
    matchPaths: ['/evidence'],
  },
  {
    step: 2,
    id: 'extract',
    label: 'Extract & Parse',
    desc: 'WhatsApp & Telegram Threads',
    icon: MessageSquare,
    route: (caseId) => `/cases/${caseId}/chat`,
    matchPaths: ['/chat'],
  },
  {
    step: 3,
    id: 'analyze',
    label: 'Analyze & Correlate',
    desc: 'Timeline, Density & Cross-App Match',
    icon: GitFork,
    route: (caseId) => `/cases/${caseId}/timeline`,
    matchPaths: ['/timeline', '/correlation'],
  },
  {
    step: 4,
    id: 'export',
    label: 'Court Export',
    desc: 'In-Memory PDF & Custody Audit',
    icon: FileText,
    route: (caseId) => `/cases/${caseId}/reports`,
    matchPaths: ['/reports'],
  },
];

const ForensicWorkflowStepper = ({ caseId, currentStage }) => {
  const location = useLocation();
  const currentStageNumber = currentStage?.stage_number || 1;

  const getStageStatus = (stage) => {
    const isCurrentRoute = stage.matchPaths.some((p) => location.pathname.includes(p));
    if (isCurrentRoute) return 'current';
    if (stage.step < currentStageNumber) return 'completed';
    if (stage.step === currentStageNumber) return 'active-pipeline';
    return 'pending';
  };

  return (
    <div className="bg-forensic-900/60 border border-forensic-800 rounded-xl p-3 shadow-inner">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {STAGES.map((stage, idx) => {
          const status = getStageStatus(stage);
          const Icon = stage.icon;
          const isCurrentRoute = status === 'current';
          const isCompleted = status === 'completed';

          return (
            <Link
              key={stage.id}
              to={stage.route(caseId)}
              className={`
                group relative flex items-center gap-3 p-2.5 rounded-lg border transition-all duration-200
                ${
                  isCurrentRoute
                    ? 'bg-accent-cyan/10 border-accent-cyan/40 shadow-sm shadow-accent-cyan/10 ring-1 ring-accent-cyan/30'
                    : isCompleted
                    ? 'bg-forensic-850/70 border-forensic-700/60 hover:border-forensic-600 hover:bg-forensic-800'
                    : 'bg-forensic-900/40 border-forensic-800/60 hover:border-forensic-700 hover:bg-forensic-850/40'
                }
              `}
            >
              {/* Step indicator badge */}
              <div
                className={`
                  w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 font-mono text-xs font-bold transition-colors
                  ${
                    isCurrentRoute
                      ? 'bg-accent-cyan text-forensic-950 shadow-sm shadow-accent-cyan/40'
                      : isCompleted
                      ? 'bg-accent-emerald/20 text-accent-emerald border border-accent-emerald/30'
                      : 'bg-forensic-800 text-forensic-400 border border-forensic-700 group-hover:text-forensic-200'
                  }
                `}
              >
                {isCompleted && !isCurrentRoute ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>

              {/* Stage labels */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-forensic-500">
                    Stage 0{stage.step}
                  </span>
                  {isCurrentRoute && (
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-cyan animate-pulse" />
                  )}
                </div>
                <div
                  className={`text-xs font-semibold truncate ${
                    isCurrentRoute
                      ? 'text-accent-cyan'
                      : isCompleted
                      ? 'text-forensic-200'
                      : 'text-forensic-400 group-hover:text-forensic-300'
                  }`}
                >
                  {stage.label}
                </div>
                <div className="text-[11px] text-forensic-500 truncate hidden md:block">
                  {stage.desc}
                </div>
              </div>

              {/* Arrow divider for non-last items */}
              {idx < STAGES.length - 1 && (
                <div className="hidden lg:flex items-center text-forensic-700 absolute -right-2 z-10">
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
};

export default ForensicWorkflowStepper;
