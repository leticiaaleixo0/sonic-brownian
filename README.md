# sonic-brownian

**Visualização Computacional da Música: uma abordagem baseada em sistemas de partículas**

Anderson Aquiles, Felipe Giehl, Letícia Aleixo — IMPA Tech, 2026.2

> Projeto em desenvolvimento.

## Sobre

O sistema recebe um arquivo de áudio e gera um vídeo de partículas sincronizado com a música. O movimento das partículas segue um **passeio browniano condicionado**: em vez de passos equiprováveis em todas as direções, as probabilidades de deslocamento, a velocidade e a aceleração dependem, quadro a quadro, das características extraídas do som (frequência, intensidade, timbre e ritmo).

O projeto retoma uma tradição antiga de tornar o som visível, do *clavecin oculaire* de Castel às figuras de Chladni, usando ferramentas atuais de processamento de sinais e computação gráfica.

## Pipeline

```
áudio (WAV/MP3) → features → mapeamento → browniano condicionado → renderização → pré-visualização / MP4
                                   └──────→ paleta de cores ───────────┘
```

A simulação usa uma atualização de Langevin, em que γ é a fricção, μ a deriva, σ a intensidade do ruído e ξ um ruído gaussiano padrão:

```
v[t+1] = (1 − γ)·v[t] + μ·Δt + σ·√Δt·ξ
x[t+1] = x[t] + v[t+1]
```

Com γ = 1 e μ = 0, o modelo se reduz ao browniano puro.

## Mapeamento inicial

| Parâmetro físico     | Feature                           | Efeito visível                              |
|----------------------|-----------------------------------|---------------------------------------------|
| Viés vertical μ_y    | centroide espectral (ou f0)       | sons agudos fazem a nuvem subir             |
| Viés horizontal μ_x  | balanço de energia graves × agudos | deriva lateral conforme o registro          |
| Ruído σ              | RMS                               | música forte agita as partículas            |
| Fricção γ            | planicidade espectral             | tonal → movimento fluido; ruidoso → errático |
| Impulso              | força de onset                    | cada ataque empurra a nuvem                 |
| Matiz                | chroma (média circular)           | cor acompanha as classes de altura          |
| Luminosidade         | centroide espectral               | sons brilhantes, cores claras               |

## Stack

Python com `librosa`, `numpy` e `scipy` (áudio e simulação), `pygame` (pré-visualização em tempo real), `imageio-ffmpeg` (exportação em vídeo), `matplotlib`, `pandas` e Jupyter (análise).

## Estrutura planejada

```
config/        presets YAML do mapeamento
data/audio/    faixas de teste e sinais sintéticos
src/
  features.py    extração e normalização
  mapping.py     features → parâmetros físicos e cores
  simulation.py  passeio browniano condicionado
  render.py      pré-visualização e exportação
  evaluate.py    métricas de coerência
notebooks/     exploração e figuras
tests/         testes do modelo
```

## Uso previsto

```bash
python -m src.render faixa.wav --preset calm --out video.mp4
```

## Avaliação

- **Sinais sintéticos** como testes de comportamento: silêncio deixa a nuvem quase parada, a varredura de frequência a faz subir e o ruído branco produz agitação errática.
- **Correlação cruzada** entre as features e as séries visuais (velocidade média, altura média, dispersão, matiz), comparada com um modelo nulo de features embaralhadas no tempo.
- **Mini-estudo perceptivo** com colegas: pareamento áudio–vídeo e nota de coerência.

## Referências

1. Tzanetakis, G.; Cook, P. *Musical genre classification of audio signals*. IEEE Trans. Speech and Audio Processing, 2002.
2. Kramer, G. et al. *Sonification Report: Status of the Field and Research Agenda*. 1999.
3. Kubelka, O. et al. *Interactive music visualization*. CESCG, 2000.
4. Barnet, E. H. *A perfect fifth of blue and red: Enlightened harmonies of the senses*. J. Canadian Historical Association, 2019.
5. Ullmann, D. *Life and work of E.F.F. Chladni*. Eur. Phys. J. Special Topics, 2007.

## Licença

[MIT](LICENSE)
