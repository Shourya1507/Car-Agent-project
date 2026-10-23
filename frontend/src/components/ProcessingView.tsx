import React, { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, Sparkles, AlertCircle } from 'lucide-react';

interface ProcessingViewProps {
  inspectionId: string;
  isComparison: boolean;
  onComplete: () => void;
  onRetakeNeeded?: (missingViewpoints: string[]) => void;
}

const STAGES = [
  { id: 'validate', label: 'Validate Upload & Video Duration', time: 1000 },
  { id: 'extract', label: 'Extract Frames & Quality Gate (Laplacian, Exposure)', time: 2000 },
  { id: 'viewpoints', label: '8-Viewpoint Classification & Coverage Gate', time: 1500 },
  { id: 'parallel', label: 'Parallel Analysis (YOLO CarDD, OpenCV Seams, Integrity)', time: 2500 },
  { id: 'handover', label: 'Handover Comparison (ORB + RANSAC Homography)', time: 2000, condition: 'comparison' },
  { id: 'agent', label: 'Bedrock Agent Reasoning & Grounding Guardrails', time: 2500 },
  { id: 'render', label: 'ECDSA P-256 Signing & Report PDF Render', time: 1500 },
];

export const ProcessingView: React.FC<ProcessingViewProps> = ({
  inspectionId,
  isComparison,
  onComplete,
  onRetakeNeeded,
}) => {
  const [activeStageIdx, setActiveStageIdx] = useState(0);

  const filteredStages = STAGES.filter((s) => !s.condition || (s.condition === 'comparison' && isComparison));

  useEffect(() => {
    let current = 0;
    const executeNextStage = () => {
      if (current < filteredStages.length - 1) {
        current += 1;
        setActiveStageIdx(current);
        setTimeout(executeNextStage, filteredStages[current].time);
      } else {
        // Complete
        setTimeout(onComplete, 1000);
      }
    };

    const timer = setTimeout(executeNextStage, filteredStages[0].time);
    return () => clearTimeout(timer);
  }, [filteredStages.length]);

  return (
    <div className="max-w-xl mx-auto px-4 py-16 text-center">
      <div className="w-16 h-16 rounded-2xl bg-orange-600/20 border border-orange-500/30 flex items-center justify-center text-orange-500 mx-auto mb-6 shadow-xl">
        <Sparkles className="w-8 h-8 animate-spin" />
      </div>

      <h2 className="text-2xl sm:text-3xl font-black text-white uppercase tracking-tight">
        Processing Walkaround
      </h2>
      <p className="text-xs sm:text-sm text-neutral-400 mt-2 font-mono">
        Inspection ID: {inspectionId}
      </p>

      {/* Step Indicators */}
      <div className="mt-10 bg-neutral-900/80 border border-neutral-800 rounded-3xl p-6 text-left space-y-4">
        {filteredStages.map((stage, idx) => {
          const isDone = idx < activeStageIdx;
          const isCurrent = idx === activeStageIdx;

          return (
            <div
              key={stage.id}
              className={`flex items-center space-x-3 transition-opacity ${
                isCurrent ? 'opacity-100' : isDone ? 'opacity-80' : 'opacity-40'
              }`}
            >
              {isDone ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
              ) : isCurrent ? (
                <Loader2 className="w-5 h-5 text-orange-500 animate-spin flex-shrink-0" />
              ) : (
                <div className="w-5 h-5 rounded-full border border-neutral-700 flex-shrink-0" />
              )}
              <span
                className={`text-xs sm:text-sm font-medium ${
                  isCurrent ? 'text-white font-bold' : isDone ? 'text-neutral-300' : 'text-neutral-500'
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-8 text-xs text-neutral-500">
        Asynchronous Step Functions execution. Total runtime budget &lt; 60 seconds.
      </div>
    </div>
  );
};
