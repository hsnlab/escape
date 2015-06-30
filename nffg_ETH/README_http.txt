This example realizes the communication described in ../README_nffglib.txt over a HTTP channel.

"get-config" is realized as a POST http request to "http://hostip:8080/get-config" with an empty body. The response body contains the description of the infrastructure in xml.

"edit-config" is realized as a POST http request to "http://hostip:8080/edit-config" with the requested configuration in the request body encoded in xml. The response is a non-error code.
