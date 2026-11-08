import { useState, useEffect } from "react";
import { uploadAudio, getVideoStatus, videoFileUrl } from "./services/api.js";

const POLL_INTERVAL_MS = 2000;
const MAX_PARTICLES = 200000;


// Audio Upload component: picks the audio and the number of particles, and starts the pipeline
export function AudioUpload({ onUpload, onError, disabled }){
    const [file, setFile] = useState(null);
    const [nParticles, setNParticles] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleUpload(){
        if (!file) return;
        setLoading(true);
        try{
            const result = await uploadAudio(file, nParticles);
            onUpload?.(result.task_id);
        } catch (error){
            console.error("Failed to upload audio:", error);
            onError?.(error.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="card">
            <h2>🎵 Sonic Brownian</h2>
            <p>
                <input type="file" accept=".wav,.mp3" onChange={(e) => setFile(e.target.files[0] ?? null)} />
            </p>
            <p style={{ textAlign: "left" }}>
                <label>
                    Partículas (opcional):
                    <input type="number" min="1" max={MAX_PARTICLES} placeholder="Padrão do sistema" value={nParticles}
                        onChange={(e) => setNParticles(e.target.value)} />
                </label>
            </p>
            <button onClick={handleUpload} disabled={!file || loading || disabled}>
                {loading ? "Enviando áudio..." : "Gerar visualização"}
            </button>
        </div>
    )
}


// Processing Status component
export function ProcessingStatus({ taskId, onComplete, onError }) {
    const [status, setStatus] = useState("checking…");
    useEffect(() => {
        if (!taskId) return;
        let timeoutId;
        let cancelled = false;

        async function checkStatus() {
            try {
                const result = await getVideoStatus(taskId);
                if (cancelled) return;

                setStatus(result.status);

                if (result.status === "completed") {
                    onComplete?.(taskId);
                    return;
                }
                if (result.status === "failed") {
                    onError?.(result.error ?? "Video generation failed");
                    return;
                }
                // Continue polling while the task is not finished
                if (["queued", "running"].includes(result.status)) {
                    timeoutId = setTimeout(checkStatus, POLL_INTERVAL_MS);
                }
            } catch (error) {
                if (cancelled) return;
                console.error("Failed to get video status:", error);
                setStatus("error");
                onError?.(error.message);
            }
        }
        checkStatus();

        // Cleanup: stop scheduled requests when taskId changes or the component is unmounted
        return () => {
            cancelled = true;
            clearTimeout(timeoutId);
        };
    }, [taskId, onComplete, onError]);

    return <p>Task {taskId}: {status}</p>;
}


// Video Player component: plays the generated video once it's ready, with a link to download it
export function VideoPlayer({ taskId }){
    if (!taskId) return null;
    const url = videoFileUrl(taskId);
    return (
        <div>
            {/* src on <video> itself, so a new task reloads the player (changing a <source> does not) */}
            <video src={url} controls style={{ maxWidth: "100%" }}>
                Your browser does not support the video tag.
            </video>
            <p>
                <a href={url} download>Download video</a>
            </p>
        </div>
    )
}


// Error Message component: displays an error message if something goes wrong
export function ErrorMessage({ message }){
    if (!message) return null;
    return (
        <div style={{ color: "red" }}>
            <p>Error: {message}</p>
        </div>
    )
}
