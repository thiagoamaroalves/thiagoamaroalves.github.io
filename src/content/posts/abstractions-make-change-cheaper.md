---
title: "A Good Abstraction Makes the Next Change Cheaper"
description: "An abstraction is useful when it hides decisions callers should not need to understand and keeps a change from spreading through the system."
pubDate: 2026-11-12
category: Programming
tags:
  - abstractions
  - modularity
  - code design
readingTime: 6 min read
featured: false
---

Abstractions are meant to simplify. In practice, they can do the opposite: add interfaces, wrappers, factories, and configuration while leaving callers just as aware of the underlying complexity as before.

The difference is not how many layers exist. It is whether a caller can complete a useful task without learning decisions that belong somewhere else.

## Hide decisions, not just data

Imagine an application that needs to send a receipt. The calling code should usually express the intent: send this receipt to this customer. It should not need to know how a provider formats requests, rotates credentials, retries transient failures, or records delivery metadata.

An interface can make that boundary clear:

```ts
interface ReceiptSender {
  send(receipt: Receipt, recipient: EmailAddress): Promise<DeliveryResult>;
}
```

The interface is only valuable if it represents a stable need of the caller. If it mirrors every method of a specific vendor SDK, the vendor's model has leaked through the abstraction. Replacing the implementation may still force changes everywhere.

## Make the useful path obvious

A strong module provides a small, complete operation. Callers should not have to assemble low level steps in precisely the right order or manage internal state that the module could own.

That often means moving complexity behind a narrow contract. A reporting module might accept a time range and return a report, rather than exposing each query, join, and formatting step to every caller. The implementation may be complex; the task presented to its users should be clear.

This is also why very small wrappers can disappoint. A wrapper that renames a function but exposes the same choices and failure modes has not reduced the caller's mental model. It has relocated a few lines.

## Let a change reveal the seam

One way to evaluate an abstraction is to trace a plausible change. If the storage format changes, which files should move? If a policy changes, which tests should fail? If callers need a new behavior, can the module offer it without exposing its internals?

The answers do not need to be perfect predictions. They make the abstraction's promise concrete. When a routine change crosses many modules, either the boundary is misplaced or the behavior is not truly independent. Both are useful discoveries.

## Keep the cost visible

Every abstraction has costs: another name to learn, another place to look, and sometimes another layer to debug. It should repay those costs by reducing coupling or making a common operation clearer.

Start with the simplest code that explains the current problem. Extract a reusable boundary when repeated behavior or an expected change gives it a clear purpose. Then judge it by the next change: did the abstraction keep the decision contained, or did it only add a new place for the same complexity to live?
