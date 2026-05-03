cd ${NER_WORK_DIR}/output
rm ${NER_WORK_DIR}/ner.tar.gz
tar -czf ${NER_WORK_DIR}/ner.tar.gz .
scp ${NER_WORK_DIR}/ner.tar.gz ${ENTRY_HOST}:${ENTRY_STAGE_DIR}
