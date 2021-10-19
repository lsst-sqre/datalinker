#!/bin/bash -ex
if [ -f dev-chart.tgz ]
then
  CHART=dev-chart.tgz
else
  CHART=lsst-sqre/datalinker
fi

helm delete datalinker -n datalinker || true
docker build -t lsstsqre/datalinker:dev .
helm upgrade --install datalinker $CHART --create-namespace --namespace datalinker --values dev-values.yaml
