import { videoFileUrl } from "../services/api.js";

// Video Player component: plays the generated video once it's ready, with a link to download it
export function VideoPlayer({ taskId }){
    if (!taskId) return null;
    const url = videoFileUrl(taskId);
    return (
        <div>
            {/* src on <video> itself, so a new task reloads the player (changing a <source> does not) */}
            <video src={url} controls style={{ maxWidth: "100%" }}>
                Seu navegador não reproduz vídeos.
            </video>
            <p>
                <a href={url} download>Baixar vídeo</a>
            </p>
        </div>
    )
}
