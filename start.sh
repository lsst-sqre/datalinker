#!/bin/bash -ex
rm -rf /tmp/secrets
cp -RL /etc/butler/secrets /tmp
chmod -R 0400 /tmp/secrets/*

uvicorn datalinker.main:app --host 0.0.0.0 --port 8080
