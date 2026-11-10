from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src import hyperparameters as hp

TaskStatus = Literal["queued", "running", "completed", "failed"]
Resolution = Literal["low", "medium", "high"]
RESOLUTION_NAMES = {"low": "Baixa", "medium": "Média", "high": "Alta"}


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


class VideoResponse(BaseModel):
    task_id: str
    status: TaskStatus


CombinedStatus = Literal["pending", "running", "ready", "failed", "unavailable"]


class VideoStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    video_url: str | None = None
    error: str | None = None
    combined_status: CombinedStatus | None = Field(None, description="Side-by-side video (particles | entropy); it is rendered after the main video is completed.")
    combined_video_url: str | None = Field(None, description="Set when combined_status is ready.")


class EntropyResponse(BaseModel):
    """Entropy S(t) = -∫ρ ln ρ of the particle density, from the Fokker–Planck equation (src/fokker_planck.py)."""
    task_id: str
    fps: int = Field(description="Frames per second of the video; time[i] = i / fps.")
    time: list[float] = Field(description="Time (s) of each entropy value; the first is the initial cloud (t = 0).")
    entropy: list[float] = Field(description="Entropy (nats) at each time.")
    max_entropy: float = Field(description="ln(width × height): the entropy of the uniform distribution on the domain.")


class Hyperparameters(BaseModel):
    """Hyperparameters the interface can change; title and description are the labels it shows."""
    model_config = ConfigDict(extra="forbid")

    resolution: Resolution = Field(hp.RESOLUTION, title="Resolução do vídeo", description="Só a nitidez muda: o movimento é o mesmo nas três. Resoluções maiores demoram mais para renderizar.")
    vertical_gain: float = Field(hp.VERTICAL_GAIN, ge=0, le=5, title="Ganho vertical", description="Velocidade de subida/descida da nuvem quando o som fica mais agudo/grave (px/quadro).")
    horizontal_gain: float = Field(hp.HORIZONTAL_GAIN, ge=0, le=5, title="Ganho horizontal", description="Velocidade lateral da nuvem quando mudam agudos e graves (px/quadro).")
    drift_tau: float = Field(hp.DRIFT_TAU, ge=0.5, le=10, title="Memória da deriva", description="Segundos de passado recente com que o som é comparado para definir a deriva.")
    sigma_min: float = Field(hp.SIGMA_MIN, ge=0, le=10, title="Ruído mínimo (σ)", description="Agitação das partículas no trecho mais baixo da faixa (px/quadro).")
    sigma_max: float = Field(hp.SIGMA_MAX, ge=0, le=20, title="Ruído máximo (σ)", description="Agitação das partículas no trecho mais forte da faixa (px/quadro).")
    friction_min: float = Field(hp.FRICTION_MIN, ge=0.01, le=1, title="Fricção mínima (γ)", description="Fricção para sons tonais: caminhos longos e suaves.")
    friction_max: float = Field(hp.FRICTION_MAX, ge=0.01, le=1, title="Fricção máxima (γ)", description="Fricção para sons ruidosos: caminhos erráticos.")
    onset_gain: float = Field(hp.ONSET_GAIN, ge=0, le=150, title="Força do impulso", description="Quanto a nuvem incha a cada ataque (px na distância típica).")
    onset_threshold: float = Field(hp.ONSET_THRESHOLD, ge=0, le=5, title="Limiar de ataque", description="Quanto um pico de onset precisa passar da mediana do último segundo para contar.")
    pulse_frames: int = Field(hp.PULSE_FRAMES, ge=1, le=30, title="Duração do impulso", description="Quadros até o impulso de cada ataque ser desfeito.")
    initial_spread: float = Field(hp.INITIAL_SPREAD, ge=0.01, le=0.5, title="Espalhamento inicial", description="Desvio padrão da nuvem inicial, como fração da altura do quadro.")
    trail_decay: float = Field(hp.TRAIL_DECAY, ge=0, le=0.99, title="Persistência do rastro", description="Fração do rastro mantida de um quadro para o outro (0 = sem rastro).")
    hue_spread: int = Field(hp.HUE_SPREAD, ge=0, le=90, title="Variação de matiz", description="Desvio máximo de matiz de cada partícula, em graus.")
    hue_of_c: float = Field(hp.HUE_OF_C, ge=0, le=359, title="Matiz do Dó", description="Matiz OKLCH da nota Dó; as outras notas seguem a ordem de Castel (−30° por semitom).")

    @model_validator(mode="after")
    def _check_ranges(self):
        if self.sigma_min > self.sigma_max:
            raise ValueError("sigma_min must not exceed sigma_max.")
        if self.friction_min > self.friction_max:
            raise ValueError("friction_min must not exceed friction_max.")
        return self

    def overrides(self):
        """The values keyed by the constant names of hyperparameters.py, for hyperparameters.resolve."""
        return {name.upper(): value for name, value in self.model_dump().items()}


class HyperparameterOption(BaseModel):
    value: str
    label: str


class HyperparameterSpec(BaseModel):
    name: str
    title: str
    description: str
    type: Literal["integer", "number", "string"]
    default: float | str
    minimum: float | None = None
    maximum: float | None = None
    options: list[HyperparameterOption] | None = None
