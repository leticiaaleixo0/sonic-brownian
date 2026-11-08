import { useState } from 'react';
import { AudioUpload, ProcessingStatus, VideoPlayer, ErrorMessage } from './components';
import './index.css';
import 'katex/dist/katex.min.css';
import { BlockMath, InlineMath } from 'react-katex';

export default function App() {
  const [taskId, setTaskId] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState(null);

  return (
    <div className="paper-container">
      {/* CABEÇALHO DO ARTIGO */}
      <header className="paper-header">
        <p className="institution">Instituto de Matemática Pura e Aplicada — IMPA Tech, 2026.2</p>
        <h1 className="paper-title">Sonic Brownian: Visualização Computacional da Música Baseada em Sistemas de Partículas</h1>
        <p className="paper-authors">
          Anderson Aquiles, Felipe Giehl, Letícia Aleixo
        </p>
      </header>

      {/* ÁREA DE DEMONSTRAÇÃO (APP) */}
      <section className="demo-section">
        <div className="demo-panel">
          <h3>Demonstração do Modelo</h3>
          <p className="demo-subtitle">Submeta um arquivo de áudio (WAV/MP3) para executar a simulação da equação de Langevin através da API.</p>
          
          {!taskId && (
            <AudioUpload 
              onUpload={(id) => { setTaskId(id); setError(null); }} 
              onError={setError} 
            />
          )}

          {taskId && !isComplete && (
            <ProcessingStatus 
              taskId={taskId} 
              onComplete={() => setIsComplete(true)} 
              onError={setError} 
            />
          )}

          {isComplete && <VideoPlayer taskId={taskId} />}
          
          <ErrorMessage message={error} />
        </div>
      </section>

      <hr className="section-divider" />

      {/* FUNDAMENTAÇÃO TEÓRICA E BASTIDORES */}
      <main className="paper-body">
        <section>
          <h2>1. Resumo do Projeto</h2>
          <p>
            O sistema propõe uma abordagem de processamento de sinais e computação gráfica para visualização musical. 
            O movimento de um sistema de partículas é regido por um <strong>passeio browniano condicionado</strong>. 
            Em vez de adotar passos equiprováveis em todas as direções, as probabilidades de deslocamento, a velocidade 
            e a aceleração são dinamicamente moduladas por características extraídas do som (frequência, intensidade, timbre e ritmo). 
            O trabalho atualiza a tradição histórica de tornar o som visível (como o <em>clavecin oculaire</em> de Castel e as figuras de Chladni) através de modelagem estocástica.
          </p>
        </section>

        <section>
          <h2>2. Arquitetura do Pipeline</h2>
          <div className="pipeline-diagram">
            <span>Áudio</span> → <span>DSP (Librosa)</span> → <span>Mapeamento Físico</span> → <span>Passeio Condicionado</span> → <span>Renderização (Pygame/FFmpeg)</span>
          </div>
        </section>

        <section>
          <h2>3. Modelo Dinâmico: Equação de Langevin</h2>
          <p>
            A simulação governa as partículas através de uma atualização discreta baseada na Equação de Langevin.
            Sendo <InlineMath math="\gamma" /> o coeficiente de fricção, <InlineMath math="\mu" /> o vetor de deriva (bias), <InlineMath math="\sigma" /> a 
            intensidade do ruído termo-acústico e <InlineMath math="\xi" /> um ruído gaussiano padrão:
          </p>
          
          <div className="math-block">
            <BlockMath math="v_{t+1} = (1 - \gamma)v_t + \mu \Delta t + \sigma \sqrt{\Delta t} \, \xi" />
            <BlockMath math="x_{t+1} = x_t + v_{t+1}" />
          </div>
          
          <p>
            No caso trivial onde <InlineMath math="\gamma = 1" /> e <InlineMath math="\mu = 0" />, o modelo perde o condicionamento musical e 
            colapsa em um passeio browniano simples.
          </p>

          <h3>3.1. Probabilidades de Direção (Leitura Discreta)</h3>
          <p>
            O viés direcional <InlineMath math="b \in [-1, 1]" /> introduz um desequilíbrio nas probabilidades de transição na malha. 
            Para passos de tamanho <InlineMath math="a" />:
          </p>
          
          <div className="math-block">
            <BlockMath math="P(\text{direita}) = \frac{1 + b_x}{2}" />
            <BlockMath math="P(\text{esquerda}) = \frac{1 - b_x}{2}" />
          </div>
          
          <p>
            O sistema calcula os vieses <InlineMath math="b_x" /> e <InlineMath math="b_y" />, que são convertidos no vetor de deriva matemática 
            <InlineMath math="\mu = \gamma \cdot G \cdot b \cdot \text{presença}" /> (onde <InlineMath math="G" /> é o ganho em pixels/quadro).
          </p>
        </section>

        <section>
          <h2>4. Mapeamento de Features (Digital Signal Processing)</h2>
          <p>A tabela abaixo descreve o coração algorítmico do projeto: a tradução de matrizes de áudio para variáveis físicas da simulação computacional, avaliadas quadro a quadro no domínio 1920×1080.</p>
          
          <div className="table-wrapper">
            <table className="academic-table">
              <thead>
                <tr>
                  <th>Parâmetro Físico</th>
                  <th>Feature Acústica (Origem)</th>
                  <th>Processamento / Efeito Observável</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Viés vertical (<InlineMath math="\mu_y" />)</strong></td>
                  <td>Centroide espectral</td>
                  <td>Avalia a derivada em relação aos últimos 3s (1 oitava → viés máximo). Som tornando-se agudo desloca a nuvem verticalmente.</td>
                </tr>
                <tr>
                  <td><strong>Viés horizontal (<InlineMath math="\mu_x" />)</strong></td>
                  <td>Fração de energia (agudos vs graves)</td>
                  <td>Variação em 3s (0,2 → viés máximo). Deslocamento lateral da nuvem conforme balanço de frequência.</td>
                </tr>
                <tr>
                  <td><strong>Ruído (<InlineMath math="\sigma" />)</strong></td>
                  <td>RMS (Normalizado)</td>
                  <td>Mapeado linearmente entre 0,6 e 5 px/quadro. Amplitude sonora controla a agitação termodinâmica.</td>
                </tr>
                <tr>
                  <td><strong>Fricção (<InlineMath math="\gamma" />)</strong></td>
                  <td>Planicidade Espectral (Spectral Flatness)</td>
                  <td>Mapeado em escala absoluta (−50 dB a −5 dB). Som tonal (baixo ruído) gera caminhos suaves; Som ruidoso resulta em trajetórias erráticas.</td>
                </tr>
                <tr>
                  <td><strong>Impulso</strong></td>
                  <td>Onsets / Ataques (Peaks)</td>
                  <td>1.0 acima da mediana do último segundo. Gera dilatação vetorial radial desfeita em 4 quadros.</td>
                </tr>
                <tr>
                  <td><strong>Presença</strong></td>
                  <td>RMS Absoluto (−60 a −30 dBFS)</td>
                  <td>Modulador global. Multiplica deriva e ruído; congela o sistema durante o silêncio.</td>
                </tr>
                <tr>
                  <td><strong>Matiz e Cor</strong></td>
                  <td>Chroma (Energia das 12 notas)</td>
                  <td>Média circular das 12 notas (Ordem de Castel: Dó azul, Sol vermelho, Lá violeta). Computado no espaço perceptualmente uniforme OKLCH.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2>5. Justificativas de Modelagem e Design de Software</h2>
          <ul className="academic-list">
            <li>
              <strong>Escalas Absolutas vs Normalizadas:</strong> A planicidade espectral utiliza escala absoluta de dB intencionalmente. 
              Se fosse normalizada por faixa, um tom puro contínuo (senoide) seria matematicamente idêntico ao silêncio, invalidando a física da fricção <InlineMath math="\gamma" />.
            </li>
            <li>
              <strong>Derivada de Frequência vs Valor Estático:</strong> A deriva (<InlineMath math="\mu" />) segue a <em>taxa de variação</em> do som e não o seu valor absoluto. 
              Se utilizasse o valor absoluto, o silêncio empurraria a nuvem para baixo iterativamente, e uma varredura (sweep) linear expulsaria a nuvem do domínio visível.
            </li>
            <li>
              <strong>Espaço de Cor OKLCH:</strong> A conversão sRGB adota o espaço perceptual OKLCH (Lightness, Chroma, Hue), 
              garantindo que deltas matemáticos na música gerem deltas visuais equivalentes à visão humana.
            </li>
          </ul>
        </section>
      </main>
    </div>
  );
}
