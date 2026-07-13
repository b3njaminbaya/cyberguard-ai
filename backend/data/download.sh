#!/usr/bin/env bash
# Downloads the UNSW-NB15 labeled network-traffic dataset used to train the
# detection model. Not committed to the repo (see .gitignore) — run this once.
#
# Citation: Moustafa, N., & Slay, J. (2015). UNSW-NB15: a comprehensive data
# set for network intrusion detection systems. Military Communications and
# Information Systems Conference (MilCIS). https://research.unsw.edu.au/projects/unsw-nb15-dataset
set -euo pipefail
cd "$(dirname "$0")"

curl -sL -o UNSW_NB15_training-set.csv \
  "https://huggingface.co/datasets/Mouwiya/UNSW-NB15/resolve/main/UNSW_NB15_training-set.csv"
curl -sL -o UNSW-NB15_features.csv \
  "https://huggingface.co/datasets/Mouwiya/UNSW-NB15/resolve/main/NUSW-NB15_features.csv"

echo "Downloaded $(wc -l < UNSW_NB15_training-set.csv) rows to UNSW_NB15_training-set.csv"
