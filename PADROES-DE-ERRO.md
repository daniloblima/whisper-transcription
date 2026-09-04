# Padrões de erro do Whisper, observados no uso

Documento vivo. Cada entrada é um padrão que apareceu em volume suficiente para valer regra, e não um caso isolado. Serve de insumo para o `glossario.json`, para a skill `/arrumar-transcricao` e para o `transcribe_complete.py`.

Criado em 01/09/2026, a partir da correção de 47 aulas de um curso de economia (200 mil palavras, 673 correções). É a primeira base grande o suficiente para separar padrão de acaso.

---

## TL;DR

Nove padrões. Os três primeiros invertem o sentido da frase e são os únicos perigosos de verdade. O resto é grafia, e o glossário resolve.

O padrão 7 não é do Whisper, é de método, e foi o erro mais caro da sessão.

---

## 1. Ele come o prefixo "des" e inverte a frase

Apareceu quatro vezes em "desigual", virando "igual". O texto passou a dizer que a África e a América Latina são "os continentes mais iguais do mundo", quando o parágrafo inteiro argumentava o contrário.

**Por que é perigoso:** a frase continua gramatical e plausível. Quem lê rápido absorve o inverso do que foi dito.

**Como pegar:** buscar "mais igual", "mais iguais", "menos desigual" e ler o parágrafo em volta. Não dá para corrigir sem contexto, porque "mais igual" é legítimo em outros usos.

## 2. Ele troca "sofisticação" por "simplificação"

Duas vezes, em "upgrade industrial ou simplificação produtiva" e "complexidade e simplificação". As duas invertem a tese do curso.

**Como pegar:** as duas palavras são comuns e opostas no contexto de desenvolvimento econômico. Vale checar toda ocorrência de "simplificação" perto de "produtiva", "industrial" ou "complexidade".

## 3. Ele cola "%" depois de ano

"em 82%" onde se lê "em 82". Aparece em texto que mistura anos e percentuais de verdade, o que torna a correção automática arriscada.

**Decisão tomada:** não corrigir por script. Registrar e deixar para a leitura humana.

## 4. Ele deforma nome próprio estrangeiro de forma consistente

E é justamente por ser consistente que o glossário resolve. Exemplos medidos: Roderick para Rodrik, Barabase para Barabási, Caldor para Kaldor, Klugmann e Kuhlman para Krugman, Balmol para Baumol, Amesden e Armstrong para Amsden, Girdrie para Deirdre.

**Como pegar:** extrair as palavras capitalizadas do texto e ordenar por frequência. Nome deformado aparece na cauda, com duas ou três ocorrências, ao lado da forma correta.

## 5. Ele quebra sobrenome em duas palavras

"Iken Green" para Eichengreen, "Tom Bini" e "Tom Beany" para Tombini, "massa e fergos" para Massey Ferguson, "Volst, Alpine" para Voestalpine.

**Consequência prática:** a busca por sobrenome não acha. Só o contexto denuncia.

## 6. Ele erra sigla trocando ou comendo letra

SITC virou STC, WIOD virou YIOD e IOD e até "A, E ou D", GGDC virou GDDC, MITI virou MIT, OMC virou M100, URV virou ORV e URB.

**Cuidado:** MIT e MITI coexistem no mesmo texto e significam coisas diferentes. Sigla curta só se corrige com a expressão inteira em volta, nunca isolada.

## 7. Correção de várias palavras come o carimbo de tempo

**Este é de método, não do Whisper, e foi o erro mais caro da sessão.**

Ao trocar uma expressão de duas ou mais palavras, o padrão de busca precisa atravessar o que existe entre elas, que é quebra de linha e carimbo de tempo. Se a substituição escrever só o texto novo, o carimbo desaparece junto. Foram 34 carimbos perdidos em 16 arquivos antes de alguém notar.

**A correção:** capturar os separadores como grupos e recolocá-los entre as palavras novas. Quando origem e destino têm número diferente de palavras, os separadores que sobram vão para o fim.

**A lição maior:** depois de qualquer correção em lote, contar o que deveria ser invariante — carimbos de tempo, marcadores de falante, número de arquivos — e comparar com o backup. A degradação estrutural não aparece na leitura do texto.

## 8. Erro do palestrante não é erro de transcrição

Sete passagens do curso traziam afirmação incorreta do próprio palestrante: Cortés no lugar de Pizarro, Eichengreen na UCLA em vez de Berkeley, Maersk como sueca. A transcrição estava fiel.

**A política adotada, por decisão de Danilo:** não corrigir o texto. Inserir uma `NOTA DE VERIFICAÇÃO` no ponto exato, com o fato correto, e um aviso no cabeçalho do arquivo para quem abrir saber de saída que há afirmação incorreta ali dentro.

## 9. Não completar o nome que o falante encurtou

O texto trazia "Robert Barabási" e foi corrigido para "Albert-László Barabási". O nome dele é esse, mas em duas outras passagens o palestrante diz "Albert Barabási", e a correção introduziu um nome do meio que não estava no áudio, além de deixar as três menções inconsistentes.

**A regra:** corrigir o que está errado, na forma que o falante usa. Se ele diz o nome curto, o nome curto fica.

**O caso vizinho, que ficou registrado sem decisão automática:** quando o primeiro nome está errado e pode ter sido erro do palestrante, e não da máquina, a troca deixa de ser fiel ao áudio. Foram sete casos, listados no `00 A RESOLVER na revisão.md` do curso, para o dono do material decidir.

---

## O que virou regra operacional

1. **Três camadas, nesta ordem.** Glossário determinístico, leitura de contexto, e registro do que sobrou para o humano decidir.
2. **A terceira camada é entregável.** Lista com aula e instante de cada dúvida, para ouvir o trecho. Sem isso o resto vira caixa-preta.
3. **Backup antes, diff depois.** O diff palavra a palavra contra o backup é o único jeito de auditar correção em lote.
4. **Contar invariantes.** Ver a regra 7.
