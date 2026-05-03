#!/bin/bash
set -e

echo "[run_ner] Removing old org.json and cleaned_htmls.tar.gz..."
rm -f  ${NER_HOME}/org.json
rm -f  ${NER_HOME}/cleaned_htmls.tar.gz

echo "[run_ner] Resetting ${NER_WORK_DIR}/input and output..."
rm -rf ${NER_WORK_DIR}/input
rm -rf ${NER_WORK_DIR}/output
mkdir ${NER_WORK_DIR}/output
mkdir -p ${NER_WORK_DIR}/input

echo "[run_ner] Copying cleaned_htmls.tar.gz from entry host..."
scp ${ENTRY_HOST}:${ENTRY_STAGE_DIR}/cleaned_htmls.tar.gz ${NER_HOME}

echo "[run_ner] Copying org.json from entry host..."
scp ${ENTRY_HOST}:${ENTRY_STAGE_DIR}/org.json ${NER_HOME}

echo "[run_ner] Extracting cleaned_htmls.tar.gz into input..."
tar -xzf ${NER_HOME}/cleaned_htmls.tar.gz -C ${NER_WORK_DIR}/input

echo "[run_ner] Submitting SLURM job..."
sbatch ${NER_HOME}/run.sh
