"""Ask WellBe answer engine (WEL-166).

A v1 closed-corpus, deterministic, non-diagnostic answer engine. It grounds
answers only in the user's own C7 threads + C9 pending items (source-linked),
classifies intent (urgent / out-of-scope diagnosis-treatment / answerable),
composes a source-linked summary, and passes the C10 gate before release. See
docs/decisions/ask-answer-engine-semantics.md.
"""
