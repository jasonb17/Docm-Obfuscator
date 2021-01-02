# docm_obfuscator
https://arielkoren.com/blog/2020/12/24/forging-malicious-doc/

Current progress: All 3 techniques implemented + combinations
API server code added

## Usage

### Run Script Directly

```
docmobfuscator.py <in_file> <obfuscation_technique>

in_file must be .docm or .zip
obfuscation_techniques: buffer_collapse, ghost_file, invalid_header, invalid_plus_buffer, invalid_plus_ghost
```

### API Server

```
server.py

Starts API server that will listen to GET/POST in below format
```

### POST - Send doc/zip for obfuscation

Request:
```
POST / HTTP/1.1
Host: localhost.:8000
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Content-Type: multipart/form-data; boundary=---------------------------4907851351774763772443316270
Content-Length: 16409
Origin: http://localhost.:8000
Connection: close
Referer: http://localhost.:8000/
Upgrade-Insecure-Requests: 1

-----------------------------4907851351774763772443316270
Content-Disposition: form-data; name="cname"

obfuscated_doc.docm
-----------------------------4907851351774763772443316270
Content-Disposition: form-data; name="obfuscation"

invalid_plus_buffer
-----------------------------4907851351774763772443316270
Content-Disposition: form-data; name="file"; filename="bad_doc.docm"
Content-Type: application/vnd.ms-word.document.macroEnabled.12

PK... zip file content...
...
-----------------------------4907851351774763772443316270--
```

Response:
```
HTTP/1.0 200 File obfuscated_doc.docm uploaded successfully with invalid_plus_buffer obfuscation applied
Server: BaseHTTP/0.6 Python/3.7.3
Date: Sat, 02 Jan 2021 18:06:05 GMT
```

### GET - Retrieve Obfuscated doc/zip

```
GET /obfuscated_doc.docm HTTP/1.1
Host: localhost.:8000
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Connection: close
Upgrade-Insecure-Requests: 1
```
