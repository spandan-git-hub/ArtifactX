import { useState, useEffect, useRef } from 'react';
import { X, CheckCircle2, Loader2, AlertTriangle, Sparkles } from 'lucide-react';
import { demoService } from '../../services/demoService';

const STEPS = [
  'Creating case...',
  'Setting up WhatsApp evidence...',
  'Generating message history...',
  'Extracting contact book...',
  'Setting up Telegram evidence...',
  'Generating Telegram messages...',
  'Building timeline...',
  'Detecting deleted messages...',
  'Finalizing analysis...',
];

export default function DemoModal({ isOpen, onClose }) {
  const [caseName, setCaseName] = useState('');
  const [hasWhatsApp, setHasWhatsApp] = useState(true);
  const [hasTelegram, setHasTelegram] = useState(true);
  const [step, setStep] = useState('idle'); // 'idle' | 'running' | 'done' | 'error'
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState(null);

  const timerRef = useRef(null);

  useEffect(() => {
    if (isOpen && step === 'idle') {
      setCaseName(`Demo Case - ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`);
      setHasWhatsApp(true);
      setHasTelegram(true);
      setProgress(0);
      setErrorMsg(null);
    }
  }, [isOpen, step]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  if (!isOpen) return null;

  const handleStartDemo = async (e) => {
    e.preventDefault();
    if (!hasWhatsApp && !hasTelegram) {
      setErrorMsg('Please select at least one data source (WhatsApp or Telegram).');
      return;
    }

    setStep('running');
    setProgress(0);
    setErrorMsg(null);

    // Advance step progress every 1.2 seconds while API call runs
    timerRef.current = setInterval(() => {
      setProgress((prev) => {
        if (prev < STEPS.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 1200);

    try {
      const result = await demoService.createDemoCase({
        case_name: caseName.trim() || `Demo Case - ${Date.now()}`,
        has_whatsapp: hasWhatsApp,
        has_telegram: hasTelegram,
        message_count: 100,
        contact_count: 15,
      });

      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      setProgress(STEPS.length);
      setStep('done');

      setTimeout(() => {
        window.location.href = `/cases/${result.case_id}/dashboard`;
      }, 600);
    } catch (err) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      setStep('error');
      const detail = err?.response?.data?.detail || err?.message || 'Failed to create demo case. Please check server logs.';
      setErrorMsg(detail);
    }
  };

  const handleReset = () => {
    setStep('idle');
    setProgress(0);
    setErrorMsg(null);
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in">
      <div className="bg-forensic-900 border border-forensic-800 rounded-xl shadow-2xl max-w-md w-full overflow-hidden animate-in">
        {/* Header */}
        <div className="px-6 py-4 border-b border-forensic-800 flex items-center justify-between bg-forensic-950/50">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-accent-cyan/10 flex items-center justify-center text-accent-cyan">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-forensic-100">Create Demo Case</h2>
              <p className="text-xs text-forensic-400">Generate realistic sample forensic data</p>
            </div>
          </div>
          {step !== 'running' && (
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-forensic-400 hover:text-forensic-200 hover:bg-forensic-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Content Body */}
        <div className="p-6">
          {step === 'idle' && (
            <form onSubmit={handleStartDemo} className="space-y-5">
              <div>
                <label className="block text-xs font-mono text-forensic-400 mb-1.5 uppercase tracking-wider">
                  Case Name
                </label>
                <input
                  type="text"
                  value={caseName}
                  onChange={(e) => setCaseName(e.target.value)}
                  placeholder="e.g. Demo Case - Suspect Alpha"
                  className="w-full bg-forensic-950 border border-forensic-800 rounded-lg px-3 py-2 text-sm text-forensic-100 placeholder-forensic-600 focus:outline-none focus:border-accent-cyan transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-forensic-400 mb-2 uppercase tracking-wider">
                  Data Sources to Include
                </label>
                <div className="space-y-2.5">
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-forensic-800 bg-forensic-950/40 hover:bg-forensic-950/80 cursor-pointer transition-colors">
                    <input
                      type="checkbox"
                      checked={hasWhatsApp}
                      onChange={(e) => setHasWhatsApp(e.target.checked)}
                      className="rounded border-forensic-700 text-accent-emerald focus:ring-accent-emerald focus:ring-offset-forensic-900"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-forensic-100">WhatsApp Data</span>
                        <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-accent-emerald/10 text-accent-emerald border border-accent-emerald/20">
                          Active
                        </span>
                      </div>
                      <p className="text-xs text-forensic-400 mt-0.5">
                        Includes messages, contacts, chat groups & sequence gaps
                      </p>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 p-3 rounded-lg border border-forensic-800 bg-forensic-950/40 hover:bg-forensic-950/80 cursor-pointer transition-colors">
                    <input
                      type="checkbox"
                      checked={hasTelegram}
                      onChange={(e) => setHasTelegram(e.target.checked)}
                      className="rounded border-forensic-700 text-accent-blue focus:ring-accent-blue focus:ring-offset-forensic-900"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-forensic-100">Telegram Data</span>
                        <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-accent-blue/10 text-accent-blue border border-accent-blue/20">
                          Active
                        </span>
                      </div>
                      <p className="text-xs text-forensic-400 mt-0.5">
                        Includes SQLite cache messages, users, timeline events
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              {errorMsg && (
                <div className="p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/30 text-accent-rose text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium rounded-lg text-forensic-300 hover:text-forensic-100 hover:bg-forensic-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary inline-flex items-center gap-2 text-xs px-4 py-2"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Start Demo Analysis
                </button>
              </div>
            </form>
          )}

          {step === 'running' && (
            <div className="py-2 space-y-4">
              <div className="flex items-center justify-between text-xs font-mono text-forensic-400 mb-2">
                <span>ANALYSIS IN PROGRESS</span>
                <span>{Math.min(100, Math.round(((progress + 1) / STEPS.length) * 100))}%</span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-forensic-950 rounded-full h-1.5 overflow-hidden border border-forensic-800">
                <div
                  className="bg-gradient-to-r from-accent-cyan to-accent-emerald h-full transition-all duration-300 ease-out"
                  style={{ width: `${Math.min(100, Math.round(((progress + 1) / STEPS.length) * 100))}%` }}
                />
              </div>

              {/* Steps List */}
              <div className="space-y-2 pt-2 max-h-60 overflow-y-auto pr-1">
                {STEPS.map((stepLabel, idx) => {
                  const isCompleted = idx < progress;
                  const isCurrent = idx === progress;

                  return (
                    <div
                      key={stepLabel}
                      className={`flex items-center gap-3 text-xs py-1.5 px-2.5 rounded-lg transition-colors ${
                        isCurrent
                          ? 'bg-accent-cyan/10 border border-accent-cyan/20 text-accent-cyan font-medium'
                          : isCompleted
                          ? 'text-accent-emerald'
                          : 'text-forensic-500'
                      }`}
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="w-4 h-4 shrink-0 text-accent-emerald" />
                      ) : isCurrent ? (
                        <Loader2 className="w-4 h-4 shrink-0 animate-spin text-accent-cyan" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-forensic-700 flex items-center justify-center shrink-0">
                          <div className="w-1.5 h-1.5 rounded-full bg-forensic-700" />
                        </div>
                      )}
                      <span>{stepLabel}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === 'done' && (
            <div className="py-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-accent-emerald/20 border border-accent-emerald/30 flex items-center justify-center mx-auto text-accent-emerald">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-forensic-100">Demo Case Ready!</h3>
                <p className="text-xs text-forensic-400 mt-1">
                  Redirecting to forensic dashboard...
                </p>
              </div>
            </div>
          )}

          {step === 'error' && (
            <div className="py-4 space-y-4">
              <div className="p-4 rounded-lg bg-accent-rose/10 border border-accent-rose/30 text-accent-rose text-xs space-y-2">
                <div className="flex items-center gap-2 font-semibold text-sm">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Demo Case Creation Failed</span>
                </div>
                <p className="text-forensic-300">{errorMsg}</p>
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium rounded-lg text-forensic-300 hover:text-forensic-100 hover:bg-forensic-800 transition-colors"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="btn-primary text-xs px-4 py-2"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
