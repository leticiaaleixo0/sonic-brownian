import { useEffect, useState } from "react";

import { getVideoStatus } from "../services/api.js";

const POLL_INTERVAL_MS = 2000;
const STATUS_LABELS = { queued: "na fila", running: "renderizando o vídeo…", completed: "pronto", failed: "falhou", error: "erro" };

// Processing Status component
export function ProcessingStatus({ taskId, onComplete, onError }) {
    const [status, setStatus] = useState("queued");
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

    return <p className="status-line">Simulação {taskId.slice(0, 8)}: {STATUS_LABELS[status] ?? status}</p>;
}
