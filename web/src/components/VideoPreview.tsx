import { useRef, useImperativeHandle, forwardRef } from 'react';

interface Props {
  src: string | null;
}

export interface VideoPreviewRef {
  seek: (time: number) => void;
  play: () => void;
  pause: () => void;
  getCurrentTime: () => number;
}

const VideoPreview = forwardRef<VideoPreviewRef, Props>(({ src }, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  useImperativeHandle(ref, () => ({
    seek(time: number) {
      if (videoRef.current) videoRef.current.currentTime = time;
    },
    play() {
      videoRef.current?.play();
    },
    pause() {
      videoRef.current?.pause();
    },
    getCurrentTime() {
      return videoRef.current?.currentTime ?? 0;
    },
  }));

  if (!src) {
    return <div style={{ width: 640, height: 360, background: '#222', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>请上传视频</div>;
  }

  return (
    <video
      ref={videoRef}
      src={src}
      controls
      style={{ width: 640, maxHeight: 360 }}
    />
  );
});

export default VideoPreview;
