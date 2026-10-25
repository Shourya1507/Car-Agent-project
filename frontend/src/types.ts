export interface Finding {
  id: string;
  type: 'dent' | 'scratch' | 'rust' | 'crack' | 'paint_mismatch' | 'panel_gap_asymmetry' | 'tyre_wear' | 'glass_chip';
  panel: string;
  severity: 'minor' | 'moderate' | 'major';
  confidence: number;
  evidenceKey: string;
  note: string;
  source: 'detector' | 'opencv' | 'reconciled';
  box?: { x1: number; y1: number; x2: number; y2: number };
  changeStatus?: 'NEW' | 'PRE-EXISTING' | 'RESOLVED' | 'UNCERTAIN';
  baselineFindingId?: string;
  baselineEvidenceKey?: string;
  returnEvidenceKey?: string;
}

export interface CoverageItem {
  viewpoint: string;
  captured: boolean;
  frameCount: number;
  bestQualityScore: number;
  reason?: string;
}

export interface ChangeItem {
  findingId: string;
  changeStatus: 'NEW' | 'PRE-EXISTING' | 'RESOLVED' | 'UNCERTAIN';
  panel: string;
  type: string;
  confidence: number;
  baselineEvidenceKey?: string;
  returnEvidenceKey?: string;
  alignmentQuality: number;
  note: string;
}

export interface IntegritySummary {
  challengePassed: boolean;
  challengeAttempts: number;
  matchedFrameTimeSec?: number;
  inAppCapture: boolean;
  videoSha256: string;
  sha256Match: boolean;
  hardCutCount: number;
  cutTimestamps: number[];
  plateConsistent: boolean;
  plateConfidence: number;
  colourConsistencyScore: number;
  appearanceConsistent: boolean;
  trustLevel: 'VERIFIED' | 'PARTIAL' | 'UNVERIFIED';
  reasons: string[];
}

export interface ReportSchema {
  inspectionId: string;
  carMake: string;
  carModel: string;
  year: number;
  inspectionDate: string;
  carDetected?: boolean;
  score: number;
  scoreSummary: string;
  coverage: CoverageItem[];
  findings: Finding[];
  sellerQuestions: string[];
  limitations: string[];
  trust: IntegritySummary;
  changes?: ChangeItem[];
  reportSignature?: string;
  reportHash?: string;
  pdfKey?: string;
}

export interface Inspection {
  inspectionId: string;
  userId: string;
  carMake: string;
  carModel: string;
  year: number;
  type: 'STANDARD' | 'BASELINE' | 'COMPARISON';
  baselineId?: string;
  trustMode: boolean;
  carDetected?: boolean;
  status: 'CREATED' | 'UPLOADED' | 'PROCESSING' | 'NEEDS_RETAKE' | 'DONE' | 'FAILED';
  score?: number;
  trustLevel?: 'VERIFIED' | 'PARTIAL' | 'UNVERIFIED';
  videoSha256?: string;
  reportSignature?: string;
  reportHash?: string;
  retakeRound: number;
  missingViewpoints: string[];
  createdAt: string;
  report?: ReportSchema;
  failureReason?: string;
}

export interface Challenge {
  nonce: string;
  angleOrder: string[];
  expiresAt: number;
  verified: boolean;
}
