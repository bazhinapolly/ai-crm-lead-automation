# Lead Scoring Evaluation

The repository includes a versioned synthetic specification set with five Hot, five Warm, and five Cold examples. The cases contain no real client data and exercise urgency, buying intent, budget signals, service categories, and low-intent boundaries.

Run `python3 tools/evaluate_scoring.py --require-perfect` to reproduce the checked result: 15/15 (100%), with precision and recall of 1.00 and zero false positives or false negatives for every priority label.

This proves conformance to the documented synthetic policy, not real-world sales performance. Before a client rollout, extend the cases with approved de-identified historical outcomes and agree on the business cost of false assignments.

Optional provider run:

```bash
OPENAI_API_KEY='your-key' OPENAI_MODEL='gpt-4o-mini-2024-07-18' python3 tools/evaluate_scoring.py --mode openai
```

No live OpenAI score is claimed until that paid run is completed for the selected model and reviewed against the target pipeline.
