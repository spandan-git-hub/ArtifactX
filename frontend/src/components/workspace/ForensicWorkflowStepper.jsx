import { Link } from 'react-router-dom';
import { CheckCircle2, ChevronRight } from 'lucide-react';

const STAGES = [
  { number: 1, name: 'Ingest & Hash', path: '' },
  { number: 2, name: 'Extract & Parse', path: '/search' },
  { number: 3, name: 'Analyze & Correlate', path: '/dashboard' },
  { number: 4, name: 'Court Export', path: '/reports' },
];

const ForensicWorkflowStepper = ({ currentStage = 1, caseId, currentPath = '' }) => {
  return (
    <div className="flex items-center gap-1 sm:gap-2 text-xs font-mono">
      {STAGES.map((stage, idx) => {
        const isCompleted = stage.number < currentStage;
        const isActive = stage.number === currentStage;
        const isCurrentRoute =
          stage.path === ''
            ? currentPath === `/cases/${caseId}` || currentPath === `/cases/${caseId}/`
            : currentPath.endsWith(stage.path);
        const stageUrl = `/cases/${caseId}${stage.path}`;

        return (
          <div key={stage.number} className="flex items-center gap-1 sm:gap-2">
            <Link
              to={stageUrl}
              className={`
                flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-colors whitespace-nowrap
                ${
                  isCurrentRoute || isActive
                    ? 'bg-accent-cyan/15 text-accent-cyan font-semibold border border-accent-cyan/30'
                    : isCompleted
                    ? 'bg-forensic-800/60 text-accent-emerald hover:bg-forensic-800'
                    : 'bg-forensic-900/40 text-forensic-500 hover:text-forensic-300'
                }
              `}
            >
              {isCompleted ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-accent-emerald" />
              ) : (
                <span className="w-4 h-4 rounded-full bg-forensic-800 flex items-center justify-center text-[10px]">
                  {stage.number}
                </span>
              )}
              <span>{stage.name}</span>
            </Link>

            {idx < STAGES.length - 1 && (
              <ChevronRight className="w-3 h-3 text-forensic-700 flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
};

export default ForensicWorkflowStepper;
