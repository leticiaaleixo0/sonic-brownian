import { useEffect, useMemo, useState } from "react";
import { InlineMath } from "react-katex";

import { getEntropy } from "../services/api.js";

const WIDTH = 800;
const HEIGHT = 320;
const MARGIN = { top: 16, right: 24, bottom: 44, left: 56 };
const BUCKETS = 500; // the line keeps the minimum and the maximum of each bucket, so peaks survive


// Step of the ticks: 1, 2 or 5 times a power of ten, giving about `target` ticks over `range`
function niceStep(range, target) {
    const raw = Math.max(range, 1e-9) / target;
    const magnitude = 10 ** Math.floor(Math.log10(raw));
    const normalized = raw / magnitude;
    return (normalized < 1.5 ? 1 : normalized < 3.5 ? 2 : normalized < 7.5 ? 5 : 10) * magnitude;
}

function makeTicks(min, max, target) {
    const step = niceStep(max - min, target);
    const ticks = [];
    for (let value = Math.ceil(min / step) * step; value <= max + step * 1e-6; value += step) {
        ticks.push(Number(value.toPrecision(10)));
    }
    return ticks;
}

// [index, ...] of the points to draw: the minimum and the maximum of each bucket, in time order
function decimate(values, buckets) {
    const n = values.length;
    if (n <= 2 * buckets) return values.map((_, index) => index);
    const indices = [];
    for (let b = 0; b < buckets; b++) {
        const start = Math.floor((b * n) / buckets);
        const end = Math.max(Math.floor(((b + 1) * n) / buckets), start + 1);
        let low = start;
        let high = start;
        for (let i = start + 1; i < end; i++) {
            if (values[i] < values[low]) low = i;
            if (values[i] > values[high]) high = i;
        }
        indices.push(...new Set([low, high]));
    }
    return indices;
}

function buildChart({ time, entropy, max_entropy: maxEntropy }) {
    const duration = time[time.length - 1] || 1;
    // reduce and not Math.min(...values): a long track has too many values to spread as arguments
    const lowest = entropy.reduce((a, b) => Math.min(a, b), Infinity);
    const highest = entropy.reduce((a, b) => Math.max(a, b), maxEntropy);
    const yMin = Math.floor((lowest - 0.2) * 2) / 2;
    const yMax = Math.ceil((highest + 0.1) * 2) / 2;
    const plotWidth = WIDTH - MARGIN.left - MARGIN.right;
    const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
    const x = (seconds) => MARGIN.left + (seconds / duration) * plotWidth;
    const y = (value) => MARGIN.top + (1 - (value - yMin) / (yMax - yMin)) * plotHeight;

    const path = decimate(entropy, BUCKETS)
        .sort((a, b) => a - b)
        .map((index, position) => `${position === 0 ? "M" : "L"}${x(time[index]).toFixed(1)},${y(entropy[index]).toFixed(1)}`)
        .join(" ");

    return { duration, x, y, path, xTicks: makeTicks(0, duration, 8), yTicks: makeTicks(yMin, yMax, 6), plotHeight };
}


// Entropy Chart component: S(t) = -∫ρ ln ρ of the particle cloud along the music, with a marker that follows the video
export function EntropyChart({ taskId, currentTime = 0 }) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!taskId) return;
        let cancelled = false;
        setData(null);
        setError(null);
        getEntropy(taskId)
            .then((result) => !cancelled && setData(result))
            .catch((err) => !cancelled && setError(err.message));
        return () => {
            cancelled = true;
        };
    }, [taskId]);

    const chart = useMemo(() => (data ? buildChart(data) : null), [data]);

    if (error) return <p className="status-line">Gráfico de entropia indisponível. {error}</p>;
    if (!chart) return <p className="status-line">Carregando o gráfico de entropia…</p>;

    const { x, y, path, xTicks, yTicks, plotHeight, duration } = chart;
    const frame = Math.min(Math.max(Math.round(currentTime * data.fps), 0), data.entropy.length - 1);
    const markerTime = data.time[frame];
    const markerValue = data.entropy[frame];

    return (
        <figure className="entropy-chart">
            <figcaption>
                Entropia da distribuição das partículas, <InlineMath math="S(t) = -\int \rho \ln \rho \, dA" />, obtida
                resolvendo a equação de Fokker–Planck a partir da nuvem inicial.
            </figcaption>

            <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Entropia da nuvem de partículas ao longo da música">
                {yTicks.map((tick) => (
                    <g key={`y${tick}`}>
                        <line className="entropy-grid" x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={y(tick)} y2={y(tick)} />
                        <text className="entropy-tick" x={MARGIN.left - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle">{tick}</text>
                    </g>
                ))}
                {xTicks.map((tick) => (
                    <g key={`x${tick}`}>
                        <line className="entropy-grid" x1={x(tick)} x2={x(tick)} y1={MARGIN.top} y2={MARGIN.top + plotHeight} />
                        <text className="entropy-tick" x={x(tick)} y={MARGIN.top + plotHeight + 16} textAnchor="middle">{tick}</text>
                    </g>
                ))}

                {/* entropy of the uniform distribution on the domain: the ceiling the cloud can reach */}
                <line className="entropy-max" x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={y(data.max_entropy)} y2={y(data.max_entropy)} />
                <text className="entropy-max-label" x={WIDTH - MARGIN.right - 4} y={y(data.max_entropy) - 6} textAnchor="end">máximo: distribuição uniforme no quadro</text>

                <path className="entropy-line" d={path} />

                <line className="entropy-playhead" x1={x(markerTime)} x2={x(markerTime)} y1={MARGIN.top} y2={MARGIN.top + plotHeight} />
                <circle className="entropy-marker" cx={x(markerTime)} cy={y(markerValue)} r="4" />

                <text className="entropy-axis-label" x={MARGIN.left + (WIDTH - MARGIN.left - MARGIN.right) / 2} y={HEIGHT - 6} textAnchor="middle">tempo (s)</text>
                <text className="entropy-axis-label" transform={`translate(14 ${MARGIN.top + plotHeight / 2}) rotate(-90)`} textAnchor="middle">S (nats)</text>
            </svg>

            <p className="entropy-readout">
                t = {markerTime.toFixed(1)} s de {duration.toFixed(1)} s · S = {markerValue.toFixed(2)} nats
            </p>
        </figure>
    );
}
