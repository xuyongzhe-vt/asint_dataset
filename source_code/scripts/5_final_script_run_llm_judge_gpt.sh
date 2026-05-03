mkdir -p ${BASE_DIR}/llm/re-evaluation/alias_judge
mkdir -p ${BASE_DIR}/llm/re-evaluation/parent_judge

echo "run re-eva"
screen -S llm_server -X stuff "cd ${REMOTE_LLM_HOME}/ && sbatch ${REMOTE_LLM_HOME}/llm_batch_job.sh \n"
./run_re_eva.sh
