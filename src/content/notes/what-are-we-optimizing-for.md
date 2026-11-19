---
title: "What are we optimizing for?"
description: "A Shopify case about MySQL and Redis raises questions about popularity, novelty, and operational complexity in architecture choices."
pubDate: 2026-11-19
language: en
category: Architecture
tags:
  - architecture
  - databases
  - trade-offs
  - operational-complexity
readingTime: "2 min read"
translationKey: what-are-we-optimizing
---

Reading Shopify's account of moving inventory reservations from Redis to MySQL made me happy and a little surprised. The team needed to keep checkout inventory consistent and handle peak traffic. After redesigning the reservation flow, it hit its throughput goals on MySQL.

Moving reservations into the same MySQL database as the inventory ledger made operations simpler by removing the separate Redis cluster and allowed ACID transactions across both steps. The team redesigned the reservation flow around SKIP LOCKED. When throughput fell short of the target, they traced connection usage and found other checkout processes holding connections too long. Checkout cleanup and a MySQL configuration change removed that ceiling. [Shopify's account of the migration and investigation](https://shopify.engineering/scaling-inventory-reservations).

Redis remains an excellent choice for problems it fits. Widespread use brings a practical advantage: more people know how to run a technology, which makes staffing projects easier. Those people carry their experience into new work, helping the technology spread further. Some teams choose a technology because it is new or looks modern. That motive is separate from following what other teams use.

<figure>
  <img src="/images/what-are-we-optimizing/architecture-choice.svg" alt="Flow from a business problem through an explicit objective and trade-off review to an architecture choice. Popularity and novelty influence which options are considered." width="1200" height="700" loading="lazy" />
  <figcaption>A popular tool can make hiring easier, while a new tool can attract attention. The stated objective guides the comparison.</figcaption>
</figure>

I prefer to start with the business problem and the outcome we want. From there, a team can compare how well each technology meets the need and how much effort it takes to operate. Some teams also give more weight to operating cost or the availability of skilled people. Those are valid priorities. A well-designed solution can be simpler to operate and serve the business better.
