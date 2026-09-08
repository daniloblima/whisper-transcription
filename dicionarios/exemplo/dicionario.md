---
tema: exemplo
descricao: modelo de dicionário temático, para copiar ao começar um tema novo
quando_usar: nunca em transcrição de verdade; esta pasta existe só como formato
---

# Dicionário de exemplo

Copie esta pasta com o nome do seu tema, em `dicionarios/<tema>/`, e edite os dois arquivos. O `.md` guarda o porquê de cada decisão, com fonte; o `glossario.json` guarda a substituição automática. Um termo só entra no JSON quando o acerto é sempre o mesmo dentro do tema.

O bloco no topo é lido pela ferramenta para propor este dicionário quando o contexto que você declarar combinar. Escreva `descricao` e `quando_usar` com as palavras que você usaria ao descrever um áudio desse assunto, porque é por elas que o casamento acontece.

As quatro seções abaixo estão na ordem em que se consulta, não por tipo de informação. A ordem saiu do uso: as três primeiras se leem a cada arquivo novo, a quarta quase nunca.

## 1. Formas corretas e como o motor as deforma

A coluna da direita é o que procurar numa transcrição nova.

| Forma correta | Como aparece errado |
|---|---|
| Eichengreen | Iken Green, Aiken Green |
| Pólya | polia, Polia |

## 2. Decidido, não reabrir

O que já foi resolvido, com a decisão e o motivo. Existe para a mesma dúvida não voltar no décimo arquivo.

- **Nome curto que o falante usa fica curto.** Se ele diz "Albert Barabási", não vira "Albert-László Barabási". Completar o nome põe na boca dele uma precisão que não teve.

## 3. Erros do falante, registrados sem correção

A transcrição é fiel ao que foi dito. O que estiver factualmente errado ganha `NOTA DE VERIFICAÇÃO` no ponto, com o fato correto, e um aviso no cabeçalho do arquivo.

| Onde | O que foi dito | O que é |
|---|---|---|
| arquivo, instante | afirmação como saiu | o fato, com a fonte |

## 4. Quem é quem, e a fonte

Consulta rara. Serve para desambiguar homônimo e para auditar o que foi afirmado acima. Campo de fonte obrigatório em qualquer entrada que afirme algo sobre o mundo: entrada de dicionário errada se propaga, porque é ela que orienta as correções seguintes.

| Nome | Quem é | Fonte |
|---|---|---|
| | | |
