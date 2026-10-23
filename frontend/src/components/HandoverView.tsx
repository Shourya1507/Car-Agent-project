import React, { useState } from 'react';
import { Layers, ArrowRight, ShieldCheck, AlertCircle, CheckCircle2, SplitSquareVertical } from 'lucide-react';
import { Inspection, ChangeItem } from '../types';

interface HandoverViewProps {
  inspections: Inspection[];
  onStartComparison: () => void;
}

export const HandoverView: React.FC<HandoverViewProps> = ({ inspections, onStartComparison }) => {
  const comparisonInspections = inspections.filter((i) => i.type === 'COMPARISON');
  const baselineInspections = inspections.filter((i) => i.type === 'BASELINE');

  const [selectedInspection, setSelectedInspection] = useState<Inspection | null>(
    comparisonInspections[0] || inspections[0] || null
  );

  const changes: ChangeItem[] = selectedInspection?.report?.changes || [
    {
      findingId: 'fnd_mock_1',
      changeStatus: 'NEW',
      panel: 'right door',
      type: 'scratch',
      confidence: 0.88,
      baselineEvidenceKey: 'evidence/baseline/door.jpg',
      returnEvidenceKey: 'evidence/return/door_scratch.jpg',
      alignmentQuality: 0.85,
      note: 'NEW scratch detected on right door (34mm length) not present in baseline pickup inspection.',
    },
    {
      findingId: 'fnd_mock_2',
      changeStatus: 'PRE-EXISTING',
      panel: 'front bumper',
      type: 'dent',
      confidence: 0.92,
      baselineEvidenceKey: 'evidence/baseline/bumper_dent.jpg',
      returnEvidenceKey: 'evidence/return/bumper_dent.jpg',
      alignmentQuality: 0.78,
      note: 'Pre-existing minor dent on front bumper verified from baseline pickup footage.',
    },
    {
      findingId: 'fnd_mock_3',
      changeStatus: 'UNCERTAIN',
      panel: 'rear-right quarter panel',
      type: 'paint_mismatch',
      confidence: 0.42,
      baselineEvidenceKey: undefined,
      returnEvidenceKey: 'evidence/return/rear_quarter.jpg',
      alignmentQuality: 0.32,
      note: 'Viewpoint alignment below inlier threshold (<40 inliers); angle varied significantly.',
    },
  ];

  const newCount = changes.filter((c) => c.changeStatus === 'NEW').length;
  const preExistingCount = changes.filter((c) => c.changeStatus === 'PRE-EXISTING').length;
  const resolvedCount = changes.filter((c) => c.changeStatus === 'RESOLVED').length;
  const uncertainCount = changes.filter((c) => c.changeStatus === 'UNCERTAIN').length;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-neutral-800 gap-4">
        <div>
          <div className="text-[11px] font-mono font-bold tracking-widest text-orange-500 uppercase">
            Handover Mode (FR19 - FR22)
          </div>
          <h1 className="text-3xl sm:text-4xl font-black text-white mt-1 uppercase tracking-tight">
            Baseline vs Return Comparison
          </h1>
          <p className="text-sm text-neutral-400 mt-1 max-w-xl">
            Compare rental or fleet pickup with return walkaround. Automatically aligns frames with ORB + RANSAC homography and reports only what changed.
          </p>
        </div>

        <button
          onClick={onStartComparison}
          className="px-5 py-3 rounded-full bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs uppercase tracking-wider transition-all shadow-lg shadow-orange-600/30 flex items-center space-x-2"
        >
          <Layers className="w-4 h-4" />
          <span>New Handover Check</span>
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5">
          <div className="text-xs font-mono text-red-400 uppercase font-bold">NEW Damage</div>
          <div className="text-3xl font-black text-white mt-1">{newCount}</div>
          <div className="text-[11px] text-neutral-500 mt-0.5">Added since pickup</div>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5">
          <div className="text-xs font-mono text-emerald-400 uppercase font-bold">PRE-EXISTING</div>
          <div className="text-3xl font-black text-white mt-1">{preExistingCount}</div>
          <div className="text-[11px] text-neutral-500 mt-0.5">Verified on baseline</div>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5">
          <div className="text-xs font-mono text-sky-400 uppercase font-bold">RESOLVED</div>
          <div className="text-3xl font-black text-white mt-1">{resolvedCount}</div>
          <div className="text-[11px] text-neutral-500 mt-0.5">Repaired / gone</div>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5">
          <div className="text-xs font-mono text-amber-400 uppercase font-bold">UNCERTAIN</div>
          <div className="text-3xl font-black text-white mt-1">{uncertainCount}</div>
          <div className="text-[11px] text-neutral-500 mt-0.5">Poor alignment / angle</div>
        </div>
      </div>

      {/* Changes Comparison Feed */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white uppercase tracking-tight">
            Comparison Results ({changes.length})
          </h2>
          <span className="text-xs text-neutral-400">Homography RANSAC threshold 4.0px</span>
        </div>

        <div className="space-y-4">
          {changes.map((item, idx) => (
            <div
              key={idx}
              className="bg-neutral-800/40 border border-neutral-700/60 rounded-2xl p-5 space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-3">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                      item.changeStatus === 'NEW'
                        ? 'bg-red-950 text-red-400 border border-red-800'
                        : item.changeStatus === 'PRE-EXISTING'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : item.changeStatus === 'RESOLVED'
                        ? 'bg-sky-950 text-sky-400 border border-sky-800'
                        : 'bg-amber-950 text-amber-400 border border-amber-800'
                    }`}
                  >
                    {item.changeStatus}
                  </span>
                  <span className="font-bold text-white capitalize text-sm">
                    {item.type.replace('_', ' ')} · {item.panel}
                  </span>
                </div>
                <div className="text-xs font-mono text-neutral-400">
                  Confidence: <span className="text-white font-bold">{Math.round(item.confidence * 100)}%</span> | Alignment Quality: <span className="text-white font-bold">{Math.round(item.alignmentQuality * 100)}%</span>
                </div>
              </div>

              {/* Side-by-Side Before / After View (FR21) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                {/* Baseline (Pickup) Crop */}
                <div className="bg-black/60 border border-neutral-700/80 rounded-xl p-3 text-center">
                  <div className="text-[11px] font-mono text-neutral-400 uppercase mb-2">
                    Baseline (Pickup) Frame
                  </div>
                  <div className="aspect-video bg-neutral-950 rounded-lg flex items-center justify-center border border-neutral-800 relative">
                    {item.changeStatus === 'NEW' ? (
                      <span className="text-xs text-neutral-500 font-mono">No defect in baseline</span>
                    ) : (
                      <span className="text-xs text-emerald-400 font-mono">[BASELINE EVIDENCE CROP]</span>
                    )}
                  </div>
                </div>

                {/* Return Frame */}
                <div className="bg-black/60 border border-neutral-700/80 rounded-xl p-3 text-center">
                  <div className="text-[11px] font-mono text-neutral-400 uppercase mb-2">
                    Return Frame
                  </div>
                  <div className="aspect-video bg-neutral-950 rounded-lg flex items-center justify-center border border-neutral-800 relative">
                    <span className="text-xs text-orange-400 font-mono">[RETURN EVIDENCE CROP]</span>
                  </div>
                </div>
              </div>

              <div className="text-xs text-neutral-300 bg-neutral-900/60 p-3 rounded-xl border border-neutral-800">
                <span className="font-bold text-white uppercase mr-1">Finding Analysis:</span>
                {item.note}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
