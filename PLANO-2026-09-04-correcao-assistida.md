# PLANO — Correção assistida: motor e correção numa aplicação só

> Aberto em 04/09/2026. Documento vivo, no padrão do `PLANO.md` de agosto: cada fase é marcada como concluída aqui e detalhada no `CHANGELOG.md`. Enquanto houver item pendente, este arquivo fica na raiz.

## TL;DR

A transcrição hoje termina no `.md` e a correção começa do zero, com uma sessão de Claude lendo o arquivo inteiro sem nada preparado. O que este plano faz é juntar as duas pontas, na ordem em que cada peça protege a seguinte.

Primeiro a rede de segurança, porque o achado mais duro das lições de 03/09 é que o corretor erra mais que o motor, e quem corrigiu fui eu, editando o arquivo direto, sem rastro. Depois os relatórios que dirigem o olho, que valem igual no áudio de cinco minutos e no curso de cinquenta aulas. Depois os dicionários por tema, que é onde o conhecimento se acumula. Só então a fusão do fluxo, que sem as três peças anteriores seria uma casca em volta do que já existe.

Seis fases, e a última é o resto do backlog. Nada aqui toca o motor: os dois modelos, o limiar de 0,92 e o controle de falantes foram medidos em agosto e continuam valendo inteiros.

---

## Decisões de 04/09/2026, antes de qualquer código

**Evoluir no lugar, sem aplicação nova.** O que muda é a camada depois do motor, não o motor. O ativo do projeto são as 2.322 linhas de `CHANGELOG.md` que registram por que Pyannote saiu, por que o limiar é 0,92 e por que o turbo ganhou do medium por 23 a 11; pasta nova abandonaria esse histórico ou o duplicaria. O nome é questão separada e mais barata: o app pode ser renomeado quando o fluxo novo estiver pronto, que é quando o nome novo passa a descrever alguma coisa.

**O contexto do áudio é um campo de texto livre, curto e opcional.** Não há como a aplicação adivinhar o assunto, e nem sempre importa. Áudio de recado de família entra sem contexto e sai transcrito. Áudio sobre a tese entra com três linhas e aciona o dicionário do tema, os relatórios e o dossiê. O esforço passa a ser declarado pelo dono do material, não inferido pela ferramenta, e some a distinção entre modo acervo e modo avulso: há uma porta só, com um campo que se preenche quando importa.

**A unidade de acúmulo é o tema, não a pasta.** Um áudio isolado sobre economia se beneficia do mesmo dicionário que o curso de cinquenta aulas. Acervo é um tema que por acaso tem muitos arquivos.

**Um nível só de dicionários, sem subtemas.** Se um tema crescer demais, ele se divide em dois temas no mesmo nível e o áudio carrega os dois. Composição em vez de hierarquia, o que evita a pergunta que a árvore obriga a responder toda vez: onde mora o termo que serve aos dois ramos. O gatilho para dividir é observável, não previsto — quando as seções de consulta deixarem de caber numa leitura, ou quando um termo começar a atrapalhar áudios do mesmo tema.

**A segunda passada com outro modelo sai do plano como frente.** Custou quatro horas de máquina por acervo e nenhuma das 351 divergências revelou sozinha um erro que valesse correção. O valor real dela foi auditar a correção anterior, e o log da Fase 1 faz isso melhor e de graça. Ela fica disponível como ferramenta de recuperação para material antigo sem log, e nada mais.

**Anonimização do material de origem.** O repositório é público e os documentos nomeavam o curso, o autor e a plataforma de onde o acervo veio, inclusive atribuindo sete afirmações factualmente incorretas a uma pessoa identificada. Nenhuma lição depende de quem disse. Limpo em 04/09, commit `40ebe01`. O histórico do git guarda as versões antigas e a reescrita foi avaliada e descartada.

---

## Versionamento — proposta, aguardando aprovação

O projeto não tem versionamento nenhum: sem tag, sem número, sem marco. Isso não é urgente por si só, mas vira um problema concreto quando se junta com o que este plano constrói, porque o resultado da ferramenta passa a depender de mais coisas do que hoje.

**A dor real não é ter um número, é saber o que produziu cada arquivo.** Uma transcrição feita hoje sai do `large-v3-turbo` com limiar 0,92 e 145 termos de glossário. A mesma transcrição feita em 2027 sairá de outra combinação, com dicionários temáticos aplicados por cima. Sem carimbo de procedência no arquivo, não há como saber por que dois textos do mesmo áudio diferem, nem se vale reprocessar.

Proposta em três partes, da mais útil para a menos:

**1. Carimbo de procedência em todo arquivo produzido.** O cabeçalho da transcrição passa a registrar versão da ferramenta, modelo de transcrição, modelo de voz, limiar, glossário e dicionários aplicados, e data. Isso é o que resolve a dor, e vale mesmo que o resto da proposta seja recusado.

**2. SemVer com tag git em cada marco.** `MAJOR.MINOR.PATCH`, com regra explícita de quando cada número sobe:

| Número | Sobe quando | Exemplo |
|---|---|---|
| MAJOR | muda o formato de saída ou quebra o que já está em disco | mudar o formato do carimbo de tempo |
| MINOR | capacidade nova, sem quebrar nada | dicionários temáticos, relatórios de suspeita |
| PATCH | correção de defeito, termo novo no glossário | `.opus` aceito, ajuste de regex |

O estado atual, com o motor medido em agosto, seria marcado retroativamente como `v1.0.0`. O que este plano constrói fecha em `v2.0.0`, porque a Fase 4 muda o cabeçalho dos arquivos produzidos.

**3. Versão no CHANGELOG, sem mexer no estilo.** As entradas continuam narrativas e por data, que é o que as torna úteis. Ganham só o número da versão no título, quando houver.

O que a proposta deliberadamente não faz: número de versão em arquivo de configuração separado, changelog gerado por script, ou release no GitHub. Nada disso resolve dor nenhuma aqui, e cada um é uma coisa a manter.

---

## FASE 1 — O aplicador único de correções

**Problema.** Os cinco erros do corretor catalogados nas lições — apagar fala, inventar precisão, corrigir olhando o vizinho, tratar português falado como erro, aplicar correção pela metade — foram todos cometidos em sessão de Claude editando o `.md` direto. Não há backup, não há log, não há verificação. A auditoria de 01/09 só foi possível por acidente, porque o método de substituição deixava espaço órfão onde mexia: 19 cicatrizes, três delas escondendo fala apagada.

A rede de segurança que o `BACKLOG.md` descreve está escrita como se protegesse a correção em lote por script, que é justamente a parte que erra menos.

**O que muda.** A correção deixa de ser edição livre do arquivo e passa a ser uma lista declarada de trocas, aplicada por código, valendo para script e para sessão de Claude sem exceção. O aplicador faz, em toda corrida:

- backup do arquivo antes de qualquer escrita
- log estruturado de cada troca: regra, arquivo, posição, texto antes, texto depois, origem da decisão
- contagem de invariantes antes e depois: carimbos de tempo, marcadores de falante, número de arquivos e bytes quando a operação for de movimentação
- tratamento dos separadores na substituição de expressões com mais de uma palavra, capturando quebra de linha e carimbo como grupos e recolocando entre as palavras novas
- recusa da corrida quando um invariante muda sem que a troca o justifique

**Por que primeiro.** Resolve estruturalmente cinco problemas de uma vez. Fala apagada aparece no log. Correção pela metade fica detectável. O padrão 7, que comeu 34 carimbos em 16 arquivos, deixa de acontecer. E a cicatriz, que hoje é o único instrumento de auditoria, vira desnecessária.

**Critério de sucesso.** Refazer a correção de uma aula do acervo com o aplicador e obter, sem nenhuma leitura humana, um log que aponte as três edições de fala que em 01/09 levaram dois dias para aparecer.

**Estado:** [x] CONCLUÍDA em 04/09/2026. `aplicar_correcoes.py` e `FORMATO-CORRECOES.md` na raiz, skill ligada ao aplicador.

O critério foi cumprido por um caminho mais forte que o previsto: em vez de detectar a edição de fala depois de feita, o aplicador a recusa antes. A tentativa de trocar `S11D, ou SD11` por `S11D`, que é o caso real de 01/09, é rejeitada com a corrida inteira, porque a troca encurta a fala e não traz declaração de remoção.

Dois defeitos apareceram no primeiro teste e foram corrigidos antes de qualquer uso. O primeiro é irônico: ao sobrar separador numa substituição que encurta, o módulo recolocava espaço em branco no fim e produzia exatamente a cicatriz que existe para impedir. Passou a descartar separador em branco e a preservar só o que carrega carimbo ou marcador. O segundo é que a trava de remoção só olhava `para` vazio, e o caso real de 01/09 não era vazio, era encurtamento — passou a recusar toda troca que reduza a contagem de palavras sem declaração.

Medido no acervo de 50 aulas, em cópia: 183 trocas em 41 arquivos em 0,16 s, dez delas atravessando carimbo de tempo, com os 29.795 carimbos e os 51 marcadores de falante intactos e nenhuma cicatriz introduzida. O acervo tem 14.662 pontos em que duas palavras vizinhas estão separadas por um carimbo, o que mostra que o padrão 7 não era caso raro.

---

## FASE 2 — Relatórios de suspeita, e o dossiê

**Problema.** Os erros que importam são gramaticalmente corretos e passam por revisão inteira sem nada acusar. "Fez o ato" onde se lê "fez o Atlas", "ICI" onde a mesma aula diz ECI seis vezes, "os continentes mais iguais do mundo" onde o parágrafo argumenta o contrário. Hoje a única forma de achar isso é ler tudo.

**O que muda.** Um conjunto de varreduras que roda em segundos, sem contexto nenhum, e não corrige nada:

- inversão de sentido: "mais igual", "mais iguais", "menos desigual", "simplificação" perto de "produtiva", "industrial" ou "complexidade"
- `%` colado em ano
- alucinação conhecida do motor: crédito de legendagem, "inscreva-se no canal", "obrigado por assistir", sinalizada com peso maior perto do fim do arquivo
- nomes próprios candidatos: capitalizadas por frequência, com as de cauda ao lado das formas parecidas mais frequentes
- consistência interna: sigla grafada de dois jeitos no mesmo arquivo, nome próprio com duas formas
- cicatriz: espaço duplo no meio de frase, espaço antes de pontuação
- correção pela metade: artigo que não concorda com o substantivo

A saída é um documento no formato do `00 A RESOLVER`, com arquivo e instante de cada ponto, agrupado por natureza. É a terceira camada virando entregável sem eu escrever à mão.

**Critério de sucesso.** Rodar sobre as 50 aulas já conferidas e reencontrar os casos conhecidos: as quatro ocorrências de "des" comido, as duas de "simplificação", o ECI contra ICI, as duas alucinações de legendagem. O que ele achar além disso é ganho; o que ele não achar vira caso de teste.

**Estado:** [x] CONCLUÍDA em 04/09/2026. `varrer_suspeitas.py` na raiz, skill ligada a ele.

Testado contra dois corpora do mesmo acervo, que é o contraste que mede calibragem: as 47 aulas da segunda passada, que nunca receberam correção de contexto, e as 50 aulas conferidas em três rodadas. O primeiro rende 123 pontos, o segundo 80, e as duas alucinações de legendagem aparecem só no primeiro, porque no segundo já foram tratadas.

Os casos conhecidos foram reencontrados, e o ECI contra ICI custou um ajuste: sigla de três letras com uma diferente dá semelhança 0,67, abaixo de qualquer corte razoável para nome. Passou a usar distância de uma letra quando a forma tem até quatro caracteres.

A calibragem foi o trabalho da fase, não as varreduras. A primeira versão devolvia 543 pontos, quase todos ruído de palavra comum capitalizada por estar em começo de frase. O critério que resolveu não usa lista de exceções: palavra que aparece em minúscula três vezes ou mais no acervo não é nome próprio. Com ele, mais o descarte de plural, de algarismo romano e do texto editorial das notas, a fila caiu para 123.

**Precisão medida, e ela é desigual de propósito.** Numa amostra de 25 achados de nome no material cru, cerca de metade são deformação real: Reinhardt por Reinert, Kroningen por Groningen, Hasma por Hausmann, Donésia por Indonésia, Emitidos por Emirados. No material já revisado a proporção despenca, e das sete conferidas à mão só duas eram erro. Isso não é defeito: é a varredura concordando com o trabalho já feito. A consequência de desenho é que o relatório se gera logo depois da transcrição, não depois da revisão.

**As duas que escaparam de três rodadas**, achadas por ela e conferidas no texto: "urnas de Polia" onde o dicionário manda "urnas de Pólya", e "Gines muito diferentes" onde se lê "Ginis".

---

## FASE 3 — Dicionários por tema, e o campo de contexto

**Problema.** O `glossario.json` é global, então `Levi → Levy` não tem casa: vale em economia brasileira e estraga qualquer outro áudio. O termo ficou de fora e a quarta ocorrência de uma aula escapou por causa de uma vírgula. E o conhecimento acumulado no curso — 145 termos, quem é quem, decisões que não se reabrem — vive hoje dentro da pasta do doutorado, onde nenhuma outra transcrição o alcança.

**O que muda.**

`dicionarios/` na raiz do projeto, ignorada pelo git, um nível só. Cada tema é uma pasta com dois arquivos: o `.md` que guarda o porquê de cada decisão, com fonte, e o `.json` com as substituições determinísticas. Um dicionário de exemplo fica versionado, servindo de formato e de documentação, no mesmo padrão que hoje separa `glossario.json` de `glossario.local.json`.

Cada dicionário abre com um bloco no formato do frontmatter de skill: nome do tema, uma linha do que cobre, quando usar. A aplicação lê só esse bloco de todos os dicionários, o que custa nada, e propõe os que combinam com o texto de contexto. Mais de um pode ser aprovado na mesma transcrição, porque um áudio real cruza assuntos.

O `glossario.json` da raiz continua sendo o dicionário geral, com o critério que já está escrito dentro dele: só entra erro cujo acerto é sempre o mesmo, independentemente do assunto. Ele ganha o par que hoje não tem, um `.md` com o porquê, para a estrutura ficar simétrica.

**Migração do dicionário de economia.** O `Dicionário de economia para transcrição.md` tem duas naturezas dentro. As seções 1 a 3 (formas corretas, decidido, erros do falante) e a 6 (quem é quem, com fonte) são temáticas e vão para `dicionarios/economia/`. As seções 4 e 5 (correções aula a aula, curva do glossário) são registro daquele trabalho e ficam no doutorado, com ponteiro de um para o outro. Corte feito com o cuidado de sempre, porque é documento já lido.

**Critério de sucesso.** Um áudio novo sobre economia, sem relação com o curso, transcrito com o dicionário do tema carregado, e o relatório mostrando quais termos do tema foram aplicados. E `Levi → Levy` existindo sem quebrar nada.

**Estado:** não iniciada.

---

## FASE 4 — A fusão do fluxo

**Problema.** Hoje são duas coisas com uma emenda manual. O `transcribe_complete.py` produz o `.md` e para; a skill `/arrumar-transcricao` começa lendo esse arquivo do zero, sem nada preparado e sem saber o que o script já fez.

**O que muda.** Um caminho só, da entrada do arquivo até o texto conferido:

1. campo de contexto, livre e opcional
2. proposta dos dicionários que combinam, para aprovação
3. transcrição e diarização, como hoje
4. glossário geral mais os dicionários aprovados, pelo aplicador da Fase 1
5. varreduras da Fase 2, gerando o dossiê
6. correção assistida começando do dossiê, não do arquivo cru
7. termos novos propostos ao fim, já com o destino sugerido: geral ou qual tema
8. carimbo de procedência no cabeçalho do arquivo produzido

Sem contexto declarado, o caminho para em 4 e entrega a transcrição. É o que o droplet faz hoje, preservado.

**Critério de sucesso.** Arrastar um arquivo e chegar ao texto conferido sem que eu precise reconstruir contexto nenhum no meio, e sem terminal em nenhum ponto.

**Estado:** não iniciada.

---

## FASE 5 — O que faltava virar recurso de verdade

Cada item nasceu de um caso concreto e hoje é manual.

- **Nota de verificação como recurso de primeira classe.** Marcação no corpo, aviso no cabeçalho e índice das notas do acervo. São 16 notas em 10 arquivos, todas escritas à mão.
- **Índice do material de apoio dentro do fluxo.** Generalizar o `indexar_anexos.py`, que hoje vive na pasta do curso com caminho absoluto no topo. O anexo é a terceira parada na ordem de consulta e resolveu o que nem o áudio nem dois modelos resolviam.
- **Varredura no acervo a cada correção validada**, com relatório de quantas unidades foram afetadas. É de onde vem o maior ganho medido: uma busca por XGini corrigiu 24 ocorrências em três aulas.
- **Métrica separando ocorrências de tipos**, e acompanhando a busca externa caindo em vez do glossário subindo.

**Estado:** não iniciada.

---

## FASE 6 — O resto do backlog

Sem ordem interna definida, a decidir quando as anteriores fecharem.

- filtro de muletas de fala, com a versão limpa ao lado da bruta e nunca por cima
- escolha de modo ao dropar o arquivo, e progresso mais claro durante o processamento
- distinção entre limite temporário e detecção de automação na mensagem de erro da captura
- acoplamento do DownloaderApp, já colocado como terceira evolução
- segunda passada como ferramenta de recuperação para material antigo sem log

**Estado:** não iniciada.

---

## Riscos conhecidos

**A Fase 1 pode engessar a correção.** Obrigar toda troca a passar por uma lista declarada é mais lento que editar o arquivo. A aposta é que o custo se paga na primeira vez que um log evitar uma fala apagada. Se na prática o atrito for grande demais, o ajuste é no formato da declaração, não na existência dela.

**As varreduras da Fase 2 podem gerar ruído demais.** Uma lista de duzentos pontos por arquivo não é dossiê, é outra forma de ler tudo. A medida é a proporção de pontos que viram correção: se for baixa, a varredura aperta o critério em vez de a lista crescer.

**Dicionário temático cresce e vira leitura cara.** A ordem de consulta pede ler as seções principais antes de conferir. Com 145 termos isso cabe; com mil, não. É o gatilho de divisão descrito acima, e ele não se antecipa.

**O julgamento continua sem automatizar.** Distinguir "Serra Leoa da vida" de erro de transcrição exige conhecer português falado e o assunto. Nada aqui muda isso: o sistema sinaliza candidatos e quem decide é humano, ou um modelo com o contexto do domínio na mão.

---

*Aberto em 04/09/2026. Decisões desta data registradas acima; o detalhe de cada fase entra no `CHANGELOG.md` conforme for executada.*
