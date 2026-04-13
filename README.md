# autorefine

> **New here?** Start with [QUICKSTART.md](QUICKSTART.md) — first score in 5 minutes.

**Autonomous refinement of prompts, skills, and documents using an LLM-as-judge evaluation loop.**

You give it a text artifact — a system prompt, an agent skill, a product page, a technical doc. You define what "good" means in a YAML rubric. An AI agent refines it iteratively: each change is evaluated by a separate LLM judge, kept if it improves the score, discarded if it doesn't. You walk away and come back to a better artifact and a full experiment log.

Built for AI engineers who iterate on prompts, skills, and agent instructions — the highest-leverage text artifacts where small wording changes cause large behavioral shifts. Also works for product docs, technical papers, and any text where quality is definable via a rubric.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch), which pioneered autonomous experiment loops for ML research. autorefine adapts the same pattern for text artifacts using LLM-as-judge evaluation instead of training loss.

## How it works

The repo has three files that matter, mirroring autoresearch's design:

| autoresearch | autorefine | Role |
|---|---|---|
| `prepare.py` (read-only) | `evaluate.py` (read-only) | Fixed evaluation function |
| `train.py` (agent edits) | `artifacts/*` (agent edits) | The thing being optimized |
| `program.md` (human edits) | `program.md` (human edits) | Strategy instructions |

**The loop:**

```
LOOP:
  1. Agent reads per-dimension scores, identifies weakest dimension
  2. Agent makes ONE targeted edit to the artifact
  3. Agent commits and runs evaluate.py
  4. evaluate.py scores, compares to previous best, and renders a verdict
  5. KEEP → advance. DISCARD → auto-reverted. CONVERGED → stop.
  6. Repeat until CONVERGED
```

The protocol is **mechanically enforced** — evaluate.py refuses to run with uncommitted changes and auto-reverts on DISCARD. The agent can't make a protocol mistake.

Every accepted change is a git commit. Every rejected change is automatically reverted. The full experiment history lives in `results.tsv`. Artifact snapshots are saved in `checkpoints/` on every KEEP so you can diff any two versions.

**No GPU required.** Unlike autoresearch (which needs an H100), autorefine only needs an LLM API key. Runs on any machine.

## How to use

### Phase 1: Setup (5 minutes)

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), one LLM API key (OpenAI, Azure, Anthropic, or Ollama). macOS and Linux. Anthropic users also run `uv add anthropic` after setup.

```bash
git clone https://github.com/mihirdash108/autorefine.git
cd autorefine
uv sync
cp .env.example .env     # add your OpenAI/Anthropic/Azure key
cp your-document.md artifacts/
```

### Phase 2: Define quality (with Claude Code)

Open Claude Code in the autorefine directory and configure your rubric. This is the creative step — you're defining what "good" means for your document.

```bash
claude
```

Then say:

> "I'm refining a product page for enterprise buyers. Help me write a rubric."

Claude reads your document, suggests dimensions, writes `rubric.yaml`. You iterate together — adjust criteria, calibrate with `uv run calibrate.py`, until the rubric matches your intuition about what makes the doc good.

Or start from a template:

```bash
cp templates/product-doc/rubric.yaml .
cp templates/product-doc/program.md .
```

### Phase 3: Run (walk away)

With the Claude Code skill installed:

```
/autorefine
```

This single command runs baseline, opens the dashboard, and starts the refinement loop in the background. You continue working. You get notified when it converges.

**Without the skill:** `bash start.sh` does the same thing manually.

**Monitor progress:** Open http://localhost:8501 for the live dashboard, or run `/autorefine status`.

### Installing the Claude Code skill (optional but recommended)

Copy the skill to your Claude Code skills directory:

```bash
cp -r skill/ ~/.claude/skills/autorefine/
```

This gives you:
- `/autorefine` — run the full loop in the background
- `/autorefine status` — check progress
- `/autorefine stop` — terminate a running loop
- `/autorefine resume` — pick up after a crash

## Cost

Be aware of the full cost breakdown:

| Component | Per iteration | 30 iterations |
|---|---|---|
| **Judge** (evaluate.py LLM calls) | ~$0.10-0.30 | $3-9 |
| **Refiner** (Claude Code agent calls) | ~$0.50-2.00 | $15-60 |
| **Total** | ~$0.60-2.30 | **$18-69** |

The judge cost is tracked in `eval_state.json`. The refiner cost depends on your Claude Code plan and artifact size. Set `--budget-cap` for judge cost control and max iterations for overall cost control.

The agent will create a branch, run the loop autonomously, and stop when scores converge.

## Supported LLM backends

autorefine auto-detects your backend from environment variables:

| Backend | Env vars | Notes |
|---|---|---|
| **OpenAI** | `OPENAI_API_KEY` | Recommended default |
| **Azure OpenAI** | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` | Enterprise deployments |
| **Anthropic** | `ANTHROPIC_API_KEY` | Requires `uv add anthropic` |
| **Ollama** | `OLLAMA_BASE_URL` | Local models, free |

Override with `AUTOREFINE_BACKEND=openai|azure|anthropic|ollama` and `AUTOREFINE_MODEL=model-name`.

**Key design choice:** Use a different model family for the judge than for the refiner. If Claude Code is your refiner, use GPT-4o as the judge (and vice versa). This avoids [self-preference bias](#self-preference-bias), where models rate their own outputs higher.

## Evaluation modes

### Binary mode (default, recommended)

Each dimension is evaluated as **pass/fail**. Three independent evaluations per dimension, majority vote. Combined score is the fraction of dimensions passing.

```yaml
eval_mode: binary

dimensions:
  clarity:
    pass: "Main point is clear within 30 seconds of reading."
    fail: "Main point is buried or requires full read to find."
```

**Why binary?** Research shows binary judgments have higher inter-rater reliability, are harder to game, and are statistically more efficient than numeric scales. You don't need to calibrate what "7 out of 10" means — you just need to define what "good enough" looks like.

> "Tracking a bunch of scores on a 1-5 scale is often a sign of a bad eval process." — [Hamel Husain](https://hamel.dev/blog/posts/llm-judge/)

### Scale mode

Each dimension scored on a **1-5 scale** (not 1-10 — [research shows](https://arxiv.org/html/2601.03444v1) 0-5 has the highest inter-rater agreement). Three evaluations per dimension, median score.

```yaml
eval_mode: scale
scale_range: 5

dimensions:
  clarity:
    description: "How clearly does the document communicate its main point?"
    anchors:
      1: "Main point completely unclear."
      3: "Main point exists but buried."
      5: "Immediately clear within 30 seconds."
```

Use scale mode when you need fine-grained progress tracking or when binary is too coarse for your dimensions.

## Use cases

### LLM skills, system prompts & agent config (primary use case)

The highest-leverage text artifacts: small wording changes cause large behavioral shifts. autorefine iteratively tightens instruction clarity, catches edge case gaps, and strengthens constraint enforcement — with a keep/discard gate that prevents iteration 15 from breaking what iteration 8 fixed.

```bash
cp templates/llm-skill/rubric.yaml .
cp templates/llm-skill/program.md .
cp my-skill.md artifacts/
```

**Example dimensions:** instruction clarity, edge case coverage, output format, constraint enforcement, tone consistency.

**Works for any agent instruction file:**

- **Claude Code skills** (`SKILL.md`) — refine the trigger conditions, step-by-step instructions, and subagent prompts. Evaluate whether the agent follows the skill correctly across different invocations.
- **CLAUDE.md project rules** — iterate on your project-level instructions until the agent consistently follows them. Dimensions like "rule clarity," "no ambiguity," and "covers edge cases" catch vague instructions that agents interpret differently each time.
- **User preference files** — refine your personal CLAUDE.md rules based on accumulated feedback. Add a dimension for "does this rule prevent the specific mistake it was written for?" to ensure rules stay actionable.
- **MCP tool descriptions** — tighten tool descriptions so the agent picks the right tool for each task. Evaluate with "does the description unambiguously differentiate this tool from similar ones?"

### Technical papers & evaluation docs

Strengthen methodology rigor, reproducibility, and statistical validity. Catch information security leaks — implementation details that shouldn't be in a public document. (See [case study](#case-study) below.)

```bash
cp templates/technical-paper/rubric.yaml .
cp templates/technical-paper/program.md .
```

**Example dimensions:** methodology rigor, reproducibility, statistical validity, transparency, information security.

### Product documentation

Refine product pages and sales materials. Improve value proposition clarity, competitive differentiation, and audience fit while maintaining authentic voice.

```bash
cp templates/product-doc/rubric.yaml .
cp templates/product-doc/program.md .
```

**Example dimensions:** buyer clarity, competitive differentiation, evidence quality, document effectiveness, information security.

### Research notes & competitive analysis

Improve coverage, source attribution, and synthesis quality.

```bash
cp templates/research-notes/rubric.yaml .
cp templates/research-notes/program.md .
```

**Example dimensions:** coverage, accuracy, actionability, source attribution, synthesis.

### Other use cases

autorefine works with any text artifact where quality is definable via a rubric:

- **API documentation** — completeness, example quality, error documentation
- **Blog posts & essays** — argument strength, engagement, evidence quality
- **MCP tool descriptions** — clarity, parameter documentation, example coverage
- **Agent instruction sets** — constraint enforcement, edge cases, output format
- **Runbooks & SOPs** — step completeness, error handling, clarity under stress

## Writing effective rubrics

The rubric is the most important file in autorefine. A bad rubric means the agent optimizes in the wrong direction. Here's how to write a good one.

### Start with binary, upgrade to scale only if needed

Binary (pass/fail) is the default for a reason:

- **Easier to define.** "Does this document clearly state who it's for?" is easier to answer than "How well does it state who it's for, on a scale of 1-5?"
- **Higher reliability.** LLM judges agree with humans more on binary judgments than scaled ones.
- **Harder to game.** You can't score 0.1 higher by adding a sentence. Either it passes or it doesn't.

Only switch to scale mode when you need fine-grained progress tracking over many iterations on a well-understood artifact type.

### Keep 3-5 dimensions maximum

More than 5 dimensions creates:
- **Overlap** — "Specificity" and "Evidence Quality" end up measuring the same thing
- **Diluted signal** — Improving one dimension by a lot matters less when it's 1 of 9
- **Annotation fatigue** — The LLM judge produces lower quality scores on dimension 8 than dimension 1

**Test for orthogonality:** Can you construct a document that passes dimension A but fails dimension B? If not, they're measuring the same thing — merge them.

### Write concrete pass/fail criteria

Bad: "Is the document clear?"
Good: "A reader can identify the document's main point, target audience, and key takeaway within 30 seconds of reading."

Bad: "Score 3: Medium quality"
Good: "Score 3: Main point exists but requires reading 2-3 sections to find. Some claims lack supporting evidence."

**For scale mode, anchor only the extremes.** Research shows that providing anchors for scores 1, 3, and 5 produces better calibration than anchoring every level. The LLM interpolates the middle scores naturally.

### Add anti-gaming dimensions

Without them, the agent will optimize for easy wins:
- **Conciseness** — Prevents content inflation (the agent adding paragraphs to pass more dimensions)
- **Voice/Authenticity** — Prevents corporate voice drift ("unlock the full potential of...")
- **Scannability** (defined carefully) — "Scannable WITH depth" prevents bullet-point-ification

### Calibrate before running

Use `calibrate.py` to validate your rubric ranks known-quality variants correctly:

```bash
# Create 2-3 variants of your document: a good one, baseline, and a bad one
uv run calibrate.py good-version.md baseline.md bad-version.md
```

If the rubric doesn't rank them correctly, fix the dimensions before running the loop. The calibration takes 5 minutes and validates your entire evaluation approach.

## LLM-as-judge: what you need to know

autorefine uses an LLM to judge document quality. This is fundamentally different from autoresearch's deterministic `val_bpb` metric. Here's what you need to understand.

### It works — with guardrails

GPT-4 class models agree with human evaluators 80-87% of the time — matching inter-human agreement rates ([MT-Bench, Chatbot Arena](https://arxiv.org/abs/2306.05685)). The judge is reliable enough for iterative refinement, but you need the right guardrails.

autorefine includes several:
- **N=3 evaluation** — Each dimension scored 3 times, majority vote (binary) or median (scale)
- **Minimum improvement threshold** — Changes must clear a noise floor to be kept
- **Convergence detection** — Stops when scores plateau instead of random-walking
- **Budget cap** — Won't exceed your spending limit
- **Checkpoint snapshots** — Human can audit the trajectory

### Known biases and mitigations

| Bias | What happens | How autorefine handles it |
|---|---|---|
| **Verbosity bias** | Longer responses score higher | Conciseness dimension + word count tracking |
| **Self-preference** | Models prefer their own outputs | Use different model family for judge vs. refiner |
| **Leniency** | GPT-4 gives 4.7/5 where humans give 2.9/5 | Binary mode (pass/fail) is harder to inflate |
| **Position bias** | First option preferred in comparisons | Not applicable (absolute scoring, not pairwise) |

### Reducing judge variance

- **Temperature 0** — Reduces but doesn't eliminate variance (GPU non-determinism)
- **N=3 with majority vote** — Smooths out individual run noise
- **Structured JSON output** — Forces discrete commitment, reduces phrasing variability
- **CoT before scoring** — Reasoning before verdict prevents post-hoc rationalization

### Model selection

**Best practice: different model family for judge vs. refiner.**

| Refiner | Recommended Judge |
|---|---|
| Claude Code (Claude) | GPT-4o (OpenAI) or Gemini |
| Codex / ChatGPT (OpenAI) | Claude Sonnet |
| Cursor (mixed) | GPT-4o or Claude Sonnet |

If budget is a concern, **multi-judge panels** using 3 smaller models (e.g., GPT-4o-mini + Claude Haiku + Gemini Flash) outperform a single GPT-4 while being 7-8x cheaper ([PoLL paper](https://arxiv.org/abs/2404.18796)).

### Key research

| Finding | Source |
|---|---|
| Binary > Likert for reliability | [Husain, LLM Judge Guide](https://hamel.dev/blog/posts/llm-judge/) |
| 0-5 scale beats 0-10 (ICC 0.853 vs 0.805) | [Grading Scale Impact, 2026](https://arxiv.org/html/2601.03444v1) |
| Temperature-consistency correlation: -0.98 | [Temperature in LLM-as-Judge, 2026](https://arxiv.org/html/2603.28304) |
| 3-model panel > single GPT-4 at 7-8x less cost | [PoLL, Verga et al.](https://arxiv.org/abs/2404.18796) |
| CoT before scoring prevents rationalization | [Wolfe, LLM-as-a-Judge](https://cameronrwolfe.substack.com/p/llm-as-a-judge) |
| Self-preference: GPT-4 picks own output 87.76% | [MT-Bench, Zheng et al.](https://arxiv.org/abs/2306.05685) |
| Anchor only extremes for best calibration | [Design Choices Impact, 2025](https://arxiv.org/html/2506.13639v1) |

## Configuration reference

### rubric.yaml

```yaml
eval_mode: binary          # "binary" (recommended) or "scale"
scale_range: 5             # 1-N scale for scale mode (5 is optimal)
judge_model: gpt-4o        # Default model (override with AUTOREFINE_MODEL)
cross_doc_weight: 0.15     # Cross-document consistency weight (0 to disable)

placeholder_mocks:         # Mock values for {PLACEHOLDER} tokens
  METRIC_A: "0.94"         # Judge sees "0.94" instead of "{METRIC_A}"

artifacts:
  my-document.md:
    weight: 1.0            # Relative weight in combined score
    context: "Description of document purpose and audience"
    dimensions:
      dimension_name:
        weight: 0.25       # Weight within this artifact (scale mode)
        pass: "Criteria for passing (binary mode)"
        fail: "Criteria for failing (binary mode)"
        description: "What this dimension measures (scale mode)"
        anchors:            # Score anchors (scale mode)
          1: "Description of score 1"
          3: "Description of score 3"
          5: "Description of score 5"
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | One backend required | Standard OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | For Azure | Azure endpoint URL |
| `AZURE_OPENAI_API_KEY` | For Azure | Azure API key |
| `AZURE_OPENAI_API_VERSION` | For Azure | API version (default: 2024-12-01-preview) |
| `AZURE_OPENAI_MODEL` | For Azure | Model deployment name |
| `ANTHROPIC_API_KEY` | For Anthropic | Anthropic API key |
| `OLLAMA_BASE_URL` | For Ollama | Ollama server URL (default: http://localhost:11434) |
| `AUTOREFINE_BACKEND` | Optional | Force a specific backend |
| `AUTOREFINE_MODEL` | Optional | Override model name |

### Exit codes

| Code | Meaning | Agent action |
|---|---|---|
| 0 | Evaluation complete | Read verdict from output |
| 1 | Validation failure (placeholder removed, empty file) | Revert and fix |
| 2 | Infrastructure error (API timeout, auth failure) | Wait and retry |

## Project structure

```
autorefine/
├── evaluate.py          # Fixed evaluation engine (do not modify)
├── calibrate.py         # Rubric calibration tool
├── rubric.yaml          # Your evaluation rubric (human-curated)
├── program.md           # Agent instructions (human-curated)
├── artifacts/           # Documents being refined (agent modifies)
├── templates/           # Example rubric+program for common use cases
│   ├── product-doc/
│   ├── technical-paper/
│   ├── llm-skill/
│   └── research-notes/
├── checkpoints/         # Artifact snapshots on each KEEP
├── results.tsv          # Experiment log (auto-generated)
├── eval_state.json      # Evaluation state (auto-generated)
├── pyproject.toml       # Dependencies
├── .env.example         # Environment variable template
└── .env                 # Your API keys (gitignored)
```

## Customizing for your project

The repo ships with a generic 4-dimension rubric. Here's how to adapt it for a real project — this is the same process we use internally.

### Step 1: Copy a template

Pick the closest template and copy it to the root:

```bash
cp templates/product-doc/rubric.yaml .
cp templates/product-doc/program.md .
```

### Step 2: Add your artifacts

```bash
rm artifacts/example.md
cp ~/path/to/your-document.md artifacts/
```

If you have multiple related documents, add them all. Set `cross_doc_weight: 0.15` in rubric.yaml to score cross-document consistency.

### Step 3: Customize the rubric

**a) Update artifact entries.** Replace the template artifact name with yours:

```yaml
artifacts:
  your-document.md:
    weight: 1.0
    context: >
      Product page for enterprise analytics teams. Target audience:
      VP of Data who needs to justify the purchase to their CTO.
```

The `context` field is critical — it tells the judge *who* the document is for, which changes how quality is assessed.

**b) Tune your dimensions.** Start with the template dimensions, then:
- Remove dimensions that don't apply to your artifact
- Add dimensions specific to your domain
- Keep it to 3-5 dimensions (more creates overlap and dilutes signal)

**c) Add placeholder mocks** if your documents have template variables:

```yaml
placeholder_mocks:
  REVENUE: "$4.2M"
  USERS: "1,250"
  METRIC_SCORE: "0.94"
```

The judge sees the mock values; the agent preserves the real `{PLACEHOLDER}` tokens.

### Step 4: Customize the program

Edit `program.md` to add domain-specific strategy guidance. The template has the generic loop — add a `## Strategy` section with advice like:

```markdown
## Strategy

- This document is for enterprise buyers. Lead with business outcomes, not technical architecture.
- The competitive landscape section is the weakest — competitors are mentioned but not specifically characterized.
- Preserve all data tables exactly. Only refine the narrative prose.
- The "Limitations" section is a credibility signal — make it more substantive, not shorter.
```

### Step 5: Calibrate (recommended)

Before running the full loop, validate your rubric:

```bash
# Create a deliberately worse version of your doc
cp artifacts/your-document.md /tmp/bad-version.md
# (manually degrade it — remove evidence, add vague claims, break structure)

uv run calibrate.py artifacts/your-document.md /tmp/bad-version.md
```

If the rubric doesn't rank the good version higher, fix your dimensions before running the loop.

### Step 6: Run

```bash
uv run evaluate.py --baseline --verbose   # See initial scores
# Then open your coding agent and say: "Read program.md and let's kick off a refinement run."
```

### Example: adapting for a technical evaluation paper

```yaml
# rubric.yaml — adapted for a technical paper
eval_mode: binary
judge_model: gpt-4o
cross_doc_weight: 0.0    # single document

placeholder_mocks:
  SCORE_A: "0.94"
  SCORE_B: "0.91"
  P99_LATENCY: "3200"

artifacts:
  evaluation-methodology.md:
    weight: 1.0
    context: >
      Technical evaluation paper for due-diligence reviewers
      assessing a RAG system. Readers will scrutinize methodology
      choices, statistical claims, and reproducibility.
    dimensions:
      methodology_rigor:
        weight: 0.25
        pass: >
          Every methodology choice is justified — sample sizes, metric
          selection, bias mitigation, evaluation design. Would pass
          peer review.
        fail: >
          Key methodology choices are unexplained. "Why 100 queries?"
          or "Why this metric?" has no answer in the document.
      reproducibility:
        weight: 0.25
        pass: >
          An independent researcher could reproduce the evaluation
          from this document alone. Exact commands, model versions,
          parameters, and expected outputs are specified.
        fail: >
          Reproduction requires reading source code or asking the
          authors. Missing versions, parameters, or environment details.
      statistical_validity:
        weight: 0.25
        pass: >
          Variance reported across runs, claims appropriately hedged
          given sample sizes. No single-run numbers presented as
          definitive.
        fail: >
          Reports single-run numbers as fact. No variance, no
          confidence intervals, claims overreach the evidence.
      transparency:
        weight: 0.25
        pass: >
          Limitations are substantive and honest. The document
          distinguishes measured results from inferred conclusions.
          Reader trusts it because of what it admits.
        fail: >
          No limitations section, or limitations are trivial. Some
          claims in the results overstep what was actually measured.
```

## Related work

autorefine sits at the intersection of autonomous agent loops and LLM-based evaluation:

| | autorefine | [autoresearch](https://github.com/karpathy/autoresearch) | [Self-Refine](https://github.com/madaan/self-refine) | [DSPy](https://github.com/stanfordnlp/dspy) | [TextGrad](https://github.com/zou-group/textgrad) |
|---|---|---|---|---|---|
| **Optimizes** | Document quality | ML training code | LLM outputs | Prompt templates | Text variables |
| **Evaluation** | LLM judge + rubric | Deterministic metric | Same-model feedback | Metric on dataset | LLM "gradients" |
| **Keep/discard gate** | Yes | Yes | No | N/A | No |
| **Multi-dimensional** | Yes (weighted rubric) | No (single scalar) | No | Yes | No |
| **Human rubric** | Yes | No | No | No | No |
| **Convergence detection** | Yes | No | No | N/A | No |
| **Cross-doc consistency** | Yes | No | No | No | No |

**Key differentiators:**
- **vs. autoresearch:** Generalizes to text quality (not just computable metrics). Multi-dimensional rubric. No GPU required.
- **vs. Self-Refine:** Separate judge model (not self-evaluation). Explicit keep/discard gate. Git-based rollback.
- **vs. DSPy:** Optimizes the output document, not the prompt template. Runtime iterative, not compile-time.
- **vs. TextGrad:** Structured rubric dimensions. Explicit quality gate. Convergence detection.

## Case study: catching proprietary information leaks

A fintech startup ran autorefine on their technical evaluation document — a whitepaper describing their RAG system's benchmark methodology. The document was well-written (4/5 dimensions passing at baseline) but had one critical gap: it leaked proprietary implementation details.

**The problem:** The document exposed exact algorithm parameters (retrieval fusion weights, clustering configuration values), internal database schema details (driver names, function signatures, connection pooling config), internal repository URLs, container names, and environment variable names. A technical competitor could reconstruct key parts of the system from the document alone.

**What autorefine did:**
- Added an `information_security` dimension: "Communicates capabilities without revealing how to replicate them"
- **Iteration 1 (DISCARD):** Over-abstracted the reproduction section — removed all concrete commands, which broke the `reproducibility` dimension. The keep/discard gate caught this automatically.
- **Iteration 2 (KEEP):** Found the right balance — abstracted implementation parameters while keeping reproduction commands concrete with placeholder identifiers. 14 specific changes: algorithm parameters removed, database internals abstracted, internal URLs replaced with access-request emails, environment variable names generalized.
- **Converged at 100%** (all dimensions passing) after 6 total iterations.

**Result:** 14 proprietary details caught and fixed. Total cost: $0.12. Total time: ~20 minutes unattended. The keep/discard gate was critical — it prevented the over-abstraction that a one-shot edit would have shipped without feedback.

**Key insight:** The agent caught leaks a human reviewer missed — not because the human was careless, but because checking "does this table cell contain a proprietary parameter?" across 50+ data points is exactly the kind of systematic, dimension-specific sweep that an LLM judge excels at.

## When to use autorefine (and when not to)

**Use autorefine when:**
- The artifact is **high-leverage** — system prompts, agent skills, product pages, evaluation docs where small changes have outsized impact
- You need **auditability** — a git log of every change, what it improved, and what was rejected
- You need **regression protection** — improving one dimension without silently degrading another
- You can **walk away** — the loop runs unattended while you do other work
- Quality is **definable** — you can articulate pass/fail criteria for 3-5 dimensions

**Don't use autorefine when:**
- You need a **quick one-pass improvement** — just ask Claude/ChatGPT directly. 5 minutes, ~$0.10, good enough for most cases.
- The document needs a **full rewrite**, not iterative refinement
- Quality depends on **external validation** (user testing, conversion rates, code correctness) that an LLM judge can't measure
- The artifact is **too short** to benefit from multi-dimensional evaluation (a 3-sentence bio doesn't need 10 iterations)

## FAQ

**How many iterations does it take?**
Typically 3-10 iterations for meaningful improvement. The convergence detector stops when scores plateau. Default max is 10 — diminishing returns set in after that.

**How much does it cost?**
~$0.60-2.30 per iteration (judge + refiner combined). A typical run of 5-10 iterations costs $3-23. Budget cap defaults to $30.

**Can I use local models?**
Yes, via Ollama. Set `OLLAMA_BASE_URL` in .env. Quality depends on the model — larger models make better judges.

**What coding agent should I use?**
Any agent that can read a file and follow instructions: Claude Code, Codex, Cursor, Windsurf, Aider. The program.md is agent-agnostic.

**Can I refine multiple documents at once?**
Yes. Put them all in `artifacts/`. Configure each in `rubric.yaml`. Set `cross_doc_weight > 0` to score cross-document consistency.

**How do I know the scores are meaningful?**
Run `calibrate.py` with known-quality variants before starting. If the rubric ranks them correctly, the scores are meaningful for your use case.

**What if the agent makes the document worse?**
It can't — the keep/discard gate ensures the committed version only improves. Every rejected change is reverted via git. That said, "score goes up" may not always mean "actually better" — use checkpoint diffs to audit the trajectory.

**Why not just ask Claude to improve my document?**
For most cases, you should! A one-shot Claude edit is faster and cheaper. autorefine is for when you need the audit trail, regression protection, exhaustive optimization, and unattended execution that a single conversation doesn't provide.

## License

MIT License. See [LICENSE](LICENSE) for details.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) (MIT License). No code was copied; the implementation is original.
