import React, { useState, useEffect, useCallback } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { timelineService } from '../services/timelineService';

export default function TimelinePage() {
  const { activeCase } = useActiveCase();

  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [appFilter, setAppFilter] = useState('All');
  const [strengthFilter, setStrengthFilter] = useState('All');
  const [search, setSearch] = useState('');

  const caseId = activeCase?.id;

  const loadTimeline = useCallback(async () => {
    if (!caseId) {
      setEvents([]);
      return;
    }
    setLoading(true);
    try {
      const data = await timelineService.getTimeline(caseId);
      if (Array.isArray(data)) {
        setEvents(data);
      } else if (data?.events && Array.isArray(data.events)) {
        setEvents(data.events);
      } else {
        setEvents([]);
      }
    } catch (err) {
      console.warn('Error fetching timeline events from API:', err);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  const handleRebuild = async () => {
    if (!caseId) return;
    setRebuilding(true);
    try {
      await timelineService.buildTimeline(caseId);
      await loadTimeline();
    } catch (err) {
      console.error('Failed to rebuild timeline:', err);
    } finally {
      setRebuilding(false);
    }
  };

  const filteredEvents = events.filter((e) => {
    if (e.isGap) return true;
    const app = e.app || (e.source_type?.toLowerCase().includes('wa') ? 'WhatsApp' : 'Telegram');
    if (appFilter !== 'All' && app !== appFilter) return false;
    const strength = e.strength || (e.confidence_score >= 0.95 ? 'Deterministic' : 'Strong');
    if (strengthFilter !== 'All' && strength !== strengthFilter) return false;
    const content = e.content || e.message_text || e.summary || '';
    const actor = e.actor || e.sender || e.source_identifier || '';
    if (search && !content.toLowerCase().includes(search.toLowerCase()) && !actor.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Action Bar */}
      <section className="border-b border-outline-variant bg-surface-container px-space-lg py-2.5 space-y-2.5 shrink-0">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-headline-md font-headline-md text-on-surface font-semibold">
                Forensic Chronological Timeline
              </h1>
              {events.length > 0 && (
                <span className="px-2 py-0.5 text-label-ui rounded bg-tertiary/10 border border-tertiary/30 text-tertiary flex items-center gap-1 text-xs">
                  <span className="material-symbols-outlined text-[13px]">check_circle</span>
                  Reconstructed
                </span>
              )}
            </div>
            <p className="text-body-sm text-on-surface-variant mt-0.5">
              Multi-source chronological timeline across forensic evidence databases for case {activeCase?.caseNumber || 'N/A'}.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {activeCase?.sha256Root && (
              <div className="flex items-center h-8 px-2 rounded bg-surface-container-lowest border border-outline-variant font-mono text-xs text-on-surface-variant">
                <span className="text-outline mr-1">ROOT:</span>
                <span className="text-on-surface mr-1.5 font-medium">{activeCase.sha256Root.substring(0, 12)}...</span>
                <button
                  type="button"
                  onClick={() => navigator.clipboard?.writeText(activeCase.sha256Root)}
                  className="hover:text-primary transition-colors cursor-pointer"
                  title="Copy Hash"
                >
                  <span className="material-symbols-outlined text-[13px]">content_copy</span>
                </button>
              </div>
            )}

            <button
              type="button"
              disabled={rebuilding || !caseId}
              onClick={handleRebuild}
              className="btn-secondary text-xs h-8 flex items-center gap-1.5"
            >
              <span className={`material-symbols-outlined text-[14px] ${rebuilding ? 'animate-spin' : ''}`}>sync</span>
              <span>{rebuilding ? 'Rebuilding...' : 'Rebuild Timeline'}</span>
            </button>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-outline-variant/60">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={appFilter}
              onChange={(e) => setAppFilter(e.target.value)}
              className="h-7 px-2.5 rounded bg-surface-container-lowest border border-outline-variant text-[11px] text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="All">App: All (WhatsApp, Telegram)</option>
              <option value="WhatsApp">WhatsApp Only</option>
              <option value="Telegram">Telegram Only</option>
            </select>

            <select
              value={strengthFilter}
              onChange={(e) => setStrengthFilter(e.target.value)}
              className="h-7 px-2.5 rounded bg-surface-container-lowest border border-outline-variant text-[11px] text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="All">Strength: All Heuristics</option>
              <option value="Deterministic">Deterministic (&gt;= 0.95)</option>
              <option value="Strong">Strong (&gt;= 0.80)</option>
            </select>

            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-2 text-[14px] text-outline">search</span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search timeline text, participant..."
                className="h-7 pl-7 pr-3 rounded bg-surface-container-lowest border border-outline-variant text-on-surface placeholder:text-outline text-[11px] focus:outline-none focus:border-primary w-64"
              />
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-label-ui text-outline text-xs">
            <span>Indexed Chrono Events:</span>
            <span className="text-primary font-mono font-semibold">{filteredEvents.length}</span>
          </div>
        </div>
      </section>

      {/* Visual Chronological Timeline Feed */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {loading && (
            <div className="py-12 text-center text-on-surface-variant font-mono text-sm">
              <span className="material-symbols-outlined text-3xl animate-spin text-primary mb-2">sync</span>
              <p>Reconstructing chronological timeline from database records...</p>
            </div>
          )}

          {!loading && filteredEvents.length === 0 && (
            <div className="py-16 text-center text-on-surface-variant border border-dashed border-outline-variant rounded-lg bg-surface-container-low p-8">
              <span className="material-symbols-outlined text-4xl text-outline mb-3">timeline</span>
              <h3 className="text-body-lg font-medium text-on-surface">No Timeline Events Recorded</h3>
              <p className="text-body-sm text-on-surface-variant max-w-md mx-auto mt-1 mb-4">
                No events found matching the current criteria. Ingest evidence files and run the extraction pipeline to construct the forensic timeline.
              </p>
              {caseId && (
                <button
                  type="button"
                  onClick={handleRebuild}
                  className="btn-primary text-xs h-8 inline-flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[14px]">play_arrow</span>
                  Build Timeline Now
                </button>
              )}
            </div>
          )}

          {!loading && filteredEvents.map((item, idx) => {
            const eventId = item.id || `ev-${idx}`;
            if (item.isGap) {
              return (
                <div
                  key={eventId}
                  className="p-3 rounded-lg border border-dashed border-amber-600/50 bg-amber-950/15 flex items-center gap-3 text-amber-200 text-xs my-3"
                >
                  <span className="material-symbols-outlined text-amber-400 text-lg">timelapse</span>
                  <div className="flex-1">
                    <div className="font-semibold text-amber-300">
                      Forensic Inactivity Gap Detected: {item.duration || 'Inactivity Interval'}
                    </div>
                    <p className="text-on-surface-variant text-[11px] mt-0.5">{item.note || item.description}</p>
                  </div>
                  <span className="font-mono text-[10px] text-amber-400/80">{item.range || ''}</span>
                </div>
              );
            }

            const app = item.app || (item.source_type?.toLowerCase().includes('wa') ? 'WhatsApp' : 'Telegram');
            const actor = item.actor || item.sender || item.source_identifier || 'Unknown Participant';
            const content = item.content || item.message_text || item.summary || '[Payload data]';
            const timestamp = item.timestamp || item.created_at || 'Undated';
            const strength = item.strength || (item.confidence_score >= 0.95 ? 'Deterministic' : 'Strong');
            const strengthScore = item.strengthScore ?? item.confidence_score ?? 1.0;

            return (
              <div
                key={eventId}
                className={`p-4 rounded-lg border bg-surface-container transition-all hover:border-primary/50 space-y-2 ${
                  item.isCarved || item.is_carved ? 'border-amber-600/40 bg-amber-950/10' : 'border-outline-variant'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant/60 pb-2">
                  <div className="flex items-center gap-2">
                    <span className={`material-symbols-outlined text-sm ${
                      app === 'WhatsApp' ? 'text-emerald-400' : 'text-blue-400'
                    }`}>
                      {app === 'WhatsApp' ? 'chat' : 'send'}
                    </span>
                    <span className="font-semibold text-on-surface text-sm">{actor}</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-surface-container-high border border-outline-variant text-on-surface-variant">
                      {item.type || item.event_type || 'Message'}
                    </span>
                    {(item.isCarved || item.is_carved) && (
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-amber-500/20 text-amber-400 border border-amber-500/40 font-semibold">
                        CARVED RESIDUAL
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 font-mono text-xs text-on-surface-variant">
                    <span className="text-on-surface">{timestamp}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      strength === 'Deterministic'
                        ? 'bg-tertiary/10 text-tertiary border border-tertiary/30'
                        : 'bg-primary/10 text-primary border border-primary/30'
                    }`}>
                      {strength} ({(strengthScore * 100).toFixed(0)}%)
                    </span>
                  </div>
                </div>

                <p className="text-body-md text-on-surface leading-relaxed text-sm select-text">
                  {content}
                </p>

                <div className="pt-1 flex items-center justify-between font-mono text-[10px] text-outline">
                  <span>RowID: {item.rowid || item.record_id || item.id || 'N/A'}</span>
                  {item.hash && (
                    <div className="flex items-center gap-1">
                      <span>SHA-256:</span>
                      <span className="text-on-surface-variant">{item.hash.substring(0, 24)}...</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
