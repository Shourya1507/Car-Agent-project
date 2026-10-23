import { Inspection, Challenge, ReportSchema } from './types';

const API_BASE = '';

export async function computeSha256(file: Blob): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export async function createInspection(data: {
  carMake: string;
  carModel: string;
  year: number;
  type: 'STANDARD' | 'BASELINE' | 'COMPARISON';
  baselineId?: string;
  trustMode: boolean;
  videoSha256?: string;
}): Promise<{
  inspectionId: string;
  uploadUrl: string;
  rawVideoKey: string;
  challenge?: Challenge;
}> {
  const res = await fetch(`${API_BASE}/inspections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create inspection' }));
    throw new Error(err.detail || 'Failed to create inspection');
  }
  return res.json();
}

export async function uploadVideo(uploadUrl: string, blob: Blob): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': blob.type || 'video/mp4',
    },
    body: blob,
  });
  if (!res.ok) {
    throw new Error('Failed to upload walkaround video');
  }
}

export async function startInspection(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/inspections/${id}/start`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error('Failed to start processing');
  }
}

export async function getInspection(id: string): Promise<Inspection> {
  const res = await fetch(`${API_BASE}/inspections/${id}`);
  if (!res.ok) {
    throw new Error('Failed to fetch inspection');
  }
  return res.json();
}

export async function listInspections(): Promise<Inspection[]> {
  const res = await fetch(`${API_BASE}/inspections`);
  if (!res.ok) {
    return [];
  }
  const data = await res.json();
  return data.inspections || [];
}

export async function getChallenge(id: string): Promise<Challenge> {
  const res = await fetch(`${API_BASE}/inspections/${id}/challenge`);
  if (!res.ok) {
    throw new Error('Failed to get challenge');
  }
  return res.json();
}

export async function verifyChallenge(id: string): Promise<void> {
  await fetch(`${API_BASE}/inspections/${id}/challenge/verify`, {
    method: 'POST',
  });
}

export async function requestRetake(id: string, viewpoints: string[]): Promise<any> {
  const res = await fetch(`${API_BASE}/inspections/${id}/retake`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ viewpoints }),
  });
  return res.json();
}

export async function createShareLink(id: string): Promise<{ shareUrl: string; token: string }> {
  const res = await fetch(`${API_BASE}/inspections/${id}/share`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expiryHours: 72 }),
  });
  return res.json();
}

export async function verifyReport(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/reports/${id}/verify`);
  if (!res.ok) {
    throw new Error('Report verification failed or report not found');
  }
  return res.json();
}

export async function deleteInspection(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/inspections/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error('Failed to delete inspection');
  }
}
