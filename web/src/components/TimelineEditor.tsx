import { useEffect, useState } from 'react';
import { Timeline, TimelineEffect, TimelineRow } from '@xzdarcy/react-timeline-editor';

interface Props {
  duration: number;
  onSegmentsChange: (segments: { start: number; end: number }[]) => void;
  onCursorChange?: (time: number) => void;
}

const mockEffect: Record<string, TimelineEffect> = {
  clip: {
    id: 'clip',
    name: 'Clip',
  },
};

export default function TimelineEditor({ duration, onSegmentsChange, onCursorChange }: Props) {
  const [data, setData] = useState<TimelineRow[]>([
    {
      id: 'track-0',
      actions: [
        {
          id: 'action-0',
          start: 0,
          end: duration || 10,
          effectId: 'clip',
        },
      ],
    },
  ]);

  // Update default action end when duration changes
  useEffect(() => {
    if (duration > 0) {
      setData([
        {
          id: 'track-0',
          actions: [
            {
              id: 'action-0',
              start: 0,
              end: duration,
              effectId: 'clip',
            },
          ],
        },
      ]);
    }
  }, [duration]);

  const handleChange = (newData: TimelineRow[]) => {
    setData(newData);
    const segments = newData.flatMap((row) =>
      row.actions.map((a) => ({ start: a.start, end: a.end }))
    );
    onSegmentsChange(segments);
  };

  return (
    <div style={{ width: '100%' }}>
      <Timeline
        editorData={data}
        effects={mockEffect}
        onChange={handleChange}
        onCursorDrag={(time) => onCursorChange?.(time)}
        style={{ width: '100%', height: 120 }}
        scale={duration > 60 ? 10 : 1}
        scaleWidth={80}
      />
      <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
        拖拽片段边缘调整起止点 | 右键添加新片段
      </p>
    </div>
  );
}
