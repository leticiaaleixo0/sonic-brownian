import { useState } from "react";

import { AudioUpload, ProcessingStatus, VideoPlayer, ErrorMessage } from "./components.jsx";

function App() {
    const [taskId, setTaskId] = useState(null);
    const [completedTaskId, setCompletedTaskId] = useState(null);
    const [error, setError] = useState(null);

    // The API renders one video at a time, so a new upload waits until this one ends
    const processing = taskId !== null && completedTaskId === null && error === null;

    function handleUpload(id) {
        setTaskId(id);
        setCompletedTaskId(null);
        setError(null);
    }

    return (
        <main>
            <h1>sonic-brownian</h1>

            <AudioUpload onUpload={handleUpload} onError={setError} disabled={processing} />
            {taskId && (
                <ProcessingStatus
                    key={taskId}
                    taskId={taskId}
                    onComplete={ setCompletedTaskId }
                    onError={ setError }
                />
            )}
            {completedTaskId && <VideoPlayer taskId={completedTaskId} />}
            {error && <ErrorMessage message={error} />}
        </main>
    );
}

export default App;
