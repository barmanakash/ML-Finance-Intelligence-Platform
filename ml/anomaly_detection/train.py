"""Anomaly detection has no persisted global model to train.

Unlike categorization, what counts as "anomalous" is defined relative to
each user's own transaction history (master prompt Rule 12) — a transaction
that's ordinary for one user is unusual for another. The IsolationForest in
ml/anomaly_detection/predict.py is therefore fit fresh, per user, on their
real transactions at request time (see
app/services/anomaly_detection_service.py in the backend). There is nothing to train ahead of time or version in the
model registry — that architecture only makes sense for a model meant to
generalize across users, like the categorizer.

This script exists to make that design decision explicit rather than
silently absent, and to satisfy the project's train/evaluate/predict
structure. To sanity-check the detection pipeline's *mechanics* (not
real-world accuracy — there's no verified fraud data for a personal
project), run:

    python -m ml.datasets.generate_anomaly_dataset
    python -m ml.anomaly_detection.evaluate
"""

if __name__ == "__main__":
    print(__doc__)
