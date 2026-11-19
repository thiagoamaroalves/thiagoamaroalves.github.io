---
title: "O que estamos otimizando?"
description: "Um caso da Shopify sobre MySQL e Redis levanta perguntas sobre popularidade, novidade e complexidade operacional nas escolhas de arquitetura."
pubDate: 2026-11-19
language: pt
category: Architecture
tags:
  - arquitetura
  - bancos-de-dados
  - trade-offs
  - complexidade-operacional
readingTime: "2 min de leitura"
translationKey: what-are-we-optimizing
---

Ler o relato da Shopify sobre mover as reservas de estoque do Redis para o MySQL me deixou feliz e um pouco surpreso. A equipe precisava manter a consistência do estoque durante o checkout e atender aos picos de tráfego. Depois de redesenhar o fluxo de reservas, conseguiu processar o volume esperado com MySQL.

Colocar as reservas no mesmo banco MySQL do registro principal do estoque reduziu a complexidade de manter um cluster Redis separado e permitiu transações ACID entre as duas etapas. A equipe redesenhou o fluxo de reservas em torno de SKIP LOCKED. Quando a taxa de reservas ficou abaixo da meta, o rastreamento das conexões mostrou que outros processos do checkout as mantinham ocupadas por tempo demais. A limpeza no código do checkout e um ajuste na configuração do MySQL removeram esse limite. [A Shopify conta como chegou à solução](https://shopify.engineering/scaling-inventory-reservations).

O Redis continua sendo uma ótima escolha para os problemas que resolve bem. A adoção ampla também traz uma vantagem prática. Quanto mais equipes usam uma tecnologia, mais profissionais aprendem a operá-la. Quando mudam de projeto, podem voltar a escolhê-la, reforçando ainda mais sua adoção. Há ainda outro impulso: algumas equipes escolhem uma tecnologia por ser nova ou parecer moderna.

<figure>
  <img src="/images/what-are-we-optimizing/pt/architecture-choice.svg" alt="Fluxo que parte de um problema de negócio, passa por um objetivo explícito e pela avaliação de trade-offs até chegar à escolha de arquitetura. Popularidade e novidade influenciam as opções consideradas." width="1200" height="700" loading="lazy" />
  <figcaption>Uma tecnologia popular pode facilitar a contratação de profissionais; uma nova pode chamar atenção. O objetivo declarado orienta a comparação.</figcaption>
</figure>

Eu prefiro começar pelo problema do negócio e pelo resultado esperado. Depois, dá para comparar as tecnologias pelo quanto atendem a essa necessidade e pelo esforço necessário para operá-las. Algumas equipes também dão mais peso ao custo e à disponibilidade de profissionais. São prioridades válidas. Uma solução bem pensada pode ser mais simples de operar e atender melhor ao negócio.
