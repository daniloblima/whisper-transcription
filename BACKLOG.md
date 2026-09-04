# Backlog — Whisper Transcription

Funcionalidades identificadas mas ainda não implementadas.
Consultar antes de iniciar uma nova sessão de desenvolvimento.

---

## Fluxo atual (referência)

1. Usuário arrasta arquivo de vídeo ou áudio para o app `TranscribeVideo.app` no Dock
2. App chama `transcribe_wrapper.py`, que chama `transcribe_complete.py`
3. Script transcreve com Whisper (GPU do Mac) e faz diarização com Sherpa-ONNX
4. Arquivo final salvo em `~/Downloads/transcrições/`

Modelos em uso:
- Transcrição: `whisper-cpp-models/ggml-medium.bin` (via whisper-cli)
- Diarização: `sherpa-onnx-models/sherpa-onnx-pyannote-segmentation-3-0/`

---

## Melhorias identificadas

### Seleção de modo ao dropar o arquivo

Hoje o app sempre roda transcrição + diarização completa.
Seria útil perguntar ao usuário o modo antes de processar:
- Modo 1: Transcrição simples (mais rápido, sem identificar falantes)
- Modo 2: Transcrição + diarização (fluxo atual)

Implementação provável: dialog AppleScript antes de chamar o script Python.

Nota: não existe "adicionar diarização depois" sem o áudio original. A diarização
precisa do áudio para identificar os falantes — não funciona só com o texto.

---

### Indicação de progresso mais clara

Durante o processamento de arquivos longos, o feedback para o usuário é mínimo.
Melhorar as notificações nativas do macOS para mostrar em qual etapa está
(convertendo áudio, transcrevendo, diarizando).

---

### Configuração de idioma

O script assume português. Para transcrever conteúdo em inglês ou outro idioma,
é necessário editar o código. Seria útil uma forma de passar o idioma como
parâmetro — talvez via nome do arquivo ou dialog de entrada.

---

## Scripts em _archive/

Ficam no Mac mas fora do GitHub. Consultar se precisar:

- `transcribe_fast.py` — versão sem diarização, mais rápida
- `add_diarization_only.py` — tentativa de diarizar transcrição existente (não funciona sem áudio)
- `diarize_with_postprocessing.py` — versão experimental do pipeline de diarização
- `explore_sherpa_api.py` / `explore_sherpa_api2.py` — exploração da API Sherpa-ONNX
- `test_*.py` — scripts de teste de desenvolvimento (threshold, otimização, comparação)
- `podcast` — atalho de linha de comando para transcribe_fast.py

---

## Vindos do lote de 47 aulas (01/09/2026)

Ver `PADROES-DE-ERRO.md` para o detalhe de cada um.

- [ ] **Aviso de inversão de sentido no fim da transcrição.** O script poderia buscar "mais igual", "mais iguais", "simplificação produtiva" e afins, e listar as ocorrências como "conferir no contexto". Não corrigir, só apontar. São os erros que passam despercebidos porque a frase continua plausível.
- [ ] **Relatório de nomes próprios candidatos.** Extrair as palavras capitalizadas, ordenar por frequência e mostrar as de cauda ao lado das formas parecidas mais frequentes. Nome deformado quase sempre aparece com duas ou três ocorrências ao lado da forma correta.
- [ ] **Contagem de invariantes no fim de toda correção em lote.** Carimbos de tempo, marcadores de falante e número de arquivos, comparados com o estado anterior. Deveria ser automático, e não depender de alguém desconfiar.
- [ ] **Sinalizar "%" colado em ano.** Padrão claro, mas correção automática é arriscada onde o texto mistura anos e percentuais. Só apontar.
- [ ] **Suporte a nota de verificação.** Um jeito padronizado de inserir `NOTA DE VERIFICAÇÃO` no corpo mais aviso no cabeçalho, para o caso de erro do palestrante. Hoje é manual.

## Vindos da validação de 50 aulas (02 e 03/09/2026)

Ver `LICOES-APRENDIDAS.md` para o caso concreto de cada um. A parte 11 daquele documento é a lista completa; aqui ficam os que dependem de código.

### Auditoria de correção

- [ ] **Log estruturado de toda correção em lote:** regra, arquivo, posição, texto antes e depois. Hoje não existe, e por isso a auditoria da rodada de 01/09 só foi possível por um acidente: o método deixava espaço órfão onde substituía. Foram 19 cicatrizes, e três delas escondiam fala apagada.
- [ ] **Backup automático antes de lote**, com diff palavra a palavra depois. Já era regra escrita e não foi seguida.
- [ ] **Varredura de cicatriz** por espaço duplo no meio de frase e espaço antes de pontuação. Teste barato, roda em segundos, e foi o que revelou as três edições de fala.
- [ ] **Detecção de correção pela metade:** artigo que não concorda com o substantivo, tipo "é a aparelho de raio-x". Rastro clássico de troca de palavra sem ajuste do resto.

### Glossário

- [ ] **Escopo por entrada:** global, por domínio, por projeto. Sem isso não dá para acrescentar `Levi → Levy`, que vale para economia brasileira e estraga qualquer outro áudio.
- [ ] **Aviso de regra que pegou parcialmente:** se `ministro Levi` casou três vezes e ainda há `Levi` solto no mesmo arquivo, apontar. Aconteceu, e a quarta ocorrência escapou por causa de uma vírgula.
- [ ] **Varredura no acervo a cada correção validada**, com relatório de quantas unidades foram afetadas. Uma busca por `XGini` corrigiu 24 ocorrências em três aulas; uma por `Antonio Serra` corrigiu quatro numa aula ainda não aberta.

### Validação assistida

- [ ] **Consistência interna por arquivo:** sigla grafada de dois jeitos, nome próprio com duas formas. Teria achado sozinho o ECI contra ICI e o Eric contra Erik Reinert.
- [ ] **Índice do material de apoio** como parte do fluxo. De 195 anexos, 125 renderam texto, e foi um deles que resolveu um nome que nem o áudio nem dois modelos resolviam.
- [ ] **Nota de verificação como recurso de primeira classe:** marcação no corpo, aviso no cabeçalho e índice das notas do acervo. Hoje é tudo manual, e são 16 notas em 10 arquivos.
- [ ] **Lista de padrões de alucinação:** créditos de legendagem e afins, sinalizados perto do fim do arquivo. Nunca apagar automaticamente. "Legenda por Sônia Ruberti" fechava duas aulas e não é fala.

### Captura

- [ ] **Distinguir limite temporário de detecção de automação** na mesma mensagem de erro do provedor. As respostas são opostas: esperar um dia num caso, trocar para o navegador do sistema no outro.
