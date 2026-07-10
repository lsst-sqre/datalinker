# datalinker

datalinker provides various facilities for discovering and referring to data products and services within the Rubin Science Platform.
It is deployed via [Phalanx](https://phalanx.lsst.io/) and depends on other Phalanx services such as [Gafaelfawr](https://gafaelfawr.lsst.io/) for authentication.

The API provided by datalinker is primarily based on the IVOA DataLink standard, but it also provides some related service discovery facilities beyond the scope of that standard.

- Implements a "links" endpoint, providing a variety of file and service links given an ID for an image in the RSP image services.
  This endpoint is the target of the `access_url` column in the RSP ObsTAP service.

- Implements a variety of "microservice" endpoints to be used as the targets of DataLink service descriptors, many of which will rewrite simple service-descriptor-friendly URL APIs into more complicated queries to a back end.
  Some of these will be associated with entries in the tables from the "links" endpoint for images; some will be used with service descriptors in catalog query results.
  These endpoints will eventually be moved to a different service.

datalinker implements [version 1.1 of the IVOA DataLink standard](https://www.ivoa.net/documents/DataLink/20231215/REC-DataLink-1.1.html) with the following known exceptions:

- Service errors preventing a response are formatted as JSON rather than as VOTables.

datalinker is developed with the [Safir](https://safir.lsst.io) framework.
