import { useState, useRef } from 'react';
import VideoPreview, { VideoPreviewRef } from './components/VideoPreview';
import TimelineEditor from './components/TimelineEditor';
import { uploadVideo, editVideo, streamUrl, downloadUrl, UploadResult } from './api';

export default function App() {
  const [videoInfo, setVideoInfo] = useState<UploadResult | null>(null);
  const [segments, setSegments] = useState<{ start: number; end: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const videoRef = useRef<VideoPreviewRef>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setResultUrl(null);
    try {
      const info = await uploadVideo(file);
      setVideoInfo(info);
      setSegments([{ start: 0, end: info.duration }]);
    } catch (err) {
      alert('上传失败: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!videoInfo || segments.length === 0) return;
    setLoading(true);
    try {
      const result = await editVideo(videoInfo.video_id, segments);
      setResultUrl(downloadUrl(result.output_id));
    } catch (err) {
      alert('导出失败: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleCursorChange = (time: number) => {
    videoRef.current?.seek(time);
  };

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif', maxWidth: 900, margin: '0 auto' }}>
      <h1>LiveCap 视频剪辑</h1>

      <div style={{ marginBottom: 16 }}>
        <input type="file" accept="video/*" onChange={handleUpload} disabled={loading} />
        {loading && <span style={{ marginLeft: 8 }}>处理中...</span>}
      </div>

      <VideoPreview
        ref={videoRef}
        src={videoInfo ? streamUrl(videoInfo.video_id) : null}
      />

      {videoInfo && (
        <div style={{ marginTop: 16 }}>
          <TimelineEditor
            duration={videoInfo.duration}
            onSegmentsChange={setSegments}
            onCursorChange={handleCursorChange}
          />
          <button
            onClick={handleExport}
            disabled={loading || segments.length === 0}
            style={{ marginTop: 12, padding: '8px 24px', fontSize: 14 }}
          >
            导出剪辑
          </button>
        </div>
      )}

      {resultUrl && (
        <div style={{ marginTop: 16 }}>
          <a href={resultUrl} download>⬇️ 下载剪辑结果</a>
        </div>
      )}
    </div>
  );
}
