# Pathway Human Review Rubric

Use this rubric to review one generated family pathway at a time. Deterministic checks catch
structural and grounding failures; this review covers the judgment they cannot make.

Score each dimension on a 1 to 3 scale:

* 1 means weak or materially problematic. The pathway would mislead, overwhelm, or fail the family.
* 2 means acceptable but needs improvement. The pathway is usable after edits.
* 3 means strong. The pathway could go to the family with little or no change.

Record scores in `examples/human_review_template.csv`, one row per case.

## Scoring dimensions

### Personalization

* 1: Generic advice that would suit almost any family. Children's interests, ages, or stated needs are absent or misread.
* 2: Reflects some stated details but leans on general self-directed education language.
* 3: Clearly written for this family. Specific children, interests, and circumstances shape the suggestions.

### Evidence support

* 1: Claims or recommendations go well beyond the retrieved Mosaic passages, or cited passages do not support them.
* 2: Mostly supported, with at least one recommendation whose connection to the cited passage is thin.
* 3: Every recommendation traces clearly to a cited passage.

### Practicality

* 1: Ignores the family's stated constraints on time, money, transportation, or supervision.
* 2: Workable in principle, but at least one suggestion would be hard to start this month.
* 3: Every suggestion is realistic for the first two weeks given the stated constraints.

### Tone

* 1: Directive, clinical, judgmental, or anxiety-producing.
* 2: Generally warm, with occasional prescriptive or evaluative phrasing.
* 3: Warm, non-directive, and respectful of the family's authority throughout.

### Scope adherence

* 1: Diagnoses a condition, prescribes a full curriculum, or promises outcomes.
* 2: Stays broadly in scope but drifts toward curriculum design or developmental assessment.
* 3: Stays within gentle, optional first steps.

### Overall usefulness

* 1: The family would be no better off, or worse off, after reading it.
* 2: Useful, but the family would need to do noticeable work to act on it.
* 3: The family could act on it this week.

## Required written fields

### Most important weakness

Name the single change that would most improve this pathway. One or two sentences. Write "none"
only when the pathway needs no change.

### Would you share this pathway as-is

Choose exactly one:

* `yes`
* `yes, after minor edits`
* `no`

## Review guidance

* Review the pathway alongside the retrieved passages that grounded it, not on its own.
* Score what the pathway says, not what you assume the model intended.
* A pathway can score 3 on tone and 1 on evidence support. Do not average the dimensions into a single number.
* Two reviewers scoring the same case independently is more informative than one reviewer scoring twice.
