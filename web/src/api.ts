const BASE = '';

export interface UploadResult {
  video_id: string;
  filename: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
}

export interface EditResult {
  output_id: string;
  download_url: string;
}

export async function uploadVideo(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/api/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
}

export async function editVideo(
  videoId: string,
  segments: { start: number; end: number }[]
): Promise<EditResult> {
  const res = await fetch(`${BASE}/api/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_id: videoId, segments }),
  });
  if (!res.ok) throw new Error('Edit failed');
  return res.json();
}

export function streamUrl(videoId: string): string {
  return `${BASE}/api/video/${videoId}/stream`;
}

export function downloadUrl(outputId: string): string {
  return `${BASE}/api/download/${outputId}`;
}
