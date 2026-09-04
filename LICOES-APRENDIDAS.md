# Lições aprendidas: como validar uma transcrição de conteúdo técnico

Documento de projeto, escrito em 03/09/2026 para servir de base ao desenho de uma aplicação de transcrição com correção assistida.

**A base empírica.** Um curso de economia com 50 aulas, cerca de 200 mil palavras e 28.309 carimbos de tempo, transcrito e corrigido em três rodadas ao longo de três dias: 673 correções em 01/09, 63 em 02/09 e 9 em 03/09. Mais uma aula de pós-graduação de duas horas, capturada por outra ferramenta, com oito falantes.

**O que este documento não é.** Não é a taxonomia dos erros do motor, que está em `PADROES-DE-ERRO.md` e continua valendo. Este aqui trata do que vem depois: como validar, em que ordem procurar, e sobretudo **quais erros o corretor comete**, que se revelaram mais caros que os do Whisper.

---

## TL;DR

Sete coisas, e as três primeiras são contraintuitivas:

1. **Transcrever duas vezes com modelos diferentes quase não serve para achar erro.** Dos 351 pontos em que dois modelos discordaram, nenhum revelou erro que valesse correção sozinho. O valor da segunda passada foi outro, e indireto.
2. **O erro que importa é aquele em que os dois modelos concordam.** É plausível, gramatical e sobrevive a qualquer comparação. Só se pega contra o mundo.
3. **O corretor erra mais que o motor, e de forma mais perigosa.** O motor produz absurdo detectável; o corretor produz plausibilidade falsa. Três dos erros mais graves do período foram introduzidos ao corrigir.
4. **O áudio é a última fonte, não a primeira.** Resolve pouco: quando os dois modelos discordam, nenhum arbitra.
5. **O material que acompanha o áudio resolve o que o áudio não resolve.** Anexo, slide, ementa — a fonte que o próprio autor escolheu costuma trazer a referência completa.
6. **Correção em lote deixa cicatriz, e a cicatriz é o melhor instrumento de auditoria que existe.**
7. **O conhecimento acumulado transfere entre unidades.** Uma pesquisa feita na aula 5 corrigiu quatro erros na aula 40 antes de ela ser aberta.

---

# Parte 1 — Por que conteúdo técnico é um problema diferente

## 1.1 O erro perigoso é gramaticalmente correto

Transcrição comum se avalia por WER, taxa de erro por palavra. Para conteúdo técnico essa métrica engana, porque trata todos os erros como iguais e eles não são.

Três exemplos reais, todos sobreviventes de uma primeira rodada de correção:

> "o Hausmann, professor de Harvard, da Kennedy School, **fez o ato** junto com o César Hidalgo"

O certo é "fez o **Atlas**". Hausmann e Hidalgo são coautores do *Atlas of Economic Complexity*, citado dois minutos antes na mesma aula. "Fez o ato" é uma expressão possível em português, então nada acusa.

> "isso daqui a gente tira do **ICI**, do indicador de complexidade"

O certo é **ECI**. As outras seis ocorrências da mesma aula dizem ECI, e a própria frase define a sigla corretamente. Uma letra trocada, zero sinais de alarme.

> "A água é **o bico**, o ar é **o bico**"

O certo é "ubíquo", conceito central daquela aula. Aqui o absurdo é visível, e ainda assim passou por uma revisão inteira.

**Consequência de desenho:** a métrica útil não é WER, é *quantos erros que mudam sentido sobraram*. Um sistema que reduz o WER de 8% para 5% mas não toca nesses três não melhorou nada para quem vai estudar pelo texto.

## 1.2 A homofonia é o inimigo, e ela é local

O motor não escolhe entre "certo" e "errado", escolhe entre candidatos que soam igual. Quem desempata é o domínio, e o motor não tem domínio.

- "aparelho de raio-x" e "a parede de raio-x" soam igual
- "fazer as vezes de" e "às vezes" soam igual
- "ubíquo" e "o bico" soam igual
- "XGini" e "ex-Gini" soam igual
- "Roderick" e "Frederick" soam quase igual, e o contexto tinha um Friedrich List a vinte segundos de distância

**O corolário incômodo:** aumentar a qualidade do motor não resolve. Testamos o `large-v3-turbo` contra o `medium`, e nas divergências o modelo melhor perdeu quase sempre, porque o `medium` estava competindo já corrigido. O ganho vem da camada de validação, não do modelo.

---

# Parte 2 — O que não funciona, e por quê

Registrado porque custou tempo, e porque a intuição leva para lá.

## 2.1 Transcrever duas vezes e comparar

**A ideia.** Rodar um segundo modelo sobre o mesmo áudio e olhar onde as duas versões divergem. Onde concordam, o áudio é claro; onde divergem, alguém errou.

**O que aconteceu.** 17,8 horas de áudio, quatro horas de máquina, 351 divergências de conteúdo em 50 aulas. **Nenhuma revelou sozinha um erro que valesse correção.** Em praticamente todas, a versão já corrigida estava certa e a segunda passada é que errava, deformando nome próprio: Allyn Young virando "olinhan", Nurkse virando "nurx", Pólya virando "polia", Ha-Joon virando "radion".

**Por que falha.** Dois modelos treinados em corpora parecidos erram parecido. Onde o áudio é ambíguo, os dois produzem a mesma corrupção plausível. E onde um acerta e o outro erra, o diff não diz qual é qual — só aponta o lugar.

**O que a segunda passada de fato entregou**, e que justifica tê-la feito:

- **Serviu de espelho para achar as cicatrizes da correção anterior.** Foi comparando com ela que apareceram os 19 pontos em que a rodada de 01/09 mexera, e foi de lá que saíram os três casos de fala apagada.
- **Confirmou padrões de erro do motor**, mostrando que "des" comido e "%" colado em ano acontecem de novo, em outro modelo.
- **Deu um marcador de dificuldade do áudio**, útil para priorizar leitura.

**Para a aplicação master:** não vender segunda passada como detector de erro. Vender como *auditoria de correção* e como *mapa de trechos difíceis*. E deixar claro que ela custa tempo de máquina proporcional ao acervo.

## 2.2 Recorrer ao áudio como primeira instância

**A ideia.** Na dúvida, ouvir o trecho.

**O que aconteceu.** Isolamos dezenas de trechos e rodamos os dois modelos sobre eles. O resultado típico foi um destes três:

- **Os dois ouvem a mesma coisa errada.** Foi o caso de "fez o ato" e do "ICI".
- **Os dois discordam entre si**, e nenhum arbitra. No trecho do Barabási, o `medium` ouviu "Albert" e o `large-v3-turbo` ouviu "Robert". Quem resolveu foi o mundo: o físico das redes é Albert-László Barabási e não existe Robert Barabási na literatura.
- **Os dois confirmam a fala**, e aí sim o áudio serve — para provar que uma correção anterior editou o que foi dito.

**Conclusão:** o áudio prova o que foi dito, não o que é certo. Ele é a fonte de fidelidade, não de correção. E como fonte de fidelidade é insubstituível: foi ele que provou que "S11D, ou SD11" e "KC 360, 370" tinham sido apagados.

## 2.3 Confiar no glossário determinístico

**O que aconteceu.** O glossário de substituição fixa saiu de 111 para 145 termos e resolve muito. Mas ele falha de dois jeitos, e os dois apareceram:

- **Regra estreita demais deixa escapar.** A entrada `ministro Levi → ministro Levy` pegou três das quatro ocorrências de uma aula. A quarta era "ministro, **o** Levi", com vírgula no meio.
- **Regra larga demais estraga.** Não se pode criar `Levi → Levy`, porque Levi é nome de pessoa comum e a regra vale para toda transcrição futura, inclusive de outros assuntos.

**Para a aplicação master:** o glossário precisa de escopo. Uma entrada deveria poder valer só para um domínio, um projeto ou um acervo, em vez de valer sempre. Sem isso, cada termo específico contamina o uso geral, e a alternativa — deixar de fora — perde o acúmulo.

---

# Parte 3 — O processo que funciona

## 3.1 A ordem de consulta

Diante de um nome ou termo duvidoso, procurar nesta ordem e parar quando resolver. A ordem não é preferência, é custo crescente e taxa de acerto decrescente.

**1. O dicionário do domínio.** O que já foi resolvido não se reabre. Barato e imediato.

**2. As outras ocorrências da mesma unidade.** Foi o que resolveu o ECI contra o ICI, porque a aula dizia ECI seis outras vezes. E o que resolveria o "Frederick" que era Rodrik, porque a mesma aula cita "o Rodrik" quatro vezes.

> **A armadilha aqui:** olhar o vizinho imediato em vez do resto da unidade. O "Frederick" nasceu assim — vinte segundos antes havia um "Friedrich List", no mesmo assunto, e a correção anterior foi contaminada por ele.

**3. O material que acompanha o áudio.** Anexo, slide, ementa, bibliografia. **Este passo vem antes da internet.** Num caso, o falante cita "o Steingart" e os dois modelos ouvem igual; o anexo daquela mesma aula traz `Schteingart, D. (2014)` com a referência completa. Em outro, uma lista de leitura em imagem confirmou três livros que ele cita de viva voz, com subtítulo e tudo.

**4. Busca externa.** Só então. É aqui que se confirma grafia canônica, autoria e data.

**5. O áudio.** Por último, e só para questões de fidelidade.

**Medição desta ordem, no acervo:** das 34 descobertas distintas do segundo dia, 12 vieram do dicionário, 11 do contexto da própria unidade, 15 de busca externa e 6 eram só forma. A proporção que muda ao longo do tempo é a da busca externa, que cai conforme o dicionário cresce.

## 3.2 A transferência é o ganho real

O efeito mais forte do dicionário não aparece na unidade em que ele é usado, e sim nas seguintes:

- Uma busca para confirmar `Antonio Serra` corrigiu três ocorrências na aula 5 e **quatro na aula 40, que ainda não tinha sido aberta**.
- Uma busca por `jerico` corrigiu uma ocorrência na aula em curso e mais duas em outras duas aulas.
- Uma pesquisa sobre `XGini` corrigiu 24 ocorrências em três aulas de uma vez.

**Para a aplicação master:** toda correção validada deveria ser oferecida como varredura no acervo inteiro, não aplicada apenas onde foi descoberta. E o relatório deveria dizer quantas unidades foram afetadas, porque é isso que mostra o valor do trabalho de validação.

## 3.3 O que medir para saber se está funcionando

A métrica intuitiva — "quantos termos o glossário tem" — engana, porque cresce com erro repetido. Duas contagens separadas resolvem:

- **Ocorrências:** quanto trabalho a unidade deu.
- **Tipos:** quantos problemas distintos apareceram. Nove correções de acentuação da mesma palavra são uma descoberta, não nove.

E a curva que importa não é a do glossário subindo, é a da **busca externa caindo**. A primeira sobe por artefato; a segunda só cai se o acúmulo estiver realmente funcionando.

---

# Parte 4 — Os erros do corretor

Esta é a parte mais importante do documento, e a que não existia antes de 02/09. **O corretor introduz erros de uma natureza pior que os do motor**, porque produz texto plausível, apagando o rastro do que estava lá.

## 4.1 Corrigir construção falada como se fosse erro

**O caso.** O áudio diz "aqui a gente está falando de **Serra Leoa da vida**, Namíbia, o Brasil, o próprio Chile". A correção trocou por "Serra Leoa, **Bolívia**", inventando um país que ninguém disse.

"X da vida" é construção de categoria em português falado: significa "países como Serra Leoa". Quem corrigiu leu como se fosse texto escrito, achou "da vida" estranho ali, e substituiu por algo que parecia mais provável numa lista de países.

**Quem pegou foi o dono do material**, lendo o relatório de correções.

**Construções da mesma família que sobreviveram no mesmo acervo**, e que qualquer corretor automático estragaria: "é um trabalho do cão", "sem pé nem cabeça", "em frangalhos", "mal e mal", "tem um quê de similaridade", "vide o desmonte dos bancos", "fazer as vezes de".

**Regra que ficou:** antes de corrigir qualquer coisa, perguntar se aquilo é português falado que não reconheci. Fala tem repetição, hesitação, concordância relaxada e expressão idiomática, e nada disso é erro.

## 4.2 Apagar fala em nome da clareza

Três casos, todos descobertos pela cicatriz que deixaram:

- O falante diz "a Vale fez esse projeto **S11D, ou SD11**", hesitando. A correção apagou o "ou SD11".
- O falante diz "é o **KC 360, 370**, uma coisa assim", e emenda sozinho admitindo a incerteza. A correção trocou por "KC-390" e apagou os dois números.
- O falante repete "o Estado, nessa visão do Hausmann e do Rodrik, **o Estado** tem uma visão chave". A correção removeu a repetição e trocou "visão" por "papel".

Nos três a intenção era boa e o resultado é o mesmo: o texto deixou de ser o que foi dito.

**Regra que ficou:** hesitação e repetição são fala e ficam. Se o dado está errado, isso vira **nota ao lado**, não edição. O texto diz "S11D, ou SD11" e a nota explica que o projeto é o S11D e que SD11 não existe.

## 4.3 Corrigir olhando o vizinho em vez do conjunto

**O caso.** O áudio diz "está muito bem explorado nesse paper do **Roderick**", que é Dani Rodrik. A correção escreveu "Frederick", quase certamente puxada pelo "Friedrich List" que aparece vinte segundos antes, no mesmo assunto de chutar a escada.

A mesma aula cita "o Rodrik" outras quatro vezes. O desempate estava dentro dela.

**Regra que ficou:** ao corrigir nome, conferir contra as outras ocorrências da mesma unidade, nunca contra o que está por perto. Proximidade textual é fonte de contaminação, não de evidência.

## 4.4 Inventar precisão que a fonte não tem

**O caso.** A transcrição trazia "Robert Barabási". Quem corrigiu escreveu "Albert-**László** Barabási", acrescentando um nome do meio que não está no áudio.

O nome real é esse, e ainda assim a correção está errada: ela põe na boca do falante uma precisão que ele não teve.

**O mesmo erro, em outra camada.** Ao documentar o dicionário, escrevi que Sea-Doo e Ski-Doo "são da Bombardier". A aula não diz isso — o falante diz apenas "marca canadense". E a afirmação é imprecisa: a divisão foi vendida em 2003 e virou a BRP. O dono do material perguntou, e a entrada foi corrigida.

**Regra que ficou:** transcrever o que foi dito, com a grafia canônica do que foi dito. E, no dicionário, só escrever o que a fonte consultada efetivamente diz. Quando a fonte não nomeia algo, registrar que ela não nomeia, em vez de preencher a lacuna.

> Este é o erro mais insidioso do conjunto, porque contamina o dicionário — que é justamente o que orienta as correções seguintes. Erro no texto morre no lugar; erro no dicionário se propaga.

## 4.5 Aplicar correção pela metade

Dois casos:

- "Fazendo São Paulo **as vezes** de Nova Iorque (...) e a cidade de São Paulo, **às vezes**, da cidade de Nova Iorque". A expressão é "fazer as vezes de" nas duas. Corrigiram a primeira e esqueceram a segunda.
- "é **a** aparelho de raio-x". A palavra foi corrigida de "parede" para "aparelho" e o artigo ficou para trás.

**Sinal de detecção:** artigo que não concorda com o substantivo é quase sempre rastro de correção incompleta. Vale uma varredura automática.

---

# Parte 5 — A cicatriz como instrumento de auditoria

**A descoberta mais útil do período, e ela é acidental.**

O método de substituição usado na primeira rodada trocava uma expressão de N palavras por outra de N−1 e **deixava o espaço para trás**. Isso produz duas assinaturas detectáveis por regex:

- espaço duplo no meio de uma frase
- espaço antes de pontuação

Foram **19 ocorrências no acervo**. Cada uma aponta o ponto exato onde alguém mexeu, sem precisar de backup nem de log.

O que se achou: 16 eram cosméticas, com a palavra certa e o espaço sobrando — `com um` para `como`, `fome gerado` para `famigerado`, `plano de emprego` para `pleno emprego`, `A, E ou D` para `WIOD`, `um classified` para `unclassified`. E **3 tinham apagado fala**, que são os casos da seção 4.2.

**Por que isso importa tanto:** não havia backup das transcrições antes da primeira correção, nem log das regras aplicadas. A cicatriz foi a única forma de auditar o que tinha sido feito.

**Para a aplicação master, três requisitos que nascem daqui:**

1. **Toda correção em lote grava um log estruturado** — regra aplicada, arquivo, posição, texto antes e depois. Isso torna a auditoria trivial e a cicatriz desnecessária.
2. **Backup antes, diff depois.** Já estava no `PADROES-DE-ERRO.md` como regra 3 e não foi seguido na prática.
3. **Enquanto o log não existir, procurar cicatriz é obrigatório.** E mesmo com log, a varredura por espaço órfão é um teste barato de integridade.

## 5.1 Contar invariantes

Correção em lote pode degradar estrutura sem mudar uma palavra do texto. Já aconteceu duas vezes:

- Um método de substituição comeu 34 dos 28.311 carimbos de tempo, e ninguém notaria lendo.
- Uma remoção legítima de duas linhas alucinadas mudou a contagem de 28.311 para 28.309, o que é o resultado correto — e só se sabe disso porque a contagem existia.

**Invariantes que valem contar antes e depois:** número de carimbos de tempo, número de marcadores de falante, número de arquivos, e a soma de bytes quando a operação for de movimentação e não de edição.

---

# Parte 6 — O material que acompanha o áudio

Um acervo real não é só áudio. Tem anexo, slide, ementa, bibliografia. **Esse material resolve o que o áudio não resolve**, e foi subutilizado até tarde.

**O caso que estabeleceu a regra.** O falante cita "um trabalho muito interessante de um argentino, que é o **Steingart**". Os dois modelos ouvem igual, o áudio isolado confirma o som, e a busca externa não achava a pessoa. O anexo daquela mesma aula, um resumo escrito pelo próprio autor, trazia: `Schteingart, D. (2014)`, com o método e o período do estudo.

**O que foi construído.** Um índice do texto de todos os anexos, um arquivo por anexo, pesquisável com `grep`. De 195 anexos, 125 renderam texto — os artigos e resumos. Dos 59 restantes, 57 eram gráficos em imagem, sem nome próprio a resolver, e 2 eram listas de leitura em imagem, lidas convertendo a página em PNG, sem precisar de OCR.

**Para a aplicação master:** se o acervo tem material de apoio, indexá-lo é pré-requisito da validação, não um extra. E o índice precisa dizer o que ficou de fora e por quê, senão parece lacuna.

---

# Parte 7 — Erro do falante não é erro de transcrição

Regra que já existia e se confirmou com volume. **A transcrição é fiel ao que foi dito; o que estiver errado ganha nota, não correção.**

Casos reais do acervo, todos preservados com nota ao lado:

- Diz que um autor ganhou o Nobel "junto com Oliver Williamson e Ronald Coase". Ele dividiu com Robert Fogel; Coase ganhou em 1991 e Williamson em 2009.
- Chama um economista de "professor de UCLA". Ele é de Berkeley desde 1987.
- Ao explicar o Bacon Number, que liga **atores** por filmes em comum, diz "autor" três vezes seguidas.
- Traduz *sesame seeds* por "alpiste". É gergelim; alpiste é *canary seed*.
- Diz que um livro foi traduzido "com o título Conectado". A edição brasileira manteve o título original.
- Data o artigo de um autor "no início dos anos 20" numa aula e "no início dos anos 1900" em outra. É de 1928, e as duas afirmações se contradizem.

**Como distinguir erro do falante de erro do motor:** isolar o trecho e rodar os modelos. Se os dois ouvem a mesma coisa e ela é plausível como fala, é do falante. Foi assim que se decidiu o caso do "autor" no Bacon Number.

**Para a aplicação master:** a nota precisa ser um recurso de primeira classe — marcação no corpo, aviso no cabeçalho do arquivo, e um índice de todas as notas do acervo. Hoje isso é manual.

---

# Parte 8 — Alucinação do motor

Duas aulas terminavam com "Legenda por Sônia Ruberti". **Não é fala.** O Whisper foi treinado com legendas de vídeo e reproduz crédito de legendador em trechos de silêncio, tipicamente no fim do áudio.

Confirmado ouvindo o final das duas, que terminam em "Obrigado". Os dois modelos produzem a frase, porque o viés é do treino e não do áudio.

**Para a aplicação master:** manter uma lista de padrões de alucinação conhecidos — créditos de legendagem, "inscreva-se no canal", "obrigado por assistir", nomes de plataformas de legenda — e sinalizar quando aparecerem perto do fim do arquivo ou em trecho de silêncio. Nunca apagar automaticamente: sinalizar.

---

# Parte 9 — O dicionário como artefato

O que funcionou, depois de uma reescrita.

**Organizado por uso, não por tipo de informação.** A primeira versão agrupava por categoria — pessoas, obras, instituições. A versão útil agrupa pelo momento em que se consulta:

1. **Formas corretas e as deformações já vistas.** É a única seção lida a cada unidade. Duas colunas: a forma certa e o que procurar no texto.
2. **Decidido, não reabrir.** Questões já resolvidas, com a decisão e o motivo. Impede reabrir a mesma dúvida na décima aula.
3. **Erros do falante.** Para não "corrigir" o que é fiel.
4. **Registro por unidade.** O que foi corrigido em cada uma e por quê.
5. **Quem é quem, com a fonte.** Consulta rara, e é o que permite auditar as afirmações das seções anteriores.

**A divisão entre o documento e o automatismo.** O `.md` guarda o porquê, com fonte e caso; o `glossario.json` guarda a substituição determinística. Um termo entra no JSON só quando a correção é sempre a mesma, independentemente do assunto do áudio.

**Um subproduto que se mostrou valioso.** Uma lista de quem é quem no acervo, com o tema pelo qual cada pessoa é citada e as unidades onde aparece. Ela não serve à correção, serve à navegação: permite localizar rapidamente onde procurar quando surge uma dúvida específica, e revelou coisas que não se veem ouvindo aula por aula — como um autor citado 63 vezes em doze aulas diferentes.

---

# Parte 10 — Captura, quando ela faz parte do problema

O acervo veio de uma plataforma com vídeo protegido, e três aulas resistiram por três dias. A conclusão registrada na época — "restrito no lado do provedor" — estava errada, e havia **duas causas distintas com respostas opostas**:

**Limite temporário do serviço antibot.** Disparado por tentativas seguidas. Passa sozinho em um dia. Duas das três aulas abriram sem que nada mudasse no método.

**Detecção de automação.** Não passa com tempo nem com recarga. Resistiu a cinco tentativas com aquecimento. A saída foi usar o navegador do sistema em vez do que a biblioteca de automação instala, com perfil próprio e porta de depuração separada, e conectar a captura nessa porta.

**Para a aplicação master:** distinguir as duas causas na mensagem de erro, porque a resposta é oposta — esperar num caso, trocar de navegador no outro. E registrar que a mesma mensagem serve às duas.

---

# Parte 11 — Requisitos derivados, para a aplicação master

Consolidando o que apareceu ao longo do documento. Cada item nasceu de um caso concreto, não de especulação.

## Correção e auditoria

- [ ] **Log estruturado de toda correção em lote:** regra, arquivo, posição, antes e depois. Elimina a necessidade de procurar cicatriz. *(Parte 5)*
- [ ] **Contagem automática de invariantes** antes e depois de qualquer operação em lote: carimbos, marcadores de falante, arquivos, bytes. *(Parte 5.1)*
- [ ] **Backup automático antes de correção em lote**, com diff palavra a palavra disponível depois. *(Parte 5)*
- [ ] **Varredura de cicatriz** por espaço duplo e espaço antes de pontuação, como teste de integridade barato. *(Parte 5)*
- [ ] **Detecção de correção pela metade:** artigo que não concorda com o substantivo. *(Parte 4.5)*

## Glossário e dicionário

- [ ] **Escopo por entrada no glossário:** global, por domínio, por projeto ou por acervo. Sem isso, termo específico contamina o uso geral. *(Parte 2.3)*
- [ ] **Aviso quando uma regra pegar parcialmente:** se `ministro Levi` casou três vezes e existem outras ocorrências de `Levi` no mesmo arquivo, apontar. *(Parte 2.3)*
- [ ] **Varredura no acervo inteiro a cada correção validada**, com relatório de quantas unidades foram afetadas. *(Parte 3.2)*
- [ ] **Campo de fonte obrigatório** em entrada de dicionário que afirme algo sobre o mundo. *(Parte 4.4)*

## Validação assistida

- [ ] **Relatório de nomes próprios candidatos:** capitalizadas ordenadas por frequência, com as de cauda ao lado das formas parecidas mais frequentes. *(já no BACKLOG desde 01/09)*
- [ ] **Aviso de inversão de sentido:** buscar "mais igual", "simplificação produtiva" e afins, e listar para conferência em contexto. Não corrigir. *(já no BACKLOG desde 01/09)*
- [ ] **Checagem de consistência interna:** sigla que aparece de duas formas no mesmo arquivo, nome próprio grafado de dois jeitos. Foi assim que se acharia o ECI/ICI e o Eric/Erik Reinert. *(Parte 3.1)*
- [ ] **Índice do material de apoio** como parte do fluxo, não como extra, com relatório do que ficou de fora. *(Parte 6)*
- [ ] **Nota de verificação como recurso de primeira classe:** marcação no corpo, aviso no cabeçalho, índice de todas as notas do acervo. *(Parte 7)*
- [ ] **Lista de padrões de alucinação conhecidos**, sinalizados e nunca apagados automaticamente. *(Parte 8)*

## Métrica

- [ ] **Contar ocorrências e tipos separadamente.** *(Parte 3.3)*
- [ ] **Acompanhar a curva da busca externa caindo**, não a do glossário subindo. *(Parte 3.3)*

## Captura

- [ ] **Distinguir limite temporário de detecção de automação** na mensagem de erro, com resposta diferente para cada. *(Parte 10)*

---

# Parte 12 — O que continua sem solução

Honestidade sobre os limites, para não desenhar em cima de premissa falsa.

**Não há como auditar correção sem rastro.** Se não houve backup nem log, e a segunda passada coincidiu com o texto corrigido, aquele ponto é invisível. Foi o caso de uma faixa desconhecida do acervo, e a única mitigação foi ler tudo.

**O julgamento de "é fala ou é erro" não automatiza.** A distinção entre "Serra Leoa da vida" e um erro de transcrição exige conhecer português falado e o assunto. Um sistema pode sinalizar candidatos; decidir é humano ou de um modelo com contexto do domínio.

**A validação contra o mundo não escala sem custo.** Cada nome novo é uma busca. O dicionário reduz o número de buscas ao longo do tempo, mas a primeira ocorrência de qualquer coisa custa o mesmo sempre.

**Diarização de conteúdo com um falante só é diferente de reunião.** Todo este acervo foi processado com `--speakers 1`, o que é correto para aula gravada e errado para reunião. A aula de pós-graduação que entrou no meio tinha oito falantes e foi capturada por outra ferramenta, que entregou os nomes — e nomear falante corretamente é um problema à parte, não coberto aqui.

---

*Escrito em 03/09/2026, a partir do trabalho sobre um acervo de 50 aulas em três rodadas de correção. Complementa o `PADROES-DE-ERRO.md`, que trata dos erros do motor; este trata do processo de validação e dos erros de quem corrige.*
