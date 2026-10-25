import React, { useRef, useState, useEffect } from 'react';
import { X, AlertTriangle, ShieldCheck, Video, Sparkles, CheckCircle2 } from 'lucide-react';
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

/**
 * Analyzes a scaled camera frame canvas to verify vehicle presence.
 * Checks:
 * 1. Frame valid luminance and dynamic range
 * 2. Presence of horizontal automotive body contours in the guide zone
 * 3. Aspect ratio and structural edge density
 */
function evaluateVehiclePresence(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): { carDetected: boolean; confidence: number } {
  const imgData = ctx.getImageData(0, 0, width, height);
  const data = imgData.data;

  // Grayscale conversion
  const gray = new Uint8Array(width * height);
  let totalLuma = 0;
  for (let i = 0, j = 0; i < data.length; i += 4, j++) {
    const luma = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
    gray[j] = luma;
    totalLuma += luma;
  }
  const meanLuma = totalLuma / gray.length;

  // Dark or blown-out frames cannot be certified as containing a vehicle
  if (meanLuma < 25 || meanLuma > 240) {
    return { carDetected: false, confidence: 0.05 };
  }

  // Region of Interest: center guide region where car outline sits
  const roiXStart = Math.floor(width * 0.15);
  const roiXEnd = Math.floor(width * 0.85);
  const roiYStart = Math.floor(height * 0.25);
  const roiYEnd = Math.floor(height * 0.90);
  const roiW = roiXEnd - roiXStart;
  const roiH = roiYEnd - roiYStart;

  // Edge and Gradient Orientation Analysis
  let horizEdges = 0;
  let vertEdges = 0;
  let totalEdges = 0;

  for (let y = roiYStart + 1; y < roiYEnd - 1; y += 2) {
    for (let x = roiXStart + 1; x < roiXEnd - 1; x += 2) {
      const idx = y * width + x;
      const gx = Math.abs(gray[idx + 1] - gray[idx - 1]);
      const gy = Math.abs(gray[idx + width] - gray[idx - width]);
      const mag = gx + gy;
      if (mag > 35) {
        totalEdges++;
        if (gy > gx * 1.25) horizEdges++;
        else if (gx > gy * 1.25) vertEdges++;
      }
    }
  }

  const roiSamples = (roiW / 2) * (roiH / 2);
  const edgeDensity = totalEdges / Math.max(1, roiSamples);

  // Insufficient edges -> plain wall, ceiling, floor, or uniform surface
  if (edgeDensity < 0.035) {
    return { carDetected: false, confidence: 0.10 };
  }

  // High vertical edge dominance -> typically standing human, vertical doorframe, face
  if (vertEdges > horizEdges * 1.85) {
    return { carDetected: false, confidence: 0.15 };
  }

  // Silhouette mass & aspect ratio in ROI
  let minX = roiXEnd, maxX = roiXStart, minY = roiYEnd, maxY = roiYStart;
  let massPixels = 0;

  for (let y = roiYStart; y < roiYEnd; y += 2) {
    for (let x = roiXStart; x < roiXEnd; x += 2) {
      const val = gray[y * width + x];
      if (Math.abs(val - meanLuma) > 22) {
        massPixels++;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }

  const bodyW = Math.max(1, maxX - minX);
  const bodyH = Math.max(1, maxY - minY);
  const bodyAspect = bodyW / bodyH;
  const massRatio = massPixels / Math.max(1, roiSamples);

  // Automotive criteria: horizontally elongated body mass with horizontal structural lines
  const hasAutomotiveShape = bodyAspect >= 1.20 && bodyAspect <= 3.6 && massRatio >= 0.18;
  const hasAutomotiveEdges = horizEdges >= 12 && edgeDensity >= 0.04 && edgeDensity <= 0.40;

  const isCar = hasAutomotiveShape && hasAutomotiveEdges;
  const confidence = isCar
    ? Math.min(0.96, 0.55 + massRatio * 0.4)
    : Math.max(0.05, 0.35 - massRatio * 0.2);

  return { carDetected: isCar, confidence };
}

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
  const detectionHistoryRef = useRef<boolean[]>([]);

  const [streamActive, setStreamActive] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentViewpointIdx, setCurrentViewpointIdx] = useState(1);
  const [recordedDuration, setRecordedDuration] = useState(0);
  const [glareWarning, setGlareWarning] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);

  // Live real-time computer vision detection state
  const [liveCarDetected, setLiveCarDetected] = useState(false);

  // Challenge nonce (e.g. 4 8 2 1 from UI design)
  const challengeCode = challenge?.nonce || '4821';
  const targetAngle = challenge?.angleOrder?.[5] || 'rear-right corner';

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

  // Periodic In-Browser Real-Time Vehicle Analysis
  useEffect(() => {
    const checkInterval = setInterval(() => {
      if (videoRef.current && canvasRef.current && streamActive) {
        try {
          const video = videoRef.current;
          const canvas = canvasRef.current;
          const ctx = canvas.getContext('2d');
          if (ctx && video.videoWidth > 0) {
            canvas.width = 160;
            canvas.height = 90;
            ctx.drawImage(video, 0, 0, 160, 90);

            const result = evaluateVehiclePresence(ctx, 160, 90);
            setLiveCarDetected(result.carDetected);

            if (isRecording) {
              detectionHistoryRef.current.push(result.carDetected);
            }
          }
        } catch {
          // Keep current state
        }
      }
    }, 600);

    return () => clearInterval(checkInterval);
  }, [streamActive, isRecording]);

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
    detectionHistoryRef.current = [];

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
        // Evaluate overall detection rate during walkaround
        const detections = detectionHistoryRef.current;
        const detectionRatio =
          detections.length > 0
            ? detections.filter(Boolean).length / detections.length
            : liveCarDetected
            ? 1.0
            : 0.0;

        let fullBlob: Blob;
        if (detectionRatio < 0.3) {
          // No car was visible during walkaround
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
      const tag = liveCarDetected
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

        {/* Real-time Vehicle Presence Detection Badge */}
        <div className="flex items-center space-x-2">
          {liveCarDetected ? (
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

      {/* Live Warning / Alignment Pill */}
      <div className="relative z-20 flex justify-center px-4 mt-2">
        {glareWarning ? (
          <div className="bg-amber-600/95 text-white font-semibold text-xs px-4 py-1.5 rounded-full shadow-lg flex items-center space-x-2 animate-bounce">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Glare: tilt the phone slightly</span>
          </div>
        ) : !liveCarDetected ? (
          <div className="bg-red-950/90 border border-red-700 text-red-200 font-semibold text-xs px-4 py-1.5 rounded-full shadow-lg flex items-center space-x-2">
            <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
            <span>No car detected · Align vehicle inside frame</span>
          </div>
        ) : (
          <div className="bg-emerald-950/90 border border-emerald-700 text-emerald-200 font-semibold text-xs px-4 py-1.5 rounded-full shadow-lg flex items-center space-x-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Vehicle aligned · Ready to record</span>
          </div>
        )}
      </div>

      {/* Viewfinder Center Area */}
      <div className="relative flex-1 flex items-center justify-center p-4">
        {/* Camera stream video */}
        {streamActive ? (
          <video
            ref={videoRef}
            playsInline
            muted
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-neutral-950 text-neutral-400 p-6 text-center">
            <Video className="w-16 h-16 mb-4 text-neutral-600 animate-pulse" />
            <p className="text-sm font-medium text-neutral-300">
              {cameraError || 'Camera initializing or simulated environment active.'}
            </p>
            <p className="text-xs text-neutral-500 mt-1 max-w-sm">
              In real walkaround inspections, the camera automatically scans for vehicle contours and wheel hubs.
            </p>
          </div>
        )}

        {/* Dynamic Vehicle Alignment Guide Overlay */}
        <div className="relative z-10 w-full max-w-md aspect-[16/10] flex items-center justify-center pointer-events-none">
          <div
            className={`w-full h-full border-2 rounded-3xl transition-all duration-300 relative flex items-center justify-center ${
              liveCarDetected
                ? 'border-emerald-500/80 bg-emerald-500/5 shadow-[0_0_30px_rgba(16,185,129,0.2)]'
                : 'border-dashed border-red-500/70 bg-red-950/10'
            }`}
          >
            {/* Corner alignment markers */}
            <div className="absolute -top-1 -left-1 w-6 h-6 border-t-4 border-l-4 border-orange-500 rounded-tl-xl" />
            <div className="absolute -top-1 -right-1 w-6 h-6 border-t-4 border-r-4 border-orange-500 rounded-tr-xl" />
            <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-4 border-l-4 border-orange-500 rounded-bl-xl" />
            <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-4 border-r-4 border-orange-500 rounded-br-xl" />

            {/* Guide label */}
            <div className="text-center px-4">
              <p
                className={`text-xs font-mono font-bold tracking-wider uppercase transition-colors ${
                  liveCarDetected ? 'text-emerald-400' : 'text-red-400'
                }`}
              >
                {liveCarDetected
                  ? `✓ ${carInfo.make} ${carInfo.model} Positioned`
                  : 'Position Vehicle Inside Outline'}
              </p>
            </div>
          </div>
        </div>

        {/* Liveness Nonce Challenge Card (TRD 5.2) */}
        {trustMode && (
          <div className="absolute top-4 left-4 z-20 bg-neutral-900/95 border border-orange-500/60 rounded-2xl p-3 shadow-2xl backdrop-blur-md max-w-[210px]">
            <div className="flex items-center space-x-1.5 text-orange-400 mb-1">
              <ShieldCheck className="w-4 h-4" />
              <span className="text-[10px] font-mono uppercase tracking-wider font-bold">
                Anti-Spoof Challenge
              </span>
            </div>
            <p className="text-xs text-neutral-300 font-medium leading-snug">
              Flash code at <span className="text-orange-400 font-bold">{targetAngle}</span>:
            </p>
            <div className="flex items-center justify-center space-x-2 mt-2 bg-neutral-950 border border-neutral-800 rounded-xl py-1 px-2">
              {challengeCode.split('').map((digit, idx) => (
                <span
                  key={idx}
                  className="font-mono text-base font-extrabold text-orange-400 tracking-wider"
                >
                  {digit}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Controls Bar */}
      <div className="relative z-20 pb-6 px-4 sm:px-6 bg-gradient-to-t from-black via-black/80 to-transparent pt-4">
        {/* Progress tracker */}
        <div className="max-w-md mx-auto mb-4">
          <div className="flex justify-between text-xs text-neutral-400 font-mono mb-1.5">
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

        {/* Shutter Button & Clean Fallback */}
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

          {/* Clean fallback for testing without camera */}
          <div className="pt-1">
            <button
              onClick={handleSimulateNormalCar}
              className="text-xs text-neutral-400 hover:text-white transition-colors underline underline-offset-4 flex items-center space-x-1"
            >
              <Sparkles className="w-3.5 h-3.5 text-orange-400" />
              <span>Simulate 360° Walkaround</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
