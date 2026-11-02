// Empty in development: Vite's proxy (vite.config.js) forwards /api to the FastAPI server
const API_URL = import.meta.env.VITE_API_URL ?? "";


// FastAPI puts the reason in "detail": a string, or a list of validation errors
async function errorMessage(response, action) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : body?.detail?.[0]?.msg;
    return `${action}: ${detail ?? response.statusText}`;
}


export async function checkHealth() {
    const response = await fetch(`${API_URL}/api/health`);
    return response.ok;
}


export async function uploadAudio(file, nParticles){
    const formData = new FormData();
    formData.append("audio", file);
    if (nParticles) {
        formData.append("n_particles", nParticles);
    }

    const response = await fetch(`${API_URL}/api/videos`, {
        method: "POST",
        body: formData,
    });
    if (!response.ok) {
        throw new Error(await errorMessage(response, "Failed to upload audio"));
    }
    return response.json();
}


export async function getVideoStatus(taskId) {
    const response = await fetch(`${API_URL}/api/videos/${taskId}`);
    if (!response.ok) {
        throw new Error(await errorMessage(response, "Failed to get video status"));
    }
    return response.json();
}


// Used directly in <video> and <a>, so the browser streams the MP4 instead of holding it all in memory
export function videoFileUrl(taskId) {
    return `${API_URL}/api/videos/${taskId}/file`;
}
