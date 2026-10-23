import React from 'react';
import { Camera, AlertCircle, RefreshCw, X } from 'lucide-react';

interface RetakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  missingViewpoints: string[];
  retakeRound: number;
  onConfirmRetake: (viewpoints: string[]) => void;
}

export const RetakeModal: React.FC<RetakeModalProps> = ({
  isOpen,
  onClose,
  missingViewpoints,
  retakeRound,
  onConfirmRetake,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
      <div className="bg-neutral-900 border border-neutral-800 rounded-3xl max-w-md w-full p-6 text-center shadow-2xl">
        <div className="w-14 h-14 rounded-2xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-500 mx-auto mb-4">
          <AlertCircle className="w-7 h-7" />
        </div>

        <h3 className="text-xl font-bold text-white uppercase tracking-tight">
          Retake Needed (Round {retakeRound + 1}/2)
        </h3>
        <p className="text-xs text-neutral-400 mt-2">
          The quality gate found blurry or missing viewpoints. To ensure an honest screening report, please capture the missing angle:
        </p>

        <div className="my-6 bg-neutral-800/80 border border-neutral-700/80 rounded-2xl p-4 text-left divide-y divide-neutral-700">
          {missingViewpoints.map((vp) => (
            <div key={vp} className="py-2.5 first:pt-0 last:pb-0 flex items-center justify-between">
              <span className="text-sm font-semibold text-white capitalize">{vp}</span>
              <span className="text-xs text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded-full border border-amber-800">
                Low sharpness / glare
              </span>
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <button
            onClick={() => onConfirmRetake(missingViewpoints)}
            className="w-full py-3.5 rounded-full bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs tracking-wider uppercase transition-all shadow-lg flex items-center justify-center space-x-2"
          >
            <Camera className="w-4 h-4" />
            <span>Retake Angle Now</span>
          </button>
          <button
            onClick={onClose}
            className="w-full py-2.5 text-xs text-neutral-400 hover:text-white transition-colors"
          >
            Continue with reduced coverage warnings
          </button>
        </div>
      </div>
    </div>
  );
};
