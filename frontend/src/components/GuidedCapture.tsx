import React, { useRef, useState, useEffect } from 'react';
import { X, AlertTriangle, ShieldCheck, Camera, Video, Sparkles, CheckCircle2 } from 'lucide-react';
import { Challenge } from '../types';

interface GuidedCaptureProps {
  carInfo: { make: string; model: string; year: number };
  challenge?: Challenge;
  trustMode: boolean;
  onFinishCapture: (videoBlob: Blob, videoSha256: string) => void;
  onCancel: () => void;
}

const VIEWPOINT_NAMES = [
  'Front',
  'Front-left',
  'Left',
  'Rear-left',
  'Rear',
  'Rear-right',
  'Right',
  'Front-right',
];

export const GuidedCapture: React.FC<GuidedCaptureProps> = ({
  carInfo,
  challenge,
  trustMode,
  onFinishCapture,
  onCancel,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);

  const [streamActive, setStreamActive] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentViewpointIdx, setCurrentViewpointIdx] = useState(1); // Front-left per design
  const [recordedDuration, setRecordedDuration] = useState(0);
  const [glareWarning, setGlareWarning] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);

  // Car Detection State: 'auto' (live CV check), 'car' (forced detected), 'no_car' (forced none)
  const [detectionMode, setDetectionMode] = useState<'auto' | 'car' | 'no_car'>('auto');
  const [liveCarDetected, setLiveCarDetected] = useState(true);

  // Challenge nonce (e.g. 4 8 2 1 from UI design)
  const challengeCode = challenge?.nonce || '4821';
  const targetAngle = challenge?.angleOrder?.[5] || 'rear-right corner';

  // Effective detection decision
  const isCarDetected =
    detectionMode === 'car'
      ? true
      : detectionMode === 'no_car'
      ? false
      : carInfo.make.toLowerCase().includes('nocar') || carInfo.model.toLowerCase().includes('nocar')
      ? false
      : liveCarDetected;

  // Start Camera
  useEffect(() => {
    let stream: MediaStream | null = null;

    async function initCamera() {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('Camera access not supported on this browser/environment.');
        }
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment',
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
          setStreamActive(true);
        }
      } catch (err: any) {
        setCameraError(err.message || 'Camera permission denied or camera device unavailable.');
      }
    }

    initCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Periodic In-Browser Real-Time Vehicle & Quality Analysis
  useEffect(() => {
    const checkInterval = setInterval(() => {
      if (videoRef.current && canvasRef.current && streamActive && detectionMode === 'auto') {
        try {
          const video = videoRef.current;
          const canvas = canvasRef.current;
          const ctx = canvas.getContext('2d');
          if (ctx && video.videoWidth > 0) {
            canvas.width = 160;
            canvas.height = 90;
            ctx.drawImage(video, 0, 0, 160, 90);
            const imgData = ctx.getImageData(0, 0, 160, 90);
            const data = imgData.data;

            // Simple fast luminance & variance check
            let totalLuma = 0;
            let varianceSum = 0;
            const lumas: number[] = [];
            for (let i = 0; i < data.length; i += 16) {
              const luma = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
              totalLuma += luma;
              lumas.push(luma);
            }
            const meanLuma = totalLuma / lumas.length;
            for (const l of lumas) {
              varianceSum += (l - meanLuma) * (l - meanLuma);
            }
            const variance = varianceSum / lumas.length;

            // If camera is completely covered, black, or flat uniform surface (no car)
            if (meanLuma < 15 || variance < 80) {
              setLiveCarDetected(false);
            } else {
              setLiveCarDetected(true);
            }
          }
        } catch {
          // Keep current state
        }
      }
    }, 800);

    return () => clearInterval(checkInterval);
  }, [streamActive, detectionMode]);

  // Progression timer during recording
  useEffect(() => {
    let interval: any = null;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordedDuration((prev) => {
          const next = prev + 1;
          const nextVp = Math.min(7, Math.floor(next / 3));
          setCurrentViewpointIdx(nextVp);
          setGlareWarning(next % 8 === 3);
          return next;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const startRecording = () => {
    if (!videoRef.current || !videoRef.current.srcObject) {
      setIsRecording(true);
      setRecordedDuration(0);
      return;
    }

    try {
      const stream = videoRef.current.srcObject as MediaStream;
      const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
      mediaRecorderRef.current = recorder;
      recordedChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          recordedChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        let fullBlob: Blob;
        if (!isCarDetected) {
          // Prefix non-car test tag so backend also knows no vehicle was in view
          fullBlob = new Blob(
            ['NO_CAR_WALKAROUND:', ...recordedChunksRef.current],
            { type: 'video/webm' }
          );
        } else {
          fullBlob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
        }

        const hashBuf = await crypto.subtle.digest('SHA-256', await fullBlob.arrayBuffer());
        const hash = Array.from(new Uint8Array(hashBuf))
          .map((b) => b.toString(16).padStart(2, '0'))
          .join('');
        onFinishCapture(fullBlob, hash);
      };

      recorder.start(500);
      setIsRecording(true);
      setRecordedDuration(0);
    } catch {
      setIsRecording(true);
      setRecordedDuration(0);
    }
  };

  const stopRecording = async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    } else {
      setIsRecording(false);
      const tag = isCarDetected
        ? `CarCheck Walkaround Video Simulation - ${carInfo.make} ${carInfo.model}`
        : `NO_CAR_WALKAROUND - Non Vehicle Footage Simulation - ${carInfo.make}`;

      const syntheticBlob = new Blob([tag], { type: 'video/mp4' });
      const hashBuf = await crypto.subtle.digest('SHA-256', await syntheticBlob.arrayBuffer());
      const hash = Array.from(new Uint8Array(hashBuf))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('');
      onFinishCapture(syntheticBlob, hash);
    }
  };

  const handleSimulateNormalCar = async () => {
    const syntheticBlob = new Blob(
      [`Simulated Walkaround 360 - ${carInfo.make} ${carInfo.model} ${Date.now()}`],
      { type: 'video/mp4' }
    );
    const hashBuf = await crypto.subtle.digest('SHA-256', await syntheticBlob.arrayBuffer());
    const hash = Array.from(new Uint8Array(hashBuf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
    onFinishCapture(syntheticBlob, hash);
  };

  const handleSimulateNoCar = async () => {
    const syntheticBlob = new Blob(
      [`NO_CAR_WALKAROUND: Simulated footage with no vehicle present ${Date.now()}`],
      { type: 'video/mp4' }
    );
    const hashBuf = await crypto.subtle.digest('SHA-256', await syntheticBlob.arrayBuffer());
    const hash = Array.from(new Uint8Array(hashBuf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
    onFinishCapture(syntheticBlob, hash);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col justify-between overflow-hidden">
      {/* Hidden canvas for video analysis */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Top Overlay Header */}
      <div className="relative z-20 pt-4 px-4 sm:px-6 flex items-center justify-between">
        <div className="bg-neutral-900/90 border border-neutral-700/80 rounded-full px-4 py-1.5 flex items-center space-x-2 backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></span>
          <span className="text-xs sm:text-sm font-bold text-white">
            Walkaround · {VIEWPOINT_NAMES[currentViewpointIdx]}
          </span>
        </div>

        {/* Real-time Car Detected Badge */}
        <div className="flex items-center space-x-2">
          {isCarDetected ? (
            <div className="bg-emerald-600/90 border border-emerald-400/50 text-white font-bold text-xs px-3.5 py-1.5 rounded-full shadow-lg flex items-center space-x-2 backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-emerald-300 animate-pulse" />
              <span>Car detected</span>
            </div>
          ) : (
            <div className="bg-red-600/95 border border-red-400/60 text-white font-bold text-xs px-3.5 py-1.5 rounded-full shadow-lg flex items-center space-x-2 animate-pulse backdrop-blur-md">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>No car detected</span>
            </div>
          )}

          <button
            onClick={onCancel}
            className="w-9 h-9 rounded-full bg-neutral-900/90 border border-neutral-700/80 text-white flex items-center justify-center hover:bg-neutral-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Glare / Blur Warning Pill */}
      <div className="relative z-20 flex justify-center px-4 mt-2">
        {glareWarning ? (
          <div className="bg-amber-600/95 text-white font-semibold text-xs px-4 py-1.5 rounded-full shadow-lg flex items-center space-x-2 animate-bounce">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Glare: tilt the phone slightly</span>
          </div>
        ) : !isCarDetected ? (
          <div className="bg-red-950/90 border border-red-700 text-red-200 font-semibold text-xs px-4 py-1.5 rounded-full shadow-lg flex items-center space-x-2">
            <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
            <span>Align car inside the dashed outline</span>
          </div>
        ) : (
          <div className="bg-emerald-600/90 text-white font-medium text-xs px-4 py-1 rounded-full shadow">
            Good sharpness & vehicle in frame
          </div>
        )}
      </div>

      {/* Center Viewport: Video Stream & Ghost Outline Overlay */}
      <div className="relative flex-1 flex items-center justify-center overflow-hidden my-2">
        {streamActive ? (
          <video
            ref={videoRef}
            playsInline
            muted
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-center p-6 text-neutral-400">
            <Camera className="w-12 h-12 text-neutral-600 mb-3" />
            <p className="text-sm font-semibold text-white">Live Camera Preview</p>
            <p className="text-xs text-neutral-500 max-w-xs mt-1">
              Virtual walkaround stream active. Point camera at vehicle.
            </p>
          </div>
        )}

        {/* Car Ghost Outline Wireframe */}
        <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center p-6">
          <svg
            className={`w-full max-w-md h-48 sm:h-64 transition-colors ${
              isCarDetected ? 'text-emerald-400/80' : 'text-red-500/90 animate-pulse'
            }`}
            viewBox="0 0 400 160"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeDasharray={isCarDetected ? '6 6' : '4 4'}
          >
            {/* Dotted car body outline */}
            <path d="M 40 100 L 70 50 L 140 25 L 260 25 L 320 50 L 360 80 L 370 115 L 340 115 A 25 25 0 0 1 290 115 L 140 115 A 25 25 0 0 1 90 115 L 30 115 Z" />
            {/* Windows */}
            <path d="M 145 32 L 200 32 L 200 65 L 120 65 Z" strokeDasharray="4 4" strokeWidth="1.5" />
            <path d="M 210 32 L 255 32 L 290 65 L 210 65 Z" strokeDasharray="4 4" strokeWidth="1.5" />
            {/* Wheels */}
            <circle cx="115" cy="115" r="18" strokeDasharray="3 3" />
            <circle cx="315" cy="115" r="18" strokeDasharray="3 3" />
          </svg>

          {!isCarDetected && (
            <div className="mt-2 bg-red-950/90 border border-red-800 text-red-300 text-xs font-mono px-3 py-1 rounded-full shadow-lg">
              ⚠️ No car detected in frame
            </div>
          )}
        </div>
      </div>

      {/* Bottom Controls & Challenge Card */}
      <div className="relative z-20 pb-8 px-4 sm:px-6 space-y-4 bg-gradient-to-t from-black via-black/90 to-transparent pt-4">
        {/* Trust Mode Challenge Card */}
        {trustMode && (
          <div className="bg-neutral-900/90 border border-neutral-800 rounded-2xl p-4 max-w-sm mx-auto backdrop-blur-md text-center shadow-xl">
            <div className="text-[11px] font-mono font-bold tracking-widest text-neutral-400 uppercase">
              Capture challenge
            </div>
            <div className="my-1.5 flex justify-center space-x-3 text-3xl font-black tracking-widest text-white">
              {challengeCode.split('').map((digit, idx) => (
                <span key={idx} className="bg-neutral-800/80 px-2.5 py-0.5 rounded-lg border border-neutral-700">
                  {digit}
                </span>
              ))}
            </div>
            <p className="text-xs text-neutral-400">
              Show this code in frame at the <span className="text-orange-400 font-semibold">{targetAngle}</span>.
            </p>
          </div>
        )}

        {/* 8-Viewpoint Progress Indicator */}
        <div className="max-w-sm mx-auto">
          <div className="flex justify-between items-center text-xs text-neutral-400 font-mono mb-2">
            <span>{currentViewpointIdx + 1} of 8 angles covered</span>
            {isRecording && <span className="text-red-500 font-bold">{recordedDuration}s</span>}
          </div>
          <div className="grid grid-cols-8 gap-1.5">
            {VIEWPOINT_NAMES.map((name, i) => (
              <div
                key={name}
                className={`h-2 rounded-full transition-all ${
                  i < currentViewpointIdx
                    ? 'bg-emerald-500'
                    : i === currentViewpointIdx
                    ? 'bg-orange-500 animate-pulse'
                    : 'bg-neutral-800'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Simulation / Override Toggles for Testing Car Detection */}
        <div className="max-w-sm mx-auto flex items-center justify-center space-x-2">
          <button
            type="button"
            onClick={() => setDetectionMode('auto')}
            className={`px-2.5 py-1 rounded-lg text-[10px] font-mono border transition-all ${
              detectionMode === 'auto'
                ? 'bg-neutral-700 border-neutral-500 text-white font-bold'
                : 'bg-neutral-900 border-neutral-800 text-neutral-400'
            }`}
          >
            Auto-Detect
          </button>
          <button
            type="button"
            onClick={() => setDetectionMode('car')}
            className={`px-2.5 py-1 rounded-lg text-[10px] font-mono border transition-all ${
              detectionMode === 'car'
                ? 'bg-emerald-900 border-emerald-500 text-emerald-200 font-bold'
                : 'bg-neutral-900 border-neutral-800 text-neutral-400'
            }`}
          >
            🚗 Force Car
          </button>
          <button
            type="button"
            onClick={() => setDetectionMode('no_car')}
            className={`px-2.5 py-1 rounded-lg text-[10px] font-mono border transition-all ${
              detectionMode === 'no_car'
                ? 'bg-red-900 border-red-500 text-red-200 font-bold'
                : 'bg-neutral-900 border-neutral-800 text-neutral-400'
            }`}
          >
            🚫 Force No Car
          </button>
        </div>

        {/* Shutter Button & Demo Fallbacks */}
        <div className="flex flex-col items-center justify-center pt-1 space-y-3">
          {!isRecording ? (
            <button
              onClick={startRecording}
              className="w-18 h-18 rounded-full border-4 border-white p-1 flex items-center justify-center hover:scale-105 active:scale-95 transition-all shadow-2xl"
              title="Start Walkaround Recording"
            >
              <div className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-500"></div>
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="w-18 h-18 rounded-full border-4 border-red-500 p-1 flex items-center justify-center hover:scale-105 active:scale-95 transition-all animate-pulse"
              title="Stop and Analyze Walkaround"
            >
              <div className="w-8 h-8 rounded-md bg-red-600"></div>
            </button>
          )}

          {/* Quick Simulation Options */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
            <button
              onClick={handleSimulateNormalCar}
              className="text-xs text-neutral-400 hover:text-white transition-colors underline underline-offset-4 flex items-center space-x-1"
            >
              <Sparkles className="w-3.5 h-3.5 text-orange-400" />
              <span>Simulate Car Walkaround</span>
            </button>
            <span className="text-neutral-600">•</span>
            <button
              onClick={handleSimulateNoCar}
              className="text-xs text-red-400 hover:text-red-300 transition-colors underline underline-offset-4 flex items-center space-x-1 font-semibold"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
              <span>Simulate Non-Car Footage ("No car detected")</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
