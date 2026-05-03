echo "copy zip from ARC"
screen -S llm_server -X stuff $'bash ${REMOTE_NER_HOME}/post_process.sh \n echo SCRIPT_DONE\n'

while ! screen -S llm_server -X hardcopy /tmp/screen_llm.log; do sleep 1; done

while ! grep -q "SCRIPT_DONE" /tmp/screen_llm.log; do
    sleep 1
    screen -S llm_server -X hardcopy /tmp/screen_llm.log
done

cp ${ENTRY_STAGE_DIR}/ner.tar.gz ${BASE_DIR}/

rm -rf ${BASE_DIR}/llm
mkdir ${BASE_DIR}/llm
mkdir ${BASE_DIR}/llm/classification
mkdir ${BASE_DIR}/llm/classification/output
mkdir ${BASE_DIR}/llm/classification/unfinished

tar -xzf ${BASE_DIR}/ner.tar.gz -C ${BASE_DIR}/llm/classification/unfinished

./run_index_lkb.sh

echo "run llm classification"


screen -S llm_server -X stuff "cd ${REMOTE_LLM_HOME}/ && sbatch ${REMOTE_LLM_HOME}/llm_batch_job_llm_inference.sh\n"
./run_llm_classification.sh

echo "run clustering"
./run_pre_cluster.sh
