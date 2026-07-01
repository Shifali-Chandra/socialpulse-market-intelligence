# SocialPulse Market Intelligence - Final Report

## Executive summary

SocialPulse collects, cleans, and analyzes public social media discussion across
YouTube and Instagram (with a Twitter dataset used for exploratory analysis only) to
surface audience interests, sentiment, engagement patterns, and emerging topics for
marketing decisions. The analysis covers ~14,300 posts across the 12 focus keywords,
refreshed continuously by an automated daily collection pipeline.

Headline: the audience is highly positive and receptive, its attention is concentrated
on AI, automation, and startup/business themes (with ChatGPT usage rising), and -
importantly - sentiment does not drive engagement, so content strategy should optimize
for topic relevance, not emotional tone.

## Scope and data

- Platforms: YouTube (~12,400 comments) and Instagram (~1,900 posts) are the analysis and
  modeling sources, balanced across 12 keywords in 4 categories (AI & automation, cloud &
  data, digital marketing, digital business).
- Twitter (~84k keyword-matched tweets) is EDA-only: it is ~99% AWS and pre-ChatGPT, so it
  is biased and is deliberately excluded from modeling and current-trend decisions.
- Methodology details are in docs/methodology_report.md and docs/feature_engineering.md;
  the interactive dashboard is data/reports/dashboard.html.

## Key findings

1. **Audience sentiment is strongly positive.** Instagram is ~86% positive; YouTube is
   ~66% positive with ~13% negative. The community is receptive and low reputational risk.
2. **Sentiment does not drive engagement.** Average engagement percentile is essentially
   identical across positive, neutral, and negative posts (spread ~0.01). Emotional tone
   is not the lever for reach.
3. **Attention concentrates on AI/automation/business.** Top keywords by volume are
   ChatGPT, Automation, Startup, AI Agents, and Digital Marketing. The largest topic is
   business/startup, and it is also the fastest-rising; a distinct ChatGPT-usage topic is
   emerging.
4. **Volume is growing and sentiment is stable** week over week across the recent window.
5. **Platform character differs.** Instagram skews promotional and highly positive;
   YouTube carries more discussion and the bulk of the (still small) negative signal.

## Recommendations

- **Lead with the rising, high-volume themes** - business/startup, AI agents, ChatGPT
  usage, and automation - in content and campaigns; these hold the most audience attention.
- **Do not optimize content for positivity to chase engagement.** Since sentiment is
  independent of engagement, invest in topic relevance, format, and timing instead.
- **Use Instagram for positive brand/community building** (very high positive share) and
  **monitor YouTube** for the minority of critical/question comments as a support and
  product-feedback channel.
- **Enter the ChatGPT-usage conversation early** - it is an emerging topic with momentum.
- **Do not use Twitter for current-trend decisions** - it is biased and dated; keep it to
  background EDA only.

## Models and validation

- **Sentiment**: VADER is the production scorer, selected by macro-F1 on an independent
  YouTube/Instagram gold set (0.65), ahead of TextBlob and a Twitter-trained classifier.
  The supervised model won in-domain (0.89) but collapsed on the deploy domain (0.52) due
  to vocabulary domain shift - a documented reason to prefer the lexicon scorer here.
- **Topics**: NMF (k=11) chosen over LDA on coherence.
- All metrics are queryable in the SQLite `model_eval` table and the model_eval reports.

## Limitations

- Lexicon sentiment is modest in absolute accuracy (deploy macro-F1 ~0.65) and English-only;
  non-English posts are not scored.
- Topics derived from comments are partly reaction-driven; title/caption-based topic
  modeling is the recommended next enhancement.
- Instagram is smaller than YouTube, so Instagram-specific conclusions are directional.
- The sentiment validation set is LLM-labeled (no human annotators), a documented proxy.
- Sentiment counts are model-dependent; compare trends over time rather than absolute
  counts across model changes.
