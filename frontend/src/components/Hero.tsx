import React from 'react';
import { ArrowRight, ShieldCheck, Sparkles, AlertCircle, RefreshCw, CheckCircle2 } from 'lucide-react';
import { Inspection } from '../types';

interface HeroProps {
  onStartInspection: () => void;
  onTryHandover: () => void;
  inspections: Inspection[];
  onSelectInspection: (inspection: Inspection) => void;
}

export const Hero: React.FC<HeroProps> = ({
  onStartInspection,
  onTryHandover,
  inspections,
  onSelectInspection,
}) => {
  const latestInspection = inspections.length > 0 ? inspections[0] : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      {/* Top Tagline & Trust Layer Callout */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6 mb-10">
        <div className="max-w-3xl">
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tight text-white leading-[1.05] uppercase">
            See what the seller <br className="hidden sm:inline" />
            <span className="text-orange-500">won’t tell you</span> in <br className="hidden sm:inline" />
            one walkaround
          </h1>
          <p className="mt-5 text-base sm:text-xl text-neutral-400 max-w-xl font-normal">
            Film a car. Get an evidence-backed condition report powered by OpenCV, damage detection, and agentic vision.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              onClick={() => {
                if (latestInspection) {
                  onSelectInspection(latestInspection);
                } else {
                  onStartInspection();
                }
              }}
              className="px-6 py-3.5 rounded-full bg-white text-black font-bold text-sm tracking-wide uppercase hover:bg-neutral-200 transition-all shadow-lg active:scale-95"
            >
              See a Report
            </button>
            <button
              onClick={onStartInspection}
              className="px-6 py-3.5 rounded-full bg-orange-600 text-white font-bold text-sm tracking-wide uppercase hover:bg-orange-500 transition-all shadow-lg shadow-orange-600/30 flex items-center space-x-2 group active:scale-95"
            >
              <span>Start Inspection</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>

        {/* Trust Layer Pill (From UI Design Page 1) */}
        <div className="lg:max-w-xs bg-neutral-900/90 border border-neutral-800 rounded-2xl p-5 backdrop-blur-sm self-start">
          <div className="text-[11px] font-mono font-bold text-orange-500 uppercase tracking-widest mb-1">
            / TRUST LAYER
          </div>
          <p className="text-xs font-semibold uppercase leading-relaxed text-neutral-300">
            Single-use capture code, video SHA-256 and a signed report, so a walkaround is harder to fake.
          </p>
        </div>
      </div>

      {/* Feature Preview Cards Grid (Matches UI Design Page 1) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 mt-8">
        {/* Card 1: Condition Score Card */}
        <div 
          onClick={() => latestInspection && onSelectInspection(latestInspection)}
          className="md:col-span-3 bg-neutral-900 border border-neutral-800 rounded-3xl p-6 flex flex-col justify-between hover:border-neutral-700 transition-all cursor-pointer group"
        >
          <div>
            <div className="text-[11px] font-mono tracking-widest text-neutral-400 uppercase">
              Condition Score
            </div>
            <div className="mt-3 flex items-baseline space-x-1">
              {latestInspection?.carDetected === false ? (
                <span className="text-2xl font-black text-red-400 tracking-tight">
                  No Car Detected
                </span>
              ) : (
                <>
                  <span className="text-5xl font-black text-orange-500 tracking-tight">
                    {latestInspection?.score ?? 82}
                  </span>
                  <span className="text-neutral-500 font-bold text-lg">/100</span>
                </>
              )}
            </div>
          </div>
          <div className="mt-6 pt-4 border-t border-neutral-800/80">
            <p className="text-xs text-neutral-300 font-medium">
              {latestInspection?.carDetected === false
                ? "No vehicle recognized in walkaround footage"
                : (latestInspection?.report?.scoreSummary || "Possible repaint: right front door")}
            </p>
            <div className="mt-2 text-[11px] text-neutral-500">
              {latestInspection ? `${latestInspection.carMake} ${latestInspection.carModel}` : "Sample Toyota CH-R"}
            </div>
          </div>
        </div>

        {/* Card 2: Center Walkaround Visual Hero Card */}
        <div className="md:col-span-6 bg-gradient-to-tr from-amber-950/40 via-orange-950/20 to-neutral-900 border border-neutral-800 rounded-3xl overflow-hidden relative min-h-[220px] flex flex-col justify-end p-6">
          <div className="absolute inset-0 bg-[radial-gradient(#ea580c_1px,transparent_1px)] [background-size:16px_16px] opacity-20"></div>
          
          <div className="relative z-10">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-black/60 border border-neutral-700 text-xs font-medium text-neutral-300 mb-3 backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-orange-500"></span>
              <span>8-Viewpoint Continuous Scan</span>
            </div>
            <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Deterministic evidence, generative explanation
            </h3>
            <p className="text-xs sm:text-sm text-neutral-400 mt-1">
              Measurements computed strictly by OpenCV & detector; reconciled by Bedrock AI with strict grounding guardrails.
            </p>
          </div>
        </div>

        {/* Card 3: Handover Mode Card */}
        <div className="md:col-span-3 bg-neutral-900 border border-neutral-800 rounded-3xl p-6 flex flex-col justify-between hover:border-neutral-700 transition-all">
          <div>
            <div className="text-[11px] font-mono tracking-widest text-orange-500 uppercase">
              Handover Mode
            </div>
            <h3 className="mt-3 text-lg font-bold text-white leading-snug">
              Compare pickup and return. See only new damage.
            </h3>
          </div>
          <div className="mt-6">
            <button
              onClick={onTryHandover}
              className="w-full py-2.5 rounded-full bg-neutral-800 hover:bg-neutral-700 text-white font-bold text-xs tracking-wider uppercase transition-colors"
            >
              Try It →
            </button>
          </div>
        </div>
      </div>

      {/* Recent Inspections Table */}
      {inspections.length > 0 && (
        <div className="mt-14">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold tracking-tight text-white uppercase">
              Recent Inspections ({inspections.length})
            </h2>
            <button
              onClick={onStartInspection}
              className="text-xs font-semibold text-orange-400 hover:text-orange-300 transition-colors"
            >
              + New Inspection
            </button>
          </div>

          <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl overflow-hidden divide-y divide-neutral-800">
            {inspections.map((insp) => (
              <div
                key={insp.inspectionId}
                onClick={() => onSelectInspection(insp)}
                className="p-4 sm:px-6 flex items-center justify-between hover:bg-neutral-800/40 transition-colors cursor-pointer"
              >
                <div className="flex items-center space-x-4">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${
                    insp.carDetected === false
                      ? 'bg-red-950/60 text-red-400 border border-red-800/60'
                      : 'bg-neutral-800 text-orange-400'
                  }`}>
                    {insp.carDetected === false ? 'N/A' : (insp.score ? `${insp.score}` : '—')}
                  </div>
                  <div>
                    <div className="font-bold text-sm sm:text-base text-white">
                      {insp.year} {insp.carMake} {insp.carModel}
                    </div>
                    <div className="text-xs text-neutral-400 flex items-center space-x-2 mt-0.5">
                      <span>{insp.type}</span>
                      <span>•</span>
                      <span>{insp.createdAt.split('T')[0]}</span>
                      {insp.carDetected === false ? (
                        <>
                          <span>•</span>
                          <span className="font-semibold text-red-400">No Car Detected</span>
                        </>
                      ) : insp.trustLevel ? (
                        <>
                          <span>•</span>
                          <span className={`font-semibold ${
                            insp.trustLevel === 'VERIFIED' ? 'text-emerald-400' :
                            insp.trustLevel === 'PARTIAL' ? 'text-amber-400' : 'text-rose-400'
                          }`}>
                            {insp.trustLevel}
                          </span>
                        </>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium uppercase ${
                    insp.carDetected === false ? 'bg-red-950/60 text-red-400 border border-red-800/60' :
                    insp.status === 'DONE' ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60' :
                    insp.status === 'PROCESSING' ? 'bg-orange-950/60 text-orange-400 border border-orange-800/60 animate-pulse' :
                    insp.status === 'NEEDS_RETAKE' ? 'bg-amber-950/60 text-amber-400 border border-amber-800/60' :
                    'bg-neutral-800 text-neutral-400'
                  }`}>
                    {insp.carDetected === false ? 'No Car Detected' : insp.status}
                  </span>
                  <ArrowRight className="w-4 h-4 text-neutral-500" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
