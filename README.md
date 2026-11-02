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

## Mapeamento

Implementado em `src/mapping.py`; os valores da tabela ficam em `src/hyperparameters.py`. Velocidades e distâncias estão em pixels por quadro, no domínio de 1920×1080 do `config/default.yaml`.

| Parâmetro físico     | Feature                                   | Como                                                                 | Efeito visível |
|----------------------|-------------------------------------------|----------------------------------------------------------------------|----------------|
| Viés vertical μ_y    | centroide espectral, em oitavas           | quanto o centroide subiu em relação aos últimos 3 s (1 oitava → viés máximo) | som ficando mais agudo faz a nuvem subir, e ela fica lá enquanto o registro se mantém |
| Viés horizontal μ_x  | fração da energia: agudos − graves        | mudança em relação aos últimos 3 s (0,2 → viés máximo)               | mais agudos empurram para a direita, mais graves para a esquerda |
| Ruído σ              | RMS em dB, normalizado na faixa           | de 0,6 a 5 px/quadro                                                 | música forte agita as partículas |
| Fricção γ            | planicidade espectral, em dB absoluto     | de −50 dB (tom puro) a −5 dB (ruído branco) → γ de 0,1 a 0,9          | tonal → caminhos longos e suaves; ruidoso → caminhos erráticos |
| Impulso              | picos de onset 1,0 acima da mediana do último segundo | dilatação a partir do centro da nuvem (40 px na distância típica), desfeita 4 quadros depois | a cada ataque a nuvem incha e volta, sem abrir buraco no meio |
| Presença             | RMS absoluto, de −60 a −30 dBFS           | multiplica a deriva e o ruído                                        | no silêncio a nuvem fica parada |
| Matiz                | chroma                                    | média circular das 12 notas, ponderada pelo chroma, na ordem de Castel (Dó azul, Sol vermelho, Lá violeta; 30° por semitom) | a cor acompanha a harmonia |
| Luminosidade         | centroide espectral, em oitavas, normalizado na faixa | OKLCH L de 0,55 a 0,92                                   | sons brilhantes, cores claras |
| Croma (saturação)    | RMS em dB, normalizado na faixa × presença | OKLCH C de 0,07 a 0,20; 0 no silêncio                               | música forte, cores vivas; silêncio cinza |
| Variação entre partículas | —                                    | desvio fixo de matiz de até ±15° por partícula                       | a nuvem não fica chapada |
| Rastro               | —                                         | a imagem é multiplicada por 0,9 a cada quadro, em vez de apagada      | as trajetórias ficam visíveis |

As cores estão em OKLCH (`src/color.py`), um espaço em que passos iguais de luminosidade, croma ou matiz parecem mudanças iguais. A paleta de cada faixa ao longo do tempo está em `notebooks/palette.ipynb`.

Por que algumas features usam escala absoluta e não a normalização por faixa: normalizada dentro da própria faixa, uma senoide constante fica igual ao silêncio, e o ruído branco fica igual à senoide.

Por que a deriva segue a *mudança* do som e não o seu valor: com o valor, o silêncio (centroide 0) empurraria a nuvem para baixo sem parar, e a varredura de 100 Hz a 4 kHz faria a nuvem descer na primeira metade. Seguindo a mudança, a posição da nuvem acompanha o registro.

A deriva, o ruído e o impulso são definidos como o que se vê (velocidade da nuvem, velocidade das partículas, distância do empurrão) e convertidos para μ, σ e o impulso da equação usando γ. Assim, a fricção muda só a textura do movimento, e não a velocidade.

### Leitura discreta: probabilidades de direção

O viés b ∈ [−1, 1] de cada eixo é o desequilíbrio entre as chances de andar para cada lado. Num passeio em rede com passos de tamanho *a*:

```
P(direita) = (1 + bₓ) / 2        P(esquerda) = (1 − bₓ) / 2
```

- bₓ = 0: os dois lados são equiprováveis (browniano puro).
- bₓ = 1: sempre para a direita; bₓ = −1: sempre para a esquerda.
- Em média, cada passo anda a · bₓ.

No código, bₓ e b_y vêm de `compute_bias` (`src/mapping.py`) e viram a deriva μ = γ · G · b · presença, com G o ganho em px/quadro.

## Stack

Python com `librosa`, `numpy` e `scipy` (áudio e simulação), `pygame` (pré-visualização em tempo real), `imageio-ffmpeg` (exportação em vídeo), `matplotlib`, `pandas` e Jupyter (análise).

## Estrutura planejada

```
config/        presets YAML do mapeamento
data/audio/    faixas de teste e sinais sintéticos
src/
  features.py    extração e normalização
  mapping.py     features → parâmetros físicos e cores
  hyperparameters.py  ganhos, escalas, suavização, cor e rastro
  color.py       conversão OKLCH → sRGB
  simulation.py  passeio browniano condicionado
  conditional_visualization.py  pré-visualização com o áudio tocando
  render.py      exportação em vídeo
  evaluate.py    métricas de coerência
notebooks/     exploração e figuras
tests/         testes do modelo
```

## Uso

```bash
pip install -r requirements.txt

# Pré-visualização com o áudio tocando
python -m src.conditional_visualization <caminho_da_musica>
```


## Referências

1. Tzanetakis, G.; Cook, P. *Musical genre classification of audio signals*. IEEE Trans. Speech and Audio Processing, 2002.
2. Kramer, G. et al. *Sonification Report: Status of the Field and Research Agenda*. 1999.
3. Kubelka, O. et al. *Interactive music visualization*. CESCG, 2000.
4. Barnet, E. H. *A perfect fifth of blue and red: Enlightened harmonies of the senses*. J. Canadian Historical Association, 2019.
5. Ullmann, D. *Life and work of E.F.F. Chladni*. Eur. Phys. J. Special Topics, 2007.

## Licença

[MIT](LICENSE)
