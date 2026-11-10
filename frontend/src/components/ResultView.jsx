import { useState } from "react";

import { CombinedDownload } from "./CombinedDownload.jsx";
import { EntropyChart } from "./EntropyChart.jsx";
import { VideoPlayer } from "./VideoPlayer.jsx";


// Result View component: the video, the download of the side-by-side video (particles | entropy) and, below, the entropy chart that follows the video's playback
// The playback time lives here and not in DemoSection, so only these two re-render while the video plays
export function ResultView({ taskId }) {
    const [currentTime, setCurrentTime] = useState(0);
    return (
        <div>
            <VideoPlayer taskId={taskId} onTimeUpdate={setCurrentTime} />
            <CombinedDownload taskId={taskId} />
            <EntropyChart taskId={taskId} currentTime={currentTime} />
        </div>
    );
}
