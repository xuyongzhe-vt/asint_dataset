count=0
start_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "🚀 Safety Watchdog started at $start_time"

while true; do
    util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits \
           | awk '{sum+=$1; n++} END{if(n>0) print int(sum/n); else print 0}')

    if [[ $util -lt 10 ]]; then
        ((count++))
        echo "[$(date +"%H:%M:%S")] Low utilization (${util}%) count=$count"
        if [[ $count -gt 400 ]]; then   # 80 × 15s = ~20 minutes
            end_time=$(date +"%Y-%m-%d %H:%M:%S")
            echo "⚠️ GPU idle for >20 minutes on average, cancelling job $SLURM_JOB_ID"
            echo "🛑 Safety Watchdog ending at $end_time"
            scancel $SLURM_JOB_ID
            exit 0
        fi
    else
        count=0
        echo "[$(date +"%H:%M:%S")] Utilization OK (avg ${util}%)"
    fi
    sleep 15
done
