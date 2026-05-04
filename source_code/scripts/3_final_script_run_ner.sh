SCRIPT_PATH="$(dirname "$0")/../clean_html.py"

ssh -T ${REMOTE_CRAWL_HOST} <<'EOF'
    echo "Compressing with tar + gzip (single-threaded)..."
    cd ${BASE_DIR}/crawling/htmls/ || exit
    tar -czf ${BASE_DIR}/crawling/crawl_remote.tar.gz .
EOF

scp ${REMOTE_CRAWL_HOST}:${BASE_DIR}/crawling/crawl_remote.tar.gz ${LOCAL_CRAWL_HOST}:${BASE_DIR}/crawling/

tar -xzf ${BASE_DIR}/crawling/crawl_remote.tar.gz -C ${BASE_DIR}/crawling/htmls/

echo "Cleaning htmls"
if ! python3 "$SCRIPT_PATH"; then
    echo "Error: clean_html.py failed" >&2
    exit 1
fi

cd ${BASE_DIR}/crawling/cleaned_content/
tar -czf ${BASE_DIR}/crawling/cleaned_htmls.tar.gz .

echo "run ner on remote HPC"
cp ${BASE_DIR}/crawling/cleaned_htmls.tar.gz ${ENTRY_STAGE_DIR}/
cp ${BASE_DIR}/output/org.json ${ENTRY_STAGE_DIR}/

screen -S llm_server -X stuff $'bash ${REMOTE_NER_HOME}/prepare_data.sh\r'
