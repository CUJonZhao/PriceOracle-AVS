# PriceOracle-AVS Paper Workspace

IEEE conference template, double-column. Target length 4-6 pages.

## Structure

```
paper/
├── main.tex              # entry point; \input's the 8 sections
├── references.bib        # 20 entries, 6 peer-reviewed
├── sections/
│   ├── 01_intro.tex                    [M4]
│   ├── 02_eigenlayer_background.tex    [M4]
│   ├── 03_contracts.tex                [M1]
│   ├── 04_operator.tex                 [M2]
│   ├── 05_aggregator.tex               [Jon]  ← already drafted
│   ├── 06_evaluation.tex               [M4]
│   ├── 07_discussion.tex               [M4 + M2]
│   └── 08_conclusion.tex               [M4]
└── figures/
    ├── fig_v1_median_robustness.pdf    ← Jon (already in)
    ├── fig_v2_tolerance_sensitivity.pdf
    ├── fig_v3_aggregation_latency.pdf
    └── (others to be added by M1/M2/M4)
```

## How to compile (3 options)

### Option 1: Overleaf (recommended for collaboration)

1. Zip the `paper/` directory.
2. Go to overleaf.com → New Project → Upload Project → drop the zip.
3. Set compiler to **pdflatex**, main document to `main.tex`.
4. Invite the other 3 teammates as collaborators.
5. Hit Recompile.

### Option 2: VSCode + LaTeX Workshop (local Windows or WSL)

1. Install TeX Live (Windows: TeX Live 2024 installer; WSL:
   `sudo apt install texlive-full`).
2. Install the LaTeX Workshop extension in VSCode.
3. Open `paper/main.tex`, hit **Build LaTeX project** (recipe:
   pdflatex → bibtex → pdflatex → pdflatex).

### Option 3: command line

```bash
cd paper
latexmk -pdf main.tex
```

## Author & section ownership

| Section | Owner | Status |
|---------|-------|--------|
| §I  Introduction                           | M4  | placeholder |
| §II EigenLayer Background                  | M4  | placeholder |
| §III Smart Contract Design                 | M1  | placeholder + 1 code listing |
| §IV Operator Implementation                | M2  | placeholder + 1 code listing |
| §V Aggregator (BLS + Median)               | Jon | **drafted** (3 figs) |
| §VI End-to-End Evaluation                  | M4  | placeholder + 2 tables |
| §VII Discussion                            | M4  | placeholder |
| §VIII Conclusion + Member Contributions    | M4  | placeholder (req'd by spec) |

Each section file has a comment block at the top explaining what
goes in each subsection and roughly how many words. Stick to that
budget so we stay in 4-6 pages.

## Page budget

| Section | Target | Running total |
|---------|--------|---------------|
| Title block + Abstract | 0.3 col | 0.3 |
| §I  Introduction       | 0.5     | 0.8 |
| §II EigenLayer Bg      | 0.5     | 1.3 |
| §III Contracts         | 1.0     | 2.3 |
| §IV Operator           | 1.0     | 3.3 |
| §V  Aggregator         | 1.0     | 4.3 |
| §VI Evaluation         | 0.8     | 5.1 |
| §VII Discussion        | 0.4     | 5.5 |
| §VIII Conclusion       | 0.3     | 5.8 |

(One IEEE column ≈ 0.5 page, so 5.8 columns ≈ 2.9 pages of single-column-equivalent ≈ ~5.5 IEEE *pages* once you account for the 2-column layout. Comfortably within 4-6.)

## When in doubt

- `\IEEEPARstart{X}{ABCD}` for the drop-cap on the first paragraph
  of §I; the rest of §I-§VIII just use normal `\par`.
- Code listings: `\begin{lstlisting}[language=Solidity]...\end{lstlisting}`
  (already configured in `main.tex` for Solidity and Go).
- Figures: 0.95\columnwidth keeps them inside one column.
- Cite with `~\cite{key}` (note the tilde to avoid line break before the cite).
