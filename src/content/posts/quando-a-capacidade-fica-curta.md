---
title: "Quando a capacidade fica curta: protegendo jornadas essenciais"
description: "Uma proposta para preservar o checkout ao reduzir trabalho de menor prioridade sob pressão."
pubDate: 2026-11-18
language: pt
category: Architecture
tags:
  - alta-disponibilidade
  - load-shedding
  - resiliência
readingTime: "10 min de leitura"
featured: true
translationKey: priority-aware-load-shedding
---

Uma pessoa que já chegou ao checkout precisa conseguir pagar e saber se o pedido foi confirmado. Durante um pico de tráfego, eu pausaria as recomendações personalizadas antes de deixar o checkout se arrastar. Essa é a troca que esta proposta faz.

Alta disponibilidade não significa manter todas as funcionalidades disponíveis o tempo todo. Significa proteger as jornadas essenciais quando a capacidade não basta.

Eu mediria a disponibilidade do checkout desde a abertura de um carrinho existente até a confirmação do pagamento. Nesse nível, duas coisas importam: com que frequência as pessoas concluem a compra e quanto tempo levam. A utilização de CPU e o p95 por rota ajudam o serviço a decidir quando agir. O SLO do checkout mede o que a pessoa vivencia ao longo de toda a jornada. O Google SRE explica como escolher indicadores voltados ao usuário e identificar jornadas críticas no capítulo sobre [SLOs](https://sre.google/sre-book/service-level-objectives/) e no [SRE Workbook](https://sre.google/workbook/implementing-slos/).

## Dê a cada requisição a prioridade da jornada que ela atende

Nesta loja, o trabalho Essencial inclui buscar o carrinho existente durante o checkout, verificar preço e estoque, criar o pedido, autorizar o pagamento e confirmar o resultado. Navegar pelo catálogo e alterar o carrinho fora do checkout são atividades Padrão. Recomendações personalizadas são Adiáveis. A equipe de produto pode classificar as jornadas considerando o custo de interrompê-las para o cliente e para o negócio.

Um mesmo endpoint pode atender mais de uma jornada. Buscar o carrinho para exibir seu conteúdo durante a navegação pode ter prioridade diferente de buscar o mesmo carrinho para concluir o checkout. Um gateway confiável ou backend for frontend (BFF) pode atribuir a prioridade a partir do contexto da jornada e propagá-la. Cada serviço decide o que admitir com base na própria capacidade. Se a prioridade viajar em um cabeçalho, o componente confiável deve defini-lo. O Google SRE trata criticidade da requisição e requisitos de latência como aspectos distintos. O filtro experimental do Envoy também destaca que o cabeçalho de prioridade precisa vir de uma origem confiável. ([Google SRE](https://sre.google/sre-book/handling-overload/), [filtro do Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/priority_load_shed_filter))

<figure>
  <img src="/images/priority-load-shedding/pt/journey-to-admission.svg" alt="As jornadas de checkout e recomendações recebem prioridades diferentes em um gateway confiável e passam pelo controle de admissão local do serviço." width="1200" height="560" loading="lazy" />
  <figcaption>A prioridade acompanha a jornada do usuário; cada serviço aplica a política com base nos sinais locais de capacidade.</figcaption>
</figure>

## Observe a utilização do serviço e a latência por rota

Meça a utilização em relação à capacidade realmente disponível para o serviço, como os núcleos de CPU ou a cota atribuída a ele. Ao se aproximar desse limite, o serviço pode rejeitar primeiro o trabalho de menor prioridade. Uma rota também pode ficar lenta mesmo com a CPU quase ociosa. O checkout talvez esteja aguardando um banco de dados compartilhado ou uma fila em outro serviço. O p95 por rota ajuda o controlador a detectar essa pressão. [Google SRE](https://sre.google/sre-book/handling-overload/)

Com um histograma clássico do Prometheus, é possível estimar o p95 de cada rota nos últimos cinco minutos:

```text
histogram_quantile(
  0.95,
  sum by (route, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```

Agrupar por rota produz uma estimativa separada para cada uma. O Prometheus interpola os valores entre os intervalos do histograma. [Funções de consulta do Prometheus](https://prometheus.io/docs/prometheus/latest/querying/functions/)

Antes de agir com base no p95, exija pelo menos `N` requisições na janela. Escolha esse mínimo usando tráfego representativo. Nesta proposta, o controlador consulta a janela móvel de cinco minutos a cada minuto e age depois que duas avaliações elegíveis consecutivas ultrapassam o limite de latência da rota. As janelas se sobrepõem. A segunda avaliação verifica se a violação ainda aparece um minuto depois, embora parte das mesmas requisições entre nos dois cálculos.

<figure>
  <img src="/images/priority-load-shedding/pt/p95-evidence-window.svg" alt="Três avaliações de p95 mostram 97 amostras abaixo de N, depois a primeira violação elegível com 217 amostras e a segunda com 354 amostras." width="1200" height="590" loading="lazy" />
  <figcaption>Neste ensaio, o mínimo de amostras adiou a proteção do trabalho Essencial até cerca de três minutos. Como as janelas se sobrepõem, a segunda avaliação confirma a persistência do problema; ela não dobra o número de amostras independentes.</figcaption>
</figure>

## Reduza o trabalho que disputa o recurso limitado

A política de CPU começa limitando o trabalho Adiável quando a utilização chega a 80%. Aos 90%, limita também o trabalho Padrão. O serviço continua admitindo requisições Essenciais enquanto houver capacidade. Os dois limites são parâmetros deste experimento.

A política por rota pode agir mesmo abaixo do limite de CPU. Se o p95 do checkout ultrapassar seu orçamento e as condições de amostragem e tempo forem atendidas, reduza o trabalho de menor prioridade que usa a mesma dependência limitada. Se as recomendações usam outro recurso e o provedor de pagamento está lento, concentre a ação na dependência de pagamento. Se somente uma rota Adiável ultrapassar seu limite, limite essa rota localmente.

<figure>
  <img src="/images/priority-load-shedding/pt/two-pressure-signals.svg" alt="Comparação entre pressão global de CPU com p95 saudável e CPU baixa com violação do p95 em uma rota Essencial." width="1200" height="660" loading="lazy" />
  <figcaption>Os dois gatilhos são independentes. As faixas de CPU e o orçamento de p95 ilustrados são parâmetros deste experimento, não valores recomendados para produção.</figcaption>
</figure>

Quando o serviço rejeita uma requisição de recomendação, a página pode omitir o painel e permitir que a pessoa continue o checkout. Quando uma nova tentativa fizer sentido, limite o número de tentativas e use espera exponencial com jitter. Um circuit breaker pode suspender chamadas a uma dependência com falhas. [AWS Well-Architected: controle e limite as tentativas](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel05-bp03.html)

## O que aconteceu na VM

Alterei o mockup para comparar dois caminhos. No controle, as requisições vão diretamente ao serviço, sem o cabeçalho `X-Request-Priority`; o caminho da rota identifica a carga para as medições, mas a política de admissão trata cada requisição como não classificada. No cenário com gateway, um componente local sobrescreve qualquer prioridade enviada pelo cliente e define o valor antes de encaminhar a requisição. Os testes de p95 usam a mesma semente aleatória e a mesma distribuição entre Essencial, Padrão e Adiável. O gateway usa o caminho como uma aproximação do contexto da jornada; em produção, o classificador precisaria distinguir jornadas diferentes que compartilham um endpoint.

Para testar a pressão de CPU, ofereci 180 requisições por segundo durante 60 segundos em cada execução. Sem classificação, o serviço respondeu às 10.800 requisições, mas apenas 21 das 1.054 respostas Essenciais chegaram dentro do limite de 250 ms; o p95 Essencial foi de 3,47 segundos e a CPU do serviço atingiu 99,91%. Pelo gateway, 1.009 de 1.053 respostas Essenciais (95,82%) ficaram dentro do limite, com p95 de 243,86 ms. Conforme a pressão de CPU aumentou, o serviço rejeitou 514 requisições Padrão e 3.031 Adiáveis. O gerador perdeu uma chegada programada; as respostas 429 foram as rejeições intencionais das rotas de menor prioridade, sem outros erros. Foi uma execução sintética por caminho.

Para testar a pressão de latência, usei uma dependência compartilhada com dois slots que levava 100 ms por chamada. A 23 requisições por segundo durante cinco minutos, a CPU ficou abaixo de 3,4%. Sem o cabeçalho de prioridade, o serviço atingiu o limite de 512 requisições em andamento e rejeitou 40 das 665 tentativas Essenciais; apenas 9 foram concluídas em até 250 ms, e o p95 das respostas Essenciais chegou a 25,74 segundos. O detector de p95 identificou a violação depois de cerca de 120 segundos, mas a política de admissão não conseguia escolher o trabalho de menor prioridade porque as requisições não tinham uma classificação de prioridade.

Pelo gateway, as 665 requisições Essenciais foram atendidas, enquanto 1.308 requisições Padrão e 2.458 Adiáveis foram rejeitadas. O p95 Essencial dos cinco minutos ainda foi de 16,99 segundos, e 345 das 665 respostas (51,88%) ficaram dentro do limite. Essa métrica da execução inteira inclui respostas lentas anteriores à ativação da proteção. Em uma amostra separada de 60 segundos após a ativação, as 144 respostas Essenciais ficaram dentro do limite e o p95 foi de 102,83 ms. O p95 móvel de cinco minutos permaneceu alto porque a janela ainda continha as respostas lentas anteriores. A amostra separada descreve o comportamento depois da ativação; ela não substitui o SLO calculado para a janela inteira.

Na primeira tentativa do cenário p95 com gateway, o timeout da chamada ao serviço era de 30 segundos e gerou dois erros 502 em requisições Padrão. Ajustei esse timeout para os mesmos 90 segundos do gerador e repeti o par; a repetição não teve perdas de cronograma nem outros erros. Esses são experimentos em uma única VM, não medições de produção. [Configuração, resultados e resumos JSON](https://github.com/thiagoamaroalves/thiagoamaroalves.github.io/blob/main/experiments/priority-load-shedding/RESULTS.md#gateway-classification-comparison)

## Reintroduza o tráfego em etapas

A proposta de recuperação espera duas observações saudáveis. Depois de uma redução acionada pela utilização, também aguarda a CPU cair abaixo de 70%. Em seguida, aumenta gradualmente a parcela de tráfego de menor prioridade para 5%, 10%, 25%, 50% e 100%, com duas observações saudáveis em cada etapa. Se o serviço voltar a se degradar, o controlador retorna à última parcela estável.

O mockup espaça as sondagens em `x`, `2x`, `4x` e `8x`. Depois de quatro sondagens malsucedidas, o circuit breaker permite uma pequena sondagem a cada intervalo `y`. Em produção, eu acrescentaria jitter e um limite de tentativas para distribuir as chamadas dos clientes. Timeouts e um circuit breaker podem limitar o tempo e a capacidade gastos ao chamar uma dependência com falhas. O teste na VM cobriu os gatilhos de sobrecarga e as decisões de rejeição. Os limites, intervalos e número de falhas da recuperação ainda precisam ser testados. ([Orientação da AWS sobre tentativas](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel05-bp03.html), [orientação da AWS sobre timeouts](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel05-bp05.html))

## O que eu testaria antes de usar isso no checkout

O laboratório usou uma VM, um serviço em Python, uma dependência simulada e uma execução por configuração. Para afirmar que o checkout está disponível, eu repetiria os testes com tráfego representativo, calibraria os limites de utilização, os orçamentos por rota e o mínimo de amostras, e mediria compras concluídas e latência fim a fim, do carrinho à confirmação do pagamento. Uma análise separada das respostas depois da ativação da proteção mostraria com que rapidez a latência do checkout se recupera.
