# Shared stems are folded into every member Question

18 of the 270 Questions cannot be answered from their own text: they belong to a 題組 whose stem
is written once and referred to by two to four consecutive Questions. Rather than model that
preamble as an entity, the parser **folds** it into every member's `stem_md` as an attributed
blockquote:

```
> **共用題幹（第46～48題）**
> 在郵遞區號自動辨識的研究中，研究人員收集了一份手寫數字影像資料集…

研究人員希望透過資料降噪的方法…
```

The corpus writes the shared stem in two conventions, and both are recognised:

| Convention | Where it sits | Seen in |
|---|---|---|
| `## 第 46～47 題（題組）` heading, prose beneath | between Questions, as a Bank sub-heading | 114年-科3 |
| `> 以下第46~48 題共用題幹：…` blockquote | at the **tail of the previous Question's region** | 115年-科3 |

## Why not a `Stimulus` entity

Because one invariant pays for everything downstream: **a Question is answerable alone.**
Composition shuffles Questions, a Drill selects an arbitrary subset of Starred Questions, and
Lookup lists a Question as a standalone hit. Each of those is a one-liner while the invariant
holds, and each grows a special case the moment a Question can point at content it does not
carry. A `Stimulus` table would have touched the parser, the catalogue, composition, the API,
the exam page and the Drill; folding touches the parser.

The price is real and accepted: the preamble is stored and rendered two to four times, and
editing it changes two to four `qkey`s at once. The second half is why the Slot record in
ADR 0002 exists — the relink is expected to fire here, in bulk, and must be deterministic.

## Consequences

The measured 18 folded Questions and 7 spans are asserted by tests: a corpus where folding
silently stopped matching would otherwise look identical to one with no 題組 in it.

`shared_for` returns the first span covering an ordinal, which is only unambiguous because
spans never overlap inside a file. That is a property of the corpus, not a law, so `check`
reports overlapping spans as a finding rather than resolving them by luck.

Folding runs before `qkey_for`, so a folded Question's identity covers its shared stem. This is
deliberate: two Questions with identical own-text under different preambles are different
Questions, and must not collapse into one row.
