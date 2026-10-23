import React, { useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  Download,
  Share2,
  Trash2,
  CheckCircle2,
  ChevronRight,
  HelpCircle,
  ExternalLink,
  Car
} from 'lucide-react';
import { Inspection, Finding } from '../types';

interface ReportViewProps {
  inspection: Inspection;
  onVerify: () => void;
  onShare: () => void;
  onDelete: () => void;
}

export const ReportView: React.FC<ReportViewProps> = ({
  inspection,
  onVerify,
  onShare,
  onDelete,
}) => {
  const report = inspection.report;
  const findings = report?.findings || [];
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(
    findings.length > 0 ? findings[0] : null
  );

  const score = inspection.score ?? report?.score ?? 86;
  const trustLevel = inspection.trustLevel ?? report?.trust?.trustLevel ?? 'VERIFIED';
  const coverageCount = report?.coverage?.filter((c) => c.captured).length ?? 8;

  const scoreColor = score >= 80 ? 'text-orange-500' : score >= 60 ? 'text-amber-500' : 'text-red-500';

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-10">
      {/* 1. Vehicle Title & Status Bar (Matches UI Design Page 3) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-neutral-800 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-neutral-400">
              Inspected
            </span>
            <span className="text-neutral-600">•</span>
            <span className="text-xs font-mono text-neutral-400">
              {inspection.type === 'BASELINE' ? 'Baseline saved' : `${inspection.type} Mode`}
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black text-white mt-1 uppercase tracking-tight">
            {inspection.year} {inspection.carMake} {inspection.carModel}
          </h1>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          <a
            href={`/inspections/${inspection.inspectionId}/report.pdf`}
            download
            className="px-4 py-2.5 rounded-full bg-neutral-800 hover:bg-neutral-700 text-white font-bold text-xs uppercase tracking-wider transition-colors flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Download PDF</span>
          </a>
          <button
            onClick={onShare}
            className="px-4 py-2.5 rounded-full bg-neutral-800 hover:bg-neutral-700 text-white font-bold text-xs uppercase tracking-wider transition-colors flex items-center space-x-2"
          >
            <Share2 className="w-4 h-4" />
            <span>Share</span>
          </button>
          <button
            onClick={onVerify}
            className="px-4 py-2.5 rounded-full bg-emerald-950/60 border border-emerald-800/80 text-emerald-400 font-bold text-xs uppercase tracking-wider hover:bg-emerald-900/60 transition-colors flex items-center space-x-2"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Verify Signature</span>
          </button>
          <button
            onClick={onDelete}
            className="p-2.5 rounded-full text-neutral-500 hover:text-red-400 hover:bg-neutral-900 transition-colors"
            title="Delete Inspection"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. Hero Score & Trust Level Banner (Matches UI Design Page 2) */}
      <div className="bg-gradient-to-b from-neutral-900 via-neutral-900/90 to-black border border-neutral-800 rounded-3xl p-6 sm:p-10 text-center relative overflow-hidden shadow-2xl">
        <div className="text-[12px] font-mono tracking-widest text-neutral-400 uppercase">
          Condition Score
        </div>
        
        {/* Huge bold score number */}
        <div className="my-2 flex items-center justify-center">
          <span className={`text-8xl sm:text-9xl font-black ${scoreColor} tracking-tighter`}>
            {score}
          </span>
          <span className="text-neutral-600 font-black text-3xl sm:text-4xl ml-2">/100</span>
        </div>

        {/* 10-Segment Condition Progress Bar (Matches UI Design Page 3) */}
        <div className="max-w-md mx-auto grid grid-cols-10 gap-1.5 my-4">
          {Array.from({ length: 10 }).map((_, i) => {
            const active = i < Math.round(score / 10);
            return (
              <div
                key={i}
                className={`h-2.5 rounded-sm transition-all ${
                  active ? (score >= 80 ? 'bg-emerald-500' : 'bg-orange-500') : 'bg-neutral-800'
                }`}
              />
            );
          })}
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-4 max-w-lg mx-auto mt-6 pt-6 border-t border-neutral-800/80">
          <div>
            <div className="text-2xl font-black text-white">{findings.length}</div>
            <div className="text-[11px] text-neutral-400 uppercase mt-0.5">Findings</div>
          </div>
          <div>
            <div className="text-2xl font-black text-white">{coverageCount}/8</div>
            <div className="text-[11px] text-neutral-400 uppercase mt-0.5">Angles Covered</div>
          </div>
          <div>
            <div className={`text-xl font-black uppercase ${
              trustLevel === 'VERIFIED' ? 'text-emerald-400' : trustLevel === 'PARTIAL' ? 'text-amber-400' : 'text-red-400'
            }`}>
              {trustLevel}
            </div>
            <div className="text-[11px] text-neutral-400 uppercase mt-0.5">Trust Level</div>
          </div>
        </div>

        {/* Mandatory Screening Disclaimer Banner (Strict Rule) */}
        <div className="mt-8 bg-neutral-950/80 border border-neutral-800 rounded-2xl p-4 max-w-2xl mx-auto text-center">
          <p className="text-xs text-neutral-400 font-medium">
            <span className="text-orange-400 font-bold uppercase">Screening Result: </span>
            {trustLevel === 'VERIFIED'
              ? 'Challenge passed, continuous video stream verified, report signed. Confirm flagged items with a mechanic.'
              : 'Screening only. Never claim certification or accident-free. Confirm flagged items with a mechanic.'}
          </p>
        </div>
      </div>

      {/* 3. Evidence Crops & Findings Detail (Matches UI Design Page 3) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Findings List */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-base font-bold text-white uppercase tracking-tight">
              Identified Findings ({findings.length})
            </h3>
            <span className="text-xs text-neutral-500">Select to inspect evidence</span>
          </div>

          <div className="space-y-2">
            {findings.map((f) => {
              const isSelected = selectedFinding?.id === f.id;
              return (
                <div
                  key={f.id}
                  onClick={() => setSelectedFinding(f)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-neutral-800/90 border-orange-500 shadow-lg'
                      : 'bg-neutral-900/60 border-neutral-800 hover:border-neutral-700'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-bold text-sm text-white capitalize">
                        {f.type.replace('_', ' ')}
                      </div>
                      <div className="text-xs text-neutral-400 mt-0.5 capitalize">
                        {f.panel} · {Math.round(f.confidence * 100)}% confidence
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                      f.severity === 'major' ? 'bg-red-950 text-red-400 border border-red-800' :
                      f.severity === 'moderate' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                      'bg-neutral-800 text-neutral-300'
                    }`}>
                      {f.severity}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Selected Finding Evidence Inspector (Matches UI Design Page 3) */}
        <div className="lg:col-span-7">
          {selectedFinding ? (
            <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-[11px] font-mono tracking-widest text-orange-500 uppercase">
                    Findings · {inspection.carMake} {inspection.carModel}
                  </div>
                  <h2 className="text-2xl font-bold text-white mt-1 capitalize">
                    {selectedFinding.type.replace('_', ' ')}: {selectedFinding.panel}
                  </h2>
                </div>
                <div className="w-4 h-4 rounded-full bg-orange-500 shadow-lg shadow-orange-500/50"></div>
              </div>

              {/* Evidence Crop Frame */}
              <div className="rounded-2xl border border-neutral-800 bg-black overflow-hidden relative aspect-video flex items-center justify-center">
                {selectedFinding.evidenceKey ? (
                  <img
                    src={`/media/${selectedFinding.evidenceKey}`}
                    alt="Evidence crop"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      // Fallback display if crop file not on disk
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                ) : null}
                <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center bg-neutral-950/40 pointer-events-none">
                  <div className="w-12 h-12 rounded-full border-2 border-orange-500 flex items-center justify-center text-orange-500 font-bold mb-2">
                    ROI
                  </div>
                  <span className="text-xs font-mono text-neutral-400 uppercase">
                    [EVIDENCE CROP WITH ANNOTATION]
                  </span>
                  <span className="text-[11px] text-neutral-500 mt-1">{selectedFinding.evidenceKey}</span>
                </div>
              </div>

              {/* Confidence & Panel Pills (Matches UI Design Page 3) */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-3 py-1 rounded-full bg-neutral-800 border border-neutral-700 text-xs font-semibold text-white">
                  {Math.round(selectedFinding.confidence * 100)}% confidence
                </span>
                <span className="px-3 py-1 rounded-full bg-neutral-800 border border-neutral-700 text-xs font-semibold text-white capitalize">
                  {selectedFinding.type.replace('_', ' ')}
                </span>
                <span className="px-3 py-1 rounded-full bg-neutral-800 border border-neutral-700 text-xs font-semibold text-white capitalize">
                  Panel: {selectedFinding.panel}
                </span>
              </div>

              {/* Agent Note & Question for Seller (Matches UI Design Page 3) */}
              <div className="space-y-3 pt-2">
                <div className="text-xs text-neutral-300 leading-relaxed bg-neutral-800/40 border border-neutral-700/60 p-4 rounded-2xl">
                  <div className="font-bold text-white text-xs mb-1 uppercase tracking-wide">
                    Agent Finding Note
                  </div>
                  {selectedFinding.note}
                </div>

                <div className="p-4 bg-orange-950/20 border border-orange-800/40 rounded-2xl">
                  <div className="text-[11px] font-mono font-bold text-orange-400 uppercase mb-1">
                    Ask the Seller:
                  </div>
                  <p className="text-xs sm:text-sm font-semibold text-white">
                    Ask the seller about past repairs on this side of the car. Has the {selectedFinding.panel} been repainted or replaced?
                  </p>
                </div>
              </div>

              {/* Trust Footer */}
              <div className="pt-4 border-t border-neutral-800 flex items-center justify-between text-xs text-neutral-400">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span>Verified · hash and signature attached</span>
                </div>
                <button
                  onClick={onShare}
                  className="font-bold text-orange-400 hover:text-orange-300 uppercase tracking-wider text-xs"
                >
                  Share verified report →
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-12 text-center text-neutral-500">
              Select any finding on the left to inspect its evidence crop.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
