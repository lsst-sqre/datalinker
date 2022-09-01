#!/bin/bash -ex

if [ -n "$DATALINKER_TAP_METADATA_URL" ]; then
    if [ -z "$DATALINKER_TAP_METADATA_DIR" ]; then
        echo 'DATAlINKER_TAP_METADATA_DIR must be specified' >&2
        exit 1
    fi
    curl -L "$DATALINKER_TAP_METADATA_URL" -o /tmp/datalink-columns.zip
    unzip /tmp/datalink-columns.zip -d "$DATALINKER_TAP_METADATA_DIR"
fi

rm -rf /tmp/secrets
cp -RL /etc/butler/secrets /tmp
chmod -R 0400 /tmp/secrets/*

uvicorn datalinker.main:app --host 0.0.0.0 --port 8080
