import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { InspectionModal } from './components/InspectionModal';
import { GuidedCapture } from './components/GuidedCapture';
import { ProcessingView } from './components/ProcessingView';
import { RetakeModal } from './components/RetakeModal';
import { ReportView } from './components/ReportView';
import { HandoverView } from './components/HandoverView';
import { VerifyView } from './components/VerifyView';
import {
  listInspections,
  createInspection,
  uploadVideo,
  startInspection,
  getInspection,
  requestRetake,
  createShareLink,
  deleteInspection,
} from './api';
import { Inspection, Challenge } from './types';

export function App() {
  const [currentTab, setCurrentTab] = useState<'home' | 'inspect' | 'handover' | 'verify'>('home');
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [activeInspection, setActiveInspection] = useState<Inspection | null>(null);

  // Modals & Flow States
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createModalDefaultType, setCreateModalDefaultType] = useState<'STANDARD' | 'BASELINE' | 'COMPARISON'>('STANDARD');

  const [isCapturing, setIsCapturing] = useState(false);
  const [currentChallenge, setCurrentChallenge] = useState<Challenge | undefined>(undefined);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentProcessingId, setCurrentProcessingId] = useState<string>('');

  const [retakeModalOpen, setRetakeModalOpen] = useState(false);
  const [missingViewpoints, setMissingViewpoints] = useState<string[]>([]);
  const [retakeRound, setRetakeRound] = useState(0);

  const [verifyTargetId, setVerifyTargetId] = useState<string>('');
  const [currentCarInfo, setCurrentCarInfo] = useState<{ make: string; model: string; year: number }>({
    make: 'Toyota',
    model: 'CH-R',
    year: 2026,
  });

  // Initial load
  const refreshInspections = async () => {
    try {
      const list = await listInspections();
      setInspections(list);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    refreshInspections();
  }, []);

  // Handle Create Inspection Submit
  const handleCreateSubmit = async (data: {
    carMake: string;
    carModel: string;
    year: number;
    type: 'STANDARD' | 'BASELINE' | 'COMPARISON';
    baselineId?: string;
    trustMode: boolean;
  }) => {
    setIsCreateModalOpen(false);
    setCurrentCarInfo({
      make: data.carMake,
      model: data.carModel,
      year: data.year,
    });
    try {
      const res = await createInspection(data);
      setCurrentProcessingId(res.inspectionId);
      setCurrentChallenge(res.challenge);
      setIsCapturing(true);
    } catch (err: any) {
      alert(`Error creating inspection: ${err.message}`);
    }
  };

  // Handle Finish Capture
  const handleFinishCapture = async (videoBlob: Blob, videoSha256: string) => {
    setIsCapturing(false);
    setIsProcessing(true);

    try {
      // 1. Upload video directly to local S3 simulation endpoint
      const uploadUrl = `/upload/raw/usr_demo_buyer/${currentProcessingId}/walkaround.mp4`;
      await uploadVideo(uploadUrl, videoBlob);

      // 2. Start asynchronous Step Functions workflow
      await startInspection(currentProcessingId);

      // 3. Polling check
      const checkStatus = async () => {
        try {
          const insp = await getInspection(currentProcessingId);
          if (insp.status === 'DONE') {
            setIsProcessing(false);
            setActiveInspection(insp);
            setCurrentTab('inspect');
            refreshInspections();
          } else if (insp.status === 'NEEDS_RETAKE') {
            setIsProcessing(false);
            setMissingViewpoints(insp.missingViewpoints || ['rear-left']);
            setRetakeRound(insp.retakeRound || 0);
            setRetakeModalOpen(true);
          } else if (insp.status === 'FAILED') {
            setIsProcessing(false);
            alert(`Inspection failed: ${insp.failureReason || 'Processing error'}`);
          } else {
            setTimeout(checkStatus, 1500);
          }
        } catch (e) {
          setTimeout(checkStatus, 2000);
        }
      };

      setTimeout(checkStatus, 3000);
    } catch (err: any) {
      setIsProcessing(false);
      alert(`Upload failed: ${err.message}`);
    }
  };

  // Retake confirmation
  const handleConfirmRetake = async (vps: string[]) => {
    setRetakeModalOpen(false);
    setIsProcessing(true);
    try {
      await requestRetake(currentProcessingId, vps);
      // Resume polling
      const checkStatus = async () => {
        const insp = await getInspection(currentProcessingId);
        if (insp.status === 'DONE') {
          setIsProcessing(false);
          setActiveInspection(insp);
          setCurrentTab('inspect');
          refreshInspections();
        } else {
          setTimeout(checkStatus, 1500);
        }
      };
      setTimeout(checkStatus, 2000);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Share Link Handler
  const handleShare = async () => {
    if (!activeInspection) return;
    try {
      const share = await createShareLink(activeInspection.inspectionId);
      const url = `${window.location.origin}${share.shareUrl}`;
      navigator.clipboard.writeText(url);
      alert(`Read-only share link copied to clipboard:\n${url}`);
    } catch (e: any) {
      alert(e.message);
    }
  };

  // Delete Inspection Handler
  const handleDelete = async () => {
    if (!activeInspection) return;
    if (confirm(`Are you sure you want to delete inspection ${activeInspection.inspectionId}? This removes all media and evidence.`)) {
      try {
        await deleteInspection(activeInspection.inspectionId);
        setActiveInspection(null);
        setCurrentTab('home');
        refreshInspections();
      } catch (e: any) {
        alert(e.message);
      }
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col font-sans">
      <Navbar
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setCurrentTab(tab);
          if (tab === 'verify' && activeInspection) {
            setVerifyTargetId(activeInspection.inspectionId);
          }
        }}
        onOpenCreateModal={() => {
          setCreateModalDefaultType('STANDARD');
          setIsCreateModalOpen(true);
        }}
      />

      <main className="flex-1">
        {/* Processing State */}
        {isProcessing ? (
          <ProcessingView
            inspectionId={currentProcessingId}
            isComparison={activeInspection?.type === 'COMPARISON'}
            onComplete={() => {}}
          />
        ) : currentTab === 'home' ? (
          <Hero
            onStartInspection={() => {
              setCreateModalDefaultType('STANDARD');
              setIsCreateModalOpen(true);
            }}
            onTryHandover={() => {
              setCreateModalDefaultType('COMPARISON');
              setIsCreateModalOpen(true);
            }}
            inspections={inspections}
            onSelectInspection={(insp) => {
              setActiveInspection(insp);
              setCurrentTab('inspect');
            }}
          />
        ) : currentTab === 'inspect' ? (
          activeInspection ? (
            <ReportView
              inspection={activeInspection}
              onVerify={() => {
                setVerifyTargetId(activeInspection.inspectionId);
                setCurrentTab('verify');
              }}
              onShare={handleShare}
              onDelete={handleDelete}
              onRetake={() => {
                setCreateModalDefaultType(activeInspection.type || 'STANDARD');
                setIsCreateModalOpen(true);
              }}
            />
          ) : (
            <div className="max-w-md mx-auto py-24 text-center">
              <p className="text-neutral-400 mb-4">No inspection selected.</p>
              <button
                onClick={() => {
                  setCreateModalDefaultType('STANDARD');
                  setIsCreateModalOpen(true);
                }}
                className="px-6 py-3 rounded-full bg-orange-600 hover:bg-orange-500 font-bold text-xs uppercase tracking-wider"
              >
                Create New Inspection
              </button>
            </div>
          )
        ) : currentTab === 'handover' ? (
          <HandoverView
            inspections={inspections}
            onStartComparison={() => {
              setCreateModalDefaultType('COMPARISON');
              setIsCreateModalOpen(true);
            }}
          />
        ) : (
          <VerifyView initialInspectionId={verifyTargetId} />
        )}
      </main>

      {/* Guided Capture Fullscreen Overlay */}
      {isCapturing && (
        <GuidedCapture
          carInfo={currentCarInfo}
          challenge={currentChallenge}
          trustMode={true}
          onFinishCapture={handleFinishCapture}
          onCancel={() => setIsCapturing(false)}
        />
      )}

      {/* Inspection Creation Modal */}
      <InspectionModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateSubmit}
        existingInspections={inspections}
        defaultType={createModalDefaultType}
      />

      {/* Retake Loop Modal */}
      <RetakeModal
        isOpen={retakeModalOpen}
        onClose={() => setRetakeModalOpen(false)}
        missingViewpoints={missingViewpoints}
        retakeRound={retakeRound}
        onConfirmRetake={handleConfirmRetake}
      />
    </div>
  );
}
