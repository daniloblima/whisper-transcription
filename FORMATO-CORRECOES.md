# Formato da declaração de correções

Toda correção de transcrição passa pelo `aplicar_correcoes.py`, que lê um JSON como este. Vale para script e para sessão de Claude, sem exceção — o motivo está no `LICOES-APRENDIDAS.md`, parte 4: os cinco erros do corretor foram cometidos editando o arquivo direto.

## Exemplo

```json
{
  "descricao": "Conferência da aula 01-2 contra fonte externa",
  "base": "/caminho/da/pasta/com/as/transcricoes",
  "alvos": ["*.md"],
  "correcoes": [
    {
      "de": "fez o ato",
      "para": "fez o Atlas",
      "ocorrencias": 1,
      "motivo": "Hausmann e Hidalgo são coautores do Atlas of Economic Complexity, citado na mesma aula",
      "origem": "externa"
    },
    {
      "de": "do ICI",
      "para": "do ECI",
      "ocorrencias": 1,
      "motivo": "as outras seis ocorrências da mesma aula dizem ECI",
      "origem": "contexto",
      "arquivos": ["01-3 Complexidade e sofisticação produtiva.md"]
    }
  ]
}
```

## Campos do topo

| Campo | Obrigatório | O que é |
|---|---|---|
| `descricao` | não | uma linha sobre a corrida, que vai para o relatório |
| `base` | não | pasta onde procurar os alvos. Padrão: a pasta do próprio JSON |
| `alvos` | sim | lista de caminhos ou globs relativos a `base` |
| `correcoes` | sim | a lista de trocas |

## Campos de cada correção

| Campo | Obrigatório | O que é |
|---|---|---|
| `de` | sim | o texto como está na transcrição |
| `para` | sim | o texto corrigido |
| `ocorrencias` | sim | quantas vezes você espera que `de` apareça no conjunto |
| `motivo` | sim | por que esta correção está certa. Vai para o relatório e não pode ser vazio |
| `origem` | sim | de onde veio a resposta: `dicionario`, `contexto`, `anexo`, `externa`, `forma`, `glossario` ou `usuario` |
| `arquivos` | não | restringe a troca a estes arquivos, pelo nome |
| `exato` | não | `true` (padrão) exige caixa idêntica. `false` casa em qualquer capitalização |
| `tipo` | não | `troca` (padrão) ou `remocao` |
| `confirmado_por` | só em remoção | quem decidiu apagar |

## As cinco travas

**Contagem declarada.** Você diz quantas ocorrências espera. Se a realidade não bater, a corrida inteira é recusada e nada é escrito. Casou menos significa regra estreita demais, como o `ministro Levi` que não alcançava `ministro, o Levi,`. Casou mais significa regra larga demais, como o `Levi` solto que pegaria qualquer Levi.

**Apagar fala exige declaração.** Se `para` tem menos palavras que `de`, a troca apaga fala e é recusada, a menos que traga `"tipo": "remocao"` com `confirmado_por`. Foi assim que `S11D, ou SD11` virou `S11D` em 01/09, e a hesitação do falante desapareceu. Hesitação e repetição são fala e ficam; se o dado está errado, isso é nota ao lado, não edição.

**Separadores preservados.** Quando a expressão tem mais de uma palavra, o que estiver entre elas — quebra de linha, carimbo de tempo, marcador de falante — é capturado e recolocado. No acervo do curso há 14.662 pontos em que duas palavras vizinhas estão separadas por um carimbo, então isso não é caso raro. Separador que sobra só permanece se carregar carimbo ou marcador; se for espaço em branco, é descartado, senão vira a cicatriz que o módulo existe para impedir.

**Invariantes conferidos.** Carimbos de tempo e marcadores de falante são contados antes e depois — tanto o `**FALANTE**` das transcrições do projeto quanto o `Nome:` abrindo linha, que é como exportam as ferramentas de notas de reunião. Se algum sumir, a corrida aborta e o arquivo não é tocado. Foi assim que se perderam 34 carimbos em 16 arquivos sem ninguém notar, porque o texto continuava perfeito.

Sobre isso corre a contagem de palavras, que é o invariante que vale em qualquer formato: cada troca sabe quantas palavras tira e põe, então o total depois tem que bater com o previsto. Ela existe porque as outras três dependem de estrutura que nem todo arquivo tem, e num lote de 08/09/2026 a trava rodou sobre 23 arquivos sem carimbo nem marcador, contou zero e zero, e informou que nada se perdera. Quando não houver estrutura nenhuma, o aplicador diz isso em voz alta em vez de dar conforto.

**Contexto de cada troca no relatório.** O log mostra o texto em volta de cada ocorrência, porque a contagem declarada protege contra pegar demais ou de menos e não mostra o que vai ser trocado. Rodar com `--dry-run` e ler as ocorrências é o passo que separa correção de estrago numa troca de nome próprio.

**Backup e log.** Antes de escrever, o original vai para `_correcoes/<data-hora>/<nome>.bak.md`. Depois, o mesmo diretório recebe `log.json` e `correcoes.md`, com regra, arquivo, linha, carimbo mais próximo, texto antes e depois, motivo e origem de cada troca.

## Uso

```bash
python3 aplicar_correcoes.py correcoes.json --dry-run   # mostra sem escrever
python3 aplicar_correcoes.py correcoes.json             # aplica
```

O `--dry-run` roda todas as travas e escreve o relatório, sem tocar nas transcrições. É o modo de conferir a contagem antes de aplicar.
