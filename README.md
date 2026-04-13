# autorefine

**Autonomous text refinement using an LLM-as-judge evaluation loop.**

You give it a document. You define what "good" means in a YAML rubric. An AI agent refines the document iteratively — each change is evaluated, kept if it improves the score, discarded if it doesn't. You wake up to a better document and a full experiment log.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch), which pioneered autonomous experiment loops for ML research. autorefine adapts the same pattern for text artifacts — documents, prompts, research notes, anything — using LLM-as-judge evaluation instead of training loss.

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
  4. evaluate.py scores the artifact, compares to previous best
  5. If improved → KEEP (advance). If not → DISCARD (git reset)
  6. Repeat until CONVERGED
```

Every accepted change is a git commit. Every rejected change is reverted. The full experiment history lives in `results.tsv`. Artifact snapshots are saved in `checkpoints/` on every KEEP so you can diff any two versions.

**No GPU required.** Unlike autoresearch (which needs an H100), autorefine only needs an LLM API key. Runs on any machine.

## Quick start

```bash
# 1. Clone
git clone https://github.com/yourusername/autorefine.git
cd autorefine

# 2. Install dependencies
uv sync

# 3. Configure your LLM backend
cp .env.example .env
# Edit .env with your API key (OpenAI, Azure, Anthropic, or Ollama)

# 4. Add your artifact(s) to artifacts/
cp your-document.md artifacts/

# 5. Configure your rubric
# Edit rubric.yaml with dimensions appropriate for your document
# Or copy a template: cp templates/product-doc/rubric.yaml .

# 6. Run baseline evaluation
uv run evaluate.py --baseline --verbose

# 7. Start the refinement loop
# Open your AI coding agent (Claude Code, Codex, Cursor, etc.) and say:
#   "Read program.md and let's kick off a refinement run."
```

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

### Product documentation

Refine product pages, landing pages, and sales materials. The agent improves value proposition clarity, competitive differentiation, and audience fit while maintaining your authentic voice.

```bash
cp templates/product-doc/rubric.yaml .
cp templates/product-doc/program.md .
cp your-product-page.md artifacts/
```

**Example dimensions:** value proposition, specificity, competitive differentiation, scannability, voice & authenticity.

### Technical papers & evaluation docs

Refine whitepapers, evaluation methodology docs, and technical reports. The agent strengthens methodology rigor, reproducibility, and statistical validity.

```bash
cp templates/technical-paper/rubric.yaml .
cp templates/technical-paper/program.md .
```

**Example dimensions:** methodology rigor, reproducibility, statistical validity, transparency, organization.

### LLM skills & system prompts

Iteratively improve AI agent skills, system prompts, and instruction sets. The agent tightens instruction clarity, adds edge case coverage, and strengthens constraint enforcement.

```bash
cp templates/llm-skill/rubric.yaml .
cp templates/llm-skill/program.md .
```

**Example dimensions:** instruction clarity, edge case coverage, output format, constraint enforcement, tone consistency.

### Research notes & competitive analysis

Refine research documents, literature reviews, and market analysis. The agent improves coverage, source attribution, and synthesis quality.

```bash
cp templates/research-notes/rubric.yaml .
cp templates/research-notes/program.md .
```

**Example dimensions:** coverage, accuracy, actionability, source attribution, synthesis.

### Other use cases

autorefine works with any text artifact where quality is definable via a rubric:

- **API documentation** — completeness, example quality, error documentation
- **Blog posts & essays** — argument strength, engagement, evidence quality
- **Configuration files** — correctness, documentation, best practices
- **Pitch decks** (as markdown) — narrative arc, specificity, credibility
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

## FAQ

**How many iterations does it take?**
Depends on the artifact and rubric. Typically 10-30 iterations for meaningful improvement. The convergence detector stops the loop when scores plateau.

**How much does it cost?**
~$0.10-0.30 per iteration with GPT-4o (binary mode, 4-5 dimensions, N=3). A full run of 30 iterations costs ~$3-9. Budget cap defaults to $30.

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

## License

MIT License. See [LICENSE](LICENSE) for details.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) (MIT License). No code was copied; the implementation is original.
