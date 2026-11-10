import { useEffect, useState } from "react";

import { combinedVideoUrl, getVideoStatus } from "../services/api.js";

const POLL_INTERVAL_MS = 3000;

// Combined Download component: link to the side-by-side video (particles on the left, entropy over time on the right)
// That video is rendered after the main one is ready, so this polls the status until it is ready (or failed)
export function CombinedDownload({ taskId }) {
    const [status, setStatus] = useState("running");

    useEffect(() => {
        if (!taskId) return;
        let timeoutId;
        let cancelled = false;
        setStatus("running");

        async function check() {
            try {
                const result = await getVideoStatus(taskId);
                if (cancelled) return;
                const combined = result.combined_status ?? "running";
                setStatus(combined);
                if (combined === "pending" || combined === "running") {
                    timeoutId = setTimeout(check, POLL_INTERVAL_MS);
                }
            } catch (error) {
                if (cancelled) return;
                console.error("Failed to get the status of the combined video:", error);
                setStatus("failed");
            }
        }
        check();

        return () => {
            cancelled = true;
            clearTimeout(timeoutId);
        };
    }, [taskId]);

    if (status === "ready") {
        return (
            <p>
                <a href={combinedVideoUrl(taskId)} download>Baixar vídeo com partículas e entropia lado a lado</a>
            </p>
        );
    }
    if (status === "failed" || status === "unavailable") {
        return <p className="status-line">Vídeo lado a lado indisponível.</p>;
    }
    return <p className="status-line">Preparando o vídeo com partículas e entropia lado a lado…</p>;
}
