#!/bin/bash

# Usage: curl -sS https://raw.githubusercontent.com/Akkisdiary/ai-tools/refs/heads/main/src/runpod/pull_hf_dataset.sh | bash <repo_id> <dataset_path>

set -e

REPO_ID=$1
DATASET_PATH=$2
TARGET_DIR="/app/ai-toolkit/datasets/${REPO_ID}"

if [ -z "$REPO_ID" ] || [ -z "$DATASET_PATH" ]; then
    echo "Error: Missing arguments."
    echo "Usage: hf pull_aitoolkit_dataset_hf.sh <repo_id> <dataset_path>"
    exit 1
fi

if ! hf auth whoami &>/dev/null; then
    echo "Warning: Not logged into Hugging Face CLI. Attempting to log in..."
    hf auth login
    
    if ! hf auth whoami; then
        echo "Please run 'hf auth login' and provide your token before running this script."
        exit 1
    fi
else
    echo "Successfully authenticated with Hugging Face CLI."
fi

echo "Starting dataset download for $REPO_ID:$DATASET_PATH..."

mkdir -p "$TARGET_DIR"


echo "Starting dataset download for $REPO_ID:$DATASET_PATH (Flattening files)..."

mkdir -p "$TARGET_DIR"
TEMP_DOWNLOAD_DIR=$(mktemp -d)

hf download \
    --repo-id "$REPO_ID" \
    --local-dir "$TEMP_DOWNLOAD_DIR" \
    --include "$DATASET_PATH/*" \
    --local-dir-use-symlinks False

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: Failed to download the dataset."
    rm -rf "$TEMP_DOWNLOAD_DIR"
    exit 1
fi

find "$TEMP_DOWNLOAD_DIR" -mindepth 1 -maxdepth 1 -exec sh -c 'cp -r "{}"/* "$TARGET_DIR"' \;

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Success: Dataset contents downloaded and flattened to '$TARGET_DIR'."
else
    echo ""
    echo "❌ Error: Failed during the file flattening/copy process."
fi

rm -rf "$TEMP_DOWNLOAD_DIR"
