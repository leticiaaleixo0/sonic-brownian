import { useEffect, useState } from "react";

const GROUPS = [
    { title: "Deriva", names: ["vertical_gain", "horizontal_gain", "drift_tau"] },
    { title: "Agitação e fricção", names: ["sigma_min", "sigma_max", "friction_min", "friction_max"] },
    { title: "Ataques", names: ["onset_gain", "onset_threshold", "pulse_frames"] },
    { title: "Partículas e cor", names: ["initial_spread", "trail_decay", "hue_spread", "hue_of_c"] },
];
const NICE_STEPS = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1];


// Largest round step that still gives about 100 positions on the slider
function stepOf(spec) {
    if (spec.type === "integer") return 1;
    const raw = (spec.maximum - spec.minimum) / 100;
    return NICE_STEPS.filter((step) => step <= raw).at(-1) ?? NICE_STEPS[0];
}


function decimalsOf(step) {
    return step >= 1 ? 0 : String(step).split(".")[1].length;
}


// Pairs like sigma_min/sigma_max whose minimum is above the maximum
export function rangeConflicts(specs, values) {
    const valueOf = (name) => values[name] ?? specs.find((spec) => spec.name === name)?.default;
    return specs
        .filter((spec) => spec.name.endsWith("_min"))
        .map((spec) => ({ min: spec, max: specs.find((other) => other.name === spec.name.replace(/_min$/, "_max")) }))
        .filter(({ min, max }) => max && valueOf(min.name) > valueOf(max.name))
        .map(({ min, max }) => `${min.title} está acima de ${max.title}.`);
}


function HyperparameterRow({ spec, value, onChange, onReset, disabled }) {
    const step = stepOf(spec);
    const decimals = decimalsOf(step);
    const [draft, setDraft] = useState(String(value));
    const changed = value !== spec.default;

    // Keeps the text box in sync when the slider or a reset changes the value
    useEffect(() => setDraft(String(value)), [value]);

    function commit(text) {
        const number = Number(text);
        if (text.trim() === "" || !Number.isFinite(number)) {
            setDraft(String(value));
            return;
        }
        const clamped = Math.min(spec.maximum, Math.max(spec.minimum, number));
        onChange(Number(clamped.toFixed(decimals)));
    }

    return (
        <div className={`hp-row${changed ? " hp-row-changed" : ""}`}>
            <div className="hp-row-header">
                <label htmlFor={`hp-${spec.name}`} title={spec.description}>{spec.title}</label>
                <button type="button" className="button-icon" onClick={onReset} disabled={disabled || !changed}
                    title={`Voltar ao padrão (${spec.default})`} aria-label={`Restaurar ${spec.title}`}>↺</button>
            </div>
            <div className="hp-row-controls">
                <input id={`hp-${spec.name}`} type="range" min={spec.minimum} max={spec.maximum} step={step} value={value}
                    disabled={disabled} onChange={(e) => onChange(Number(e.target.value))} />
                <input type="number" min={spec.minimum} max={spec.maximum} step={step} value={draft} disabled={disabled}
                    onChange={(e) => setDraft(e.target.value)} onBlur={(e) => commit(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && commit(e.currentTarget.value)} />
            </div>
            <p className="hp-description">{spec.description}</p>
        </div>
    );
}


// Hyperparameter Panel component: a button opens sliders for each hyperparameter; values holds only the changed ones
export function HyperparameterPanel({ specs, loadError, values, onChange, disabled }) {
    const [open, setOpen] = useState(false);
    const nChanged = Object.keys(values).length;
    const conflicts = rangeConflicts(specs, values);

    function setValue(spec, value) {
        const { [spec.name]: _, ...others } = values;
        onChange(value === spec.default ? others : { ...others, [spec.name]: value });
    }

    function resetValue(spec) {
        const { [spec.name]: _, ...others } = values;
        onChange(others);
    }

    const grouped = GROUPS.map((group) => ({ ...group, specs: group.names.map((name) => specs.find((spec) => spec.name === name)).filter(Boolean) }));
    const ungrouped = specs.filter((spec) => !GROUPS.some((group) => group.names.includes(spec.name)));
    if (ungrouped.length) grouped.push({ title: "Outros", specs: ungrouped });

    return (
        <div className="hp-panel">
            <button type="button" className="button-secondary" onClick={() => setOpen(!open)} aria-expanded={open}
                disabled={!specs.length}>
                {open ? "▾" : "▸"} Ajustar hiperparâmetros{nChanged ? ` (${nChanged} alterado${nChanged > 1 ? "s" : ""})` : ""}
            </button>
            {loadError && <p className="field-hint">Não foi possível carregar os hiperparâmetros: {loadError}</p>}

            {open && (
                <div className="hp-body">
                    {grouped.filter((group) => group.specs.length).map((group) => (
                        <fieldset key={group.title} className="hp-group">
                            <legend>{group.title}</legend>
                            {group.specs.map((spec) => (
                                <HyperparameterRow key={spec.name} spec={spec} value={values[spec.name] ?? spec.default}
                                    onChange={(value) => setValue(spec, value)} onReset={() => resetValue(spec)} disabled={disabled} />
                            ))}
                        </fieldset>
                    ))}
                    {conflicts.map((message) => <p key={message} className="hp-warning">{message}</p>)}
                    <button type="button" className="button-secondary" onClick={() => onChange({})} disabled={disabled || !nChanged}>
                        Restaurar todos os padrões
                    </button>
                </div>
            )}
        </div>
    );
}
