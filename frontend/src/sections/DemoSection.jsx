import { useCallback, useEffect, useState } from "react";

import { AudioUpload } from "../components/AudioUpload.jsx";
import { ErrorMessage } from "../components/ErrorMessage.jsx";
import { HyperparameterPanel, rangeConflicts } from "../components/HyperparameterPanel.jsx";
import { ProcessingStatus } from "../components/ProcessingStatus.jsx";
import { ResultView } from "../components/ResultView.jsx";
import { getHyperparameters, uploadAudio } from "../services/api.js";


// Demo Section: the form stays on screen, so the same audio can be rendered again with other hyperparameters
export function DemoSection() {
    const [file, setFile] = useState(null);
    const [nParticles, setNParticles] = useState("");
    const [specs, setSpecs] = useState([]);
    const [specsError, setSpecsError] = useState(null);
    const [hyperparameters, setHyperparameters] = useState({});
    const [taskId, setTaskId] = useState(null);
    const [phase, setPhase] = useState("idle"); // idle | uploading | processing | completed
    const [error, setError] = useState(null);

    useEffect(() => {
        getHyperparameters().then(setSpecs).catch((err) => setSpecsError(err.message));
    }, []);

    const handleComplete = useCallback(() => setPhase("completed"), []);
    const handleError = useCallback((message) => {
        setError(message);
        setPhase("idle");
    }, []);

    const busy = phase === "uploading" || phase === "processing";
    const conflicts = rangeConflicts(specs, hyperparameters);

    async function handleSubmit() {
        setPhase("uploading");
        setError(null);
        try {
            const result = await uploadAudio(file, nParticles, hyperparameters);
            setTaskId(result.task_id);
            setPhase("processing");
        } catch (err) {
            console.error("Failed to upload audio:", err);
            handleError(err.message);
        }
    }

    return (
        <section className="demo-section">
            <div className="demo-panel">
                <h3>Demonstração do Modelo</h3>
                <p className="demo-subtitle">
                    Submeta um arquivo de áudio (WAV/MP3) para executar a simulação da equação de Langevin através da API.
                    Os hiperparâmetros são opcionais: os que não forem alterados usam o padrão do sistema.
                </p>

                <AudioUpload file={file} onFileChange={setFile} nParticles={nParticles} onNParticlesChange={setNParticles} disabled={busy} />
                <HyperparameterPanel specs={specs} loadError={specsError} values={hyperparameters} onChange={setHyperparameters} disabled={busy} />

                <button onClick={handleSubmit} disabled={!file || busy || conflicts.length > 0}>
                    {phase === "uploading" ? "Enviando áudio..." : phase === "processing" ? "Gerando..." : phase === "completed" ? "Gerar novamente" : "Gerar visualização"}
                </button>

                {phase === "processing" && <ProcessingStatus taskId={taskId} onComplete={handleComplete} onError={handleError} />}
                {phase === "completed" && <ResultView taskId={taskId} />}
                <ErrorMessage message={error} />
            </div>
        </section>
    );
}
