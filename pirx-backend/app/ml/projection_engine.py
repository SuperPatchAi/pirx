"""Core projection engine orchestrating the full ML pipeline.

Pipeline:
1. Load user's feature vectors (rolling-window training metrics)
2. Select model tier based on data maturity (LMC → KNN → Gradient Boosting → LSTM)
3. Compute projected time for each registered event
4. Decompose improvement into 5 structural drivers
5. Apply volatility dampening (suppress deltas < 2 seconds)
6. Store immutable projection state
"""
