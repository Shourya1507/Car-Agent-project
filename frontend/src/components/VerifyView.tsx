import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, Search, Key, Hash, FileCheck } from 'lucide-react';
import { verifyReport } from '../api';

interface VerifyViewProps {
  initialInspectionId?: string;
}

export const VerifyView: React.FC<VerifyViewProps> = ({ initialInspectionId = '' }) => {
  const [inspectionId, setInspectionId] = useState(initialInspectionId);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (idToVerify: string) => {
    if (!idToVerify.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await verifyReport(idToVerify.trim());
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Report not found or verification check failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialInspectionId) {
      handleVerify(initialInspectionId);
    }
  }, [initialInspectionId]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
      {/* Title */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto mb-4">
          <ShieldCheck className="w-7 h-7" />
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-white uppercase tracking-tight">
          Public Report Verification
        </h1>
        <p className="text-sm text-neutral-400 mt-2">
          Verify cryptographic authenticity, ECDSA P-256 signature, SHA-256 hash, and Trust Layer status for any CarCheck inspection report.
        </p>
      </div>

      {/* Search Bar */}
      <div className="max-w-xl mx-auto flex items-center space-x-2">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-4 top-3.5 text-neutral-500" />
          <input
            type="text"
            placeholder="Enter Inspection ID (e.g. insp_a1b2c3d4)"
            value={inspectionId}
            onChange={(e) => setInspectionId(e.target.value)}
            className="w-full bg-neutral-900 border border-neutral-700 rounded-full pl-11 pr-4 py-3 text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-orange-500"
          />
        </div>
        <button
          onClick={() => handleVerify(inspectionId)}
          disabled={loading || !inspectionId.trim()}
          className="px-6 py-3 rounded-full bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs uppercase tracking-wider transition-all disabled:opacity-50"
        >
          {loading ? 'Verifying...' : 'Verify'}
        </button>
      </div>

      {error && (
        <div className="max-w-xl mx-auto p-4 bg-red-950/40 border border-red-800 rounded-2xl flex items-center space-x-3 text-red-300 text-xs">
          <XCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl">
          {/* Status Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-neutral-800 gap-4">
            <div>
              <div className="text-xs font-mono text-neutral-400 uppercase">Verification Result</div>
              <h2 className="text-2xl font-bold text-white mt-1">
                {result.year} {result.carMake} {result.carModel}
              </h2>
              <div className="text-xs text-neutral-500 mt-0.5">
                Inspection Date: {result.inspectionDate}
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {result.signatureValid && result.hashMatches ? (
                <div className="px-4 py-2 rounded-full bg-emerald-950/80 border border-emerald-700 text-emerald-400 text-xs font-bold uppercase tracking-wider flex items-center space-x-2 shadow-lg shadow-emerald-900/30">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Report Genuine & Verified</span>
                </div>
              ) : (
                <div className="px-4 py-2 rounded-full bg-red-950/80 border border-red-700 text-red-400 text-xs font-bold uppercase tracking-wider flex items-center space-x-2">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Tamper Detected / Invalid</span>
                </div>
              )}
            </div>
          </div>

          {/* Verification Checks Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 bg-neutral-800/40 border border-neutral-700/60 rounded-2xl flex items-start space-x-3">
              <Hash className="w-5 h-5 text-orange-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold text-white uppercase">SHA-256 Digest Integrity</div>
                <div className="text-xs text-emerald-400 font-semibold mt-0.5">
                  {result.hashMatches ? '✓ Canonical JSON hash matches stored report' : '✗ Hash mismatch'}
                </div>
                <div className="text-[10px] font-mono text-neutral-400 break-all mt-1">
                  {result.computedHash}
                </div>
              </div>
            </div>

            <div className="p-4 bg-neutral-800/40 border border-neutral-700/60 rounded-2xl flex items-start space-x-3">
              <Key className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold text-white uppercase">ECDSA P-256 Signature</div>
                <div className="text-xs text-emerald-400 font-semibold mt-0.5">
                  {result.signatureValid ? '✓ Valid digital signature (SECP256R1)' : '✗ Invalid signature'}
                </div>
                <div className="text-[10px] font-mono text-neutral-400 mt-1">
                  Asymmetric keypair verification passed.
                </div>
              </div>
            </div>

            <div className="p-4 bg-neutral-800/40 border border-neutral-700/60 rounded-2xl flex items-start space-x-3">
              <FileCheck className="w-5 h-5 text-sky-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold text-white uppercase">Trust Layer Grade</div>
                <div className={`text-xs font-bold uppercase mt-0.5 ${
                  result.trustLevel === 'VERIFIED' ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  {result.trustLevel}
                </div>
                <div className="text-[10px] text-neutral-400 mt-1">
                  Single-use nonce verified, video continuous, plate consistent.
                </div>
              </div>
            </div>

            <div className="p-4 bg-neutral-800/40 border border-neutral-700/60 rounded-2xl flex items-start space-x-3">
              <ShieldCheck className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-bold text-white uppercase">Video Origin SHA-256</div>
                <div className="text-xs text-neutral-300 font-semibold mt-0.5">
                  Verified client WebCrypto hash
                </div>
                <div className="text-[10px] font-mono text-neutral-400 break-all mt-1">
                  {result.videoSha256 || 'Verified at upload'}
                </div>
              </div>
            </div>
          </div>

          {/* Mandatory Screening Disclaimer */}
          <div className="p-4 bg-neutral-950/80 border border-neutral-800 rounded-2xl text-center">
            <p className="text-xs text-neutral-400">
              <span className="text-orange-400 font-bold uppercase">Screening Disclaimer: </span>
              {result.screeningDisclaimer}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
