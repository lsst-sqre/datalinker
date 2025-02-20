#!/bin/bash -ex

if [ -n "$DATALINKER_TAP_METADATA_URL" ]; then
    if [ -z "$DATALINKER_TAP_METADATA_DIR" ]; then
        echo 'DATALINKER_TAP_METADATA_DIR must be specified' >&2
        exit 1
    fi
    curl -L "$DATALINKER_TAP_METADATA_URL" -o /tmp/datalink-columns.zip
    unzip -o /tmp/datalink-columns.zip -d "$DATALINKER_TAP_METADATA_DIR"
fi

uvicorn datalinker.main:app --host 0.0.0.0 --port 8080
