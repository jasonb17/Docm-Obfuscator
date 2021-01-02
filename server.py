#!/usr/bin/env python3

"""Simple HTTP handler to handle POST and GET requests to the obfuscator.

Based on https://gist.github.com/UniIsland/3346170
"""

import os
import posixpath
import http.server
import urllib.request, urllib.parse, urllib.error
import html
import shutil
import mimetypes
import re
import docmobfuscator
from io import BytesIO


class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP request handler with GET/HEAD/POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can reveive file uploaded
    by client.

    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.

    """

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()


    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()


    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print((r, info, "by: ", self.client_address))
        if r == True:
            self.send_response(200, info)
        else:
            self.send_response(400, info)
        self.end_headers()


    def deal_post_data(self):
        content_type = self.headers['content-type']
        if not content_type:
            return (False, "Content-Type header doesn't contain boundary")
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])

        # get the custom filename, if passed
        line = self.rfile.readline()
        remainbytes -= len(line)
        if not boundary in line:
            return (False, "A boundary in Content is missing or incorrect")
        line = self.rfile.readline()
        remainbytes -= len(line)
        path = self.translate_path(self.path)

        # Check if a custom filename was passed
        target_name = ''
        filename_only = ''
        if re.findall(r'Content-Disposition.*name="cname"', line.decode()):
            line = self.rfile.readline()
            remainbytes -= len(line)
            line = self.rfile.readline()
            remainbytes -= len(line)
            line = line[:-1] #strip \n
            if line.endswith(b'\r'):
                line = line[:-1]
            target_name = os.path.join(path,line.decode())
            filename_only = line.decode()
            line = self.rfile.readline()
            remainbytes -= len(line)
            if not boundary in line:
                return (False, "A boundary in Content is missing or incorrect")
            line = self.rfile.readline()
            remainbytes -= len(line)

        # Check if an obfuscation technique was passed
        obfuscation = ''
        if re.findall(r'Content-Disposition.*name="obfuscation"', line.decode()):
            line = self.rfile.readline()
            remainbytes -= len(line)
            line = self.rfile.readline()
            remainbytes -= len(line)
            line = line[:-1] #strip \n
            if line.endswith(b'\r'):
                line = line[:-1]
            if line.decode() in ['buffer_collapse', 'ghost_file', 'invalid_header', 'invalid_plus_buffer', 'invalid_plus_ghost']:
                obfuscation = line.decode()
            line = self.rfile.readline()
            remainbytes -= len(line)
            if not boundary in line:
                return (False, "A boundary in Content is missing or incorrect")
            line = self.rfile.readline()
            remainbytes -= len(line)

        # Read in actual filename
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode())
        if not fn:
            return (False, "Can't determine file name")
        file_ext = os.path.splitext(fn[0])[1]
        if file_ext not in ['.zip', '.docm']:
            return (False, "File must be .zip or .docm")
        if target_name == '':
            target_name = os.path.join(path,fn[0])
            filename_only = fn[0]
        else:
            if os.path.splitext(target_name)[1] == '':
                target_name += file_ext
                filename_only += file_ext
        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)
        try:
            out = open(target_name, 'wb')
        except IOError:
            return (False, "Can't create file to write, do you have permission to write?")

        # Read in file content
        preline = self.rfile.readline()
        remainbytes -= len(preline)
        clean_end = False
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[:-1]
                if preline.endswith(b'\r'):
                    preline = preline[:-1]
                out.write(preline)
                out.close()
                clean_end = True
                break
            else:
                out.write(preline)
                preline = line
        if clean_end == False:
            return (False, "Unexpected end of data.")

        # Apply obfuscation if specified
        if obfuscation == '':
            return (True, "File {0} uploaded successfully with no obfuscation applied".format(filename_only))
        else:
            docmobfuscator.obfuscate(target_name, obfuscation)
            return (True, "File {0} uploaded successfully with {1} obfuscation applied".format(filename_only, obfuscation))


    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            else:
                return self.upload_page(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f


    def upload_page(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = BytesIO()
        displaypath = html.escape(urllib.parse.unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<label for=\"cname\">Custom file name:</label>")
        f.write(b"<p><input type=\"text\" id=\"cname\" name=\"cname\"></p>")
        f.write(b"<label for=\"obfuscation\">Obfuscation technique:</label>")
        f.write(b"<p><select id=\"obfuscation\" name=\"obfuscation\">")
        #obfuscation_techniques: buffer_collapse, ghost_file, invalid_header, invalid_plus_buffer, invalid_plus_ghost
        f.write(b"<option value=\"buffer_collapse\">buffer_collapse</option>")
        f.write(b"<option value=\"ghost_file\">ghost_file</option>")
        f.write(b"<option value=\"invalid_header\">invalid_header</option>")
        f.write(b"<option value=\"invalid_plus_buffer\">invalid_plus_buffer</option>")
        f.write(b"<option value=\"invalid_plus_ghost\">invalid_plus_ghost</option>")
        f.write(b"<option value=\"none\">None</option>")
        f.write(b"</select></p>")
        f.write(b"<input name=\"file\" type=\"file\"/>")
        f.write(b"<p><input type=\"submit\" value=\"upload\"/></form></p>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f


    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path


    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)


    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    })


def start(HandlerClass=SimpleHTTPRequestHandler,
         ServerClass=http.server.HTTPServer):
    http.server.test(HandlerClass, ServerClass)


if __name__ == "__main__":
    start()