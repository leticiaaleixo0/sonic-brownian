export const MAX_PARTICLES = 200000;


// Audio Upload component: the audio file and the number of particles (state lives in the parent)
export function AudioUpload({ file, onFileChange, nParticles, onNParticlesChange, disabled }) {
    return (
        <div className="upload-fields">
            <label className="field-label">
                Arquivo de áudio
                <input type="file" accept=".wav,.mp3" disabled={disabled}
                    onChange={(e) => onFileChange(e.target.files[0] ?? null)} />
            </label>
            {file && <p className="field-hint">Selecionado: {file.name}</p>}
            <label className="field-label">
                Partículas (opcional)
                <input type="number" min="1" max={MAX_PARTICLES} placeholder="Padrão do sistema" value={nParticles}
                    disabled={disabled} onChange={(e) => onNParticlesChange(e.target.value)} />
            </label>
        </div>
    );
}
