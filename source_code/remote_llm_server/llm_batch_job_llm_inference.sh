#!/bin/bash
#SBATCH --job-name=deepseek-llm
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=24
#SBATCH --time=72:00:00
#SBATCH --gres=gpu:2              # change to 4 if tensor-parallel-size=4
#SBATCH --partition=<slurm-partition>
#SBATCH --account=<slurm-account>
#SBATCH --output=slurm-%j.out

module reset
module load Anaconda3/2020.11

bash safety_watchdog.sh &

./setup_deepseek_llm_inference.sh

bash watchdog.sh &

wait
