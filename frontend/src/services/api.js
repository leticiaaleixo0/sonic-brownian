// Empty in development: Vite's proxy (vite.config.js) forwards /api to the FastAPI server
const API_URL = import.meta.env.VITE_API_URL ?? "";


// FastAPI puts the reason in "detail": a string, or a list of validation errors
async function errorMessage(response, action) {
    const body = await response.json().catch(() => null);
    const first = body?.detail?.[0];
    const detail = typeof body?.detail === "string" ? body.detail : first && [first.loc?.at(-1), first.msg].filter(Boolean).join(": ");
    return `${action}: ${detail ?? response.statusText}`;
}


export async function checkHealth() {
    const response = await fetch(`${API_URL}/api/health`);
    return response.ok;
}


// Hyperparameters the video request accepts: [{ name, title, description, type, default, minimum, maximum }]
export async function getHyperparameters() {
    const response = await fetch(`${API_URL}/api/hyperparameters`);
    if (!response.ok) {
        throw new Error(await errorMessage(response, "Failed to load hyperparameters"));
    }
    return response.json();
}


// hyperparameters: only the values that differ from the defaults, keyed by name
export async function uploadAudio(file, nParticles, hyperparameters = {}){
    const formData = new FormData();
    formData.append("audio", file);
    if (nParticles) {
        formData.append("n_particles", nParticles);
    }
    if (Object.keys(hyperparameters).length) {
        formData.append("hyperparameters", JSON.stringify(hyperparameters));
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


// Side-by-side video (particles | entropy), used in <a download>; it exists once the status says combined_status === "ready"
export function combinedVideoUrl(taskId) {
    return `${API_URL}/api/videos/${taskId}/combined`;
}


// Entropy of the particle cloud over time (Fokker–Planck): { task_id, fps, time: [s], entropy: [nats], max_entropy }
export async function getEntropy(taskId) {
    const response = await fetch(`${API_URL}/api/videos/${taskId}/entropy`);
    if (!response.ok) {
        throw new Error(await errorMessage(response, "Failed to get the entropy"));
    }
    return response.json();
}
