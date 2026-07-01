# AI Tool Usage

Generative AI tools were used to streamline development and analysis, as encouraged by
the project brief. Each tool, how it was used, and the outcomes are documented below.

## ChatGPT (OpenAI)

- Helped consolidate scattered ideas and notes into a single, clear project objective and
  problem statement.
- Provided regex patterns for social-text cleaning - removing URLs, @mentions, and hashtag
  symbols, and decoding HTML entities so artifacts (for example "&#39;") did not leak into
  the text.
- Supplied boilerplate for API and data-collection calls (YouTube Data API and the Apify
  Instagram scraper) as starting points.
- Helped with pandas transformations for the structural text features (character/word
  counts, hashtag/mention/emoji counts) and the within-platform engagement normalization.
- Suggested library usage and parameters for scikit-learn (TF-IDF, NMF/LDA) and the VADER
  and TextBlob sentiment scorers.
- Offered ideas for visualizing text data, including word clouds and chart-type choices
  for the dashboard.
- Helped interpret analysis outputs in plain language (for example, what a macro-F1 or a
  topic-coherence value indicates).

## Gemini (Google)

- Provided architecture guidance - reference architectures for social media analytics
  pipelines to inform the overall design.
- Helped sanity-check the layered flow: raw -> clean -> unified store -> feature
  engineering -> analysis.
- Informed storage choices (SQLite with indexing and full-text search) that fit the
  lightweight, no-heavy-infrastructure constraint.
- Suggested the automated-collection approach using scheduled GitHub Actions rather than a
  streaming or orchestration platform.
- Gave input on structuring the repository and modules for reuse across platforms and
  stages.
- Helped weigh design trade-offs, such as new-content-only collection versus re-fetching,
  and keeping Twitter separate from the modeling data.

## Claude (Anthropic)

- Debugging broken code - diagnosing errors and tracebacks and fixing failing scripts.
- Reviewing logic and edge cases, such as the encoding fallback on the Twitter file,
  deduplication keys, and null/empty-text handling.
- Generated human-friendly summaries of analysis results (for example, weekly sentiment
  changes and shifts in topic prevalence).
- Drafted and refined the phrasing of conclusions and marketing recommendations in the
  final report.
- Summarized model-evaluation results (sentiment leaderboards, topic coherence) into
  plain-language findings.
- Improved the clarity and consistency of the project documentation.

## Verification

All AI-suggested code snippets and phrasing were reviewed and validated against actual
pipeline runs. Reported metrics (sentiment leaderboards, topic coherence, engagement
figures) come from executed code and the data, not from any tool's assertions.
