#!/bin/bash
#SBATCH --job-name=deepseek-llm
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=48:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=<slurm-partition>
#SBATCH --account=<slurm-account>
#SBATCH --output=slurm-%j.out

source ${NER_VENV}/bin/activate
python3 ${NER_HOME}/main.py
