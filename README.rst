##########
datalinker
##########

Provides two capabilities for the Rubin Science Platform based on the IVOA DataLink standard:

- Implements a "links" endpoint, providing a variety of file and service links given an ID
  for an image in the RSP image services.  This endpoint is the target of the ``access_url``
  column in the RSP ObsTAP service.

- Implements a variety of "microservice" endpoints to be used as the targets of DataLink
  service descriptors, many of which will rewrite simple service-descriptor-friendly
  URL APIs into more complicated queries to a back end.  Some of these will be associated
  with entries in the tables from the "links" endpoint for images; some will be used with
  service descriptors in catalog query results.

datalinker is developed with the `Safir <https://safir.lsst.io>`__ framework.
`Get started with development with the tutorial <https://safir.lsst.io/set-up-from-template.html>`__.
