import React, { useState } from 'react';
import { X, Shield, ArrowRight, Layers, Car } from 'lucide-react';
import { Inspection } from '../types';

interface InspectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    carMake: string;
    carModel: string;
    year: number;
    type: 'STANDARD' | 'BASELINE' | 'COMPARISON';
    baselineId?: string;
    trustMode: boolean;
  }) => void;
  existingInspections: Inspection[];
  defaultType?: 'STANDARD' | 'BASELINE' | 'COMPARISON';
}

export const InspectionModal: React.FC<InspectionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  existingInspections,
  defaultType = 'STANDARD',
}) => {
  const [carMake, setCarMake] = useState('Toyota');
  const [carModel, setCarModel] = useState('CH-R');
  const [year, setYear] = useState(2026);
  const [type, setType] = useState<'STANDARD' | 'BASELINE' | 'COMPARISON'>(defaultType);
  const [baselineId, setBaselineId] = useState<string>(
    existingInspections.find(i => i.type === 'BASELINE')?.inspectionId || existingInspections[0]?.inspectionId || ''
  );
  const [trustMode, setTrustMode] = useState(true);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      carMake,
      carModel,
      year: Number(year),
      type,
      baselineId: type === 'COMPARISON' ? baselineId : undefined,
      trustMode,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="bg-neutral-900 border border-neutral-800 rounded-3xl max-w-lg w-full p-6 sm:p-8 relative shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-6 right-6 text-neutral-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-orange-600/20 border border-orange-500/30 flex items-center justify-center text-orange-500">
            <Car className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Create Vehicle Inspection</h2>
            <p className="text-xs text-neutral-400">Step 1 of 2: Vehicle details & mode selection</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Inspection Mode Selection */}
          <div>
            <label className="block text-xs font-mono uppercase text-neutral-400 mb-2">
              Inspection Mode
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(['STANDARD', 'BASELINE', 'COMPARISON'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setType(m)}
                  className={`py-2 px-3 rounded-xl text-xs font-bold transition-all border ${
                    type === m
                      ? 'bg-orange-600 border-orange-500 text-white shadow-lg shadow-orange-600/20'
                      : 'bg-neutral-800/80 border-neutral-700/80 text-neutral-300 hover:bg-neutral-700'
                  }`}
                >
                  {m === 'STANDARD' ? 'Standard' : m === 'BASELINE' ? 'Baseline' : 'Handover'}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-neutral-500 mt-1.5">
              {type === 'STANDARD' && 'Comprehensive screening condition report for used-car buyers.'}
              {type === 'BASELINE' && 'Saves pickup reference inspection for future comparison.'}
              {type === 'COMPARISON' && 'Handover comparison: reports only NEW, PRE-EXISTING, or RESOLVED damage.'}
            </p>
          </div>

          {/* Baseline Picker if COMPARISON */}
          {type === 'COMPARISON' && (
            <div>
              <label className="block text-xs font-mono uppercase text-neutral-400 mb-1.5">
                Select Baseline Inspection
              </label>
              {existingInspections.length > 0 ? (
                <select
                  value={baselineId}
                  onChange={(e) => setBaselineId(e.target.value)}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                  required
                >
                  {existingInspections.map((i) => (
                    <option key={i.inspectionId} value={i.inspectionId}>
                      {i.carMake} {i.carModel} ({i.year}) - {i.inspectionId.substring(0, 10)} - {i.type}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-xs text-amber-400 bg-amber-950/40 border border-amber-800 p-3 rounded-xl">
                  No previous baseline inspection found. A mock baseline will be generated automatically for this demo!
                </div>
              )}
            </div>
          )}

          {/* Quick Presets & Testing Scenarios */}
          <div>
            <label className="block text-[11px] font-mono uppercase text-neutral-400 mb-1.5">
              Quick Presets / Testing Scenarios
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => {
                  setCarMake('Toyota');
                  setCarModel('CH-R');
                  setYear(2026);
                }}
                className="px-2.5 py-1 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium border border-neutral-700"
              >
                🚗 Toyota CH-R
              </button>
              <button
                type="button"
                onClick={() => {
                  setCarMake('Honda');
                  setCarModel('Civic');
                  setYear(2025);
                }}
                className="px-2.5 py-1 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium border border-neutral-700"
              >
                🚗 Honda Civic
              </button>
              <button
                type="button"
                onClick={() => {
                  setCarMake('Hyundai');
                  setCarModel('Ioniq 5');
                  setYear(2024);
                }}
                className="px-2.5 py-1 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium border border-neutral-700"
              >
                🚗 Hyundai Ioniq 5
              </button>
            </div>
          </div>

          {/* Car Make, Model, Year */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-mono uppercase text-neutral-400 mb-1.5">
                Make
              </label>
              <input
                type="text"
                value={carMake}
                onChange={(e) => setCarMake(e.target.value)}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-mono uppercase text-neutral-400 mb-1.5">
                Model
              </label>
              <input
                type="text"
                value={carModel}
                onChange={(e) => setCarModel(e.target.value)}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-neutral-400 mb-1.5">
              Year
            </label>
            <input
              type="number"
              min={1990}
              max={2030}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
              required
            />
          </div>

          {/* Trust Mode Toggle */}
          <div className="flex items-center justify-between p-3.5 bg-neutral-800/60 border border-neutral-700/80 rounded-2xl">
            <div className="flex items-center space-x-3">
              <Shield className={`w-5 h-5 ${trustMode ? 'text-emerald-400' : 'text-neutral-500'}`} />
              <div>
                <div className="text-xs font-bold text-white">Trust Layer Mode</div>
                <div className="text-[11px] text-neutral-400">
                  Enforces challenge code, in-app stream & hash verification
                </div>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={trustMode}
                onChange={(e) => setTrustMode(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-neutral-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
            </label>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              className="w-full py-3.5 rounded-full bg-orange-600 hover:bg-orange-500 text-white font-bold text-sm tracking-wider uppercase transition-all shadow-lg shadow-orange-600/30 flex items-center justify-center space-x-2"
            >
              <span>Continue to Guided Capture</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
