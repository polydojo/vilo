"""
Vilo: Simple, unopinionated Python web framework.

Copyright (c) 2020 Polydojo, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
""";

import os;
import sys;
import json;
import re;
import io;
import functools;
import urllib.parse;
import http.cookies;
import mimetypes;
import cgi;
import traceback;
import hashlib;
import hmac;
import base64;
import pprint;

import dotsi;

__version__ = "0.0.3";  # Req'd by flit.

############################################################
# Helpers & Miscellaneous: #################################
############################################################

httpCodeLineMap = {
    200: "200 OK",
    301: "301 Moved Permanently",
    302: "302 Found",
    303: "303 See Other",
    304: "304 Not Modified",
    400: "400 Bad Request",
    401: "401 Unauthorized",
    402: "402 Payment Required",
    403: "403 Forbidden",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    408: "408 Request Timeout",
    410: "410 Gone",
    413: "413 Payload Too Large",
    418: "418 I'm a teapot",
    429: "429 Too Many Requests",
    431: "431 Request Header Fields Too Large",
    500: "500 Internal Server Error",
    503: "503 Service Unavailable",
};

def getStatusLineFromCode (code):
    return httpCodeLineMap.get(code) or "404 Not Found";

class HttpError (Exception):
    def __init__ (self, body, statusLine=404, viloTag=None):
        self.body = body;
        self.statusLine = (statusLine
            if type(statusLine) is not int
            else getStatusLineFromCode(statusLine)#,                        # no-comma-avoid-tuple
        );
        self.viloTag = viloTag;
error = HttpError;


KB = 1024;
MB = KB**2;
MAX_REQUEST_BODY_SIZE = 1 * MB; # TODO: Make configurable.

mapli = lambda seq, fn: list(map(fn, seq));
filterli = lambda seq, fn: list(filter(fn, seq));

esc = lambda s: (str(s).replace("&", "&amp;")
    .replace(">", "&gt;").replace("<", "&lt;")
    .replace('"', "&quot;").replace("'", "&#039;")
);

def dictDefaults (dicty, defaults):
    for k in defaults:
        if k not in dicty:
            dicty[k] = defaults[k];
    return None;

def escfmt (string, seq):
    if isinstance(seq, (str, float, int, type(None), bool)):
        seq = [seq];
    if isinstance(seq, (list, tuple)):
        return string % tuple(mapli(seq, esc));
    if isinstance(seq, dict):
        dct = {};
        for (k, v) in seq.items():
            dct[str(k)] = esc(str(v));
        return string % dct;

# String encoding and cookie-signing related: ::::::::::::::

def toBytes (x, enc="utf8"):
    if type(x) is bytes: return x;
    if type(x) is str: return x.encode(enc);
    raise TypeError("Expected `str` (or `bytes`), not `%s`" % (type(x),));

def toStr (x, enc="utf8"):
    if type(x) is str: return x;
    if type(x) is bytes: return x.decode(enc);
    raise TypeError("Expected `bytes` (or `str`), not `%s`" % (type(x),));

def latin1_to_utf8 (s):
    "Useful for consuing request headers.";
    assert type(s) is str;  # str i/p, str o/p.
    return s.encode("latin1").decode("utf8");

def utf8_to_latin1 (s):
    "Useful for producing response headers.";
    assert type(s) is str;  # str i/p, str o/p.
    return s.encode("utf8").decode("latin1");

def hmacy (b_msg, b_secret, digestmod=hashlib.sha512):
    assert type(b_msg) is bytes and type(b_secret) is bytes;
    return hmac.HMAC(b_secret, b_msg, digestmod).digest();    

B_SIGN_SEP = b"@|";  # SIGNing SEParator, of type `bytes`.

def signWrap (value, secret):
    b_jval = toBytes(json.dumps(value));
    b_secret = toBytes(secret);
    b_sig = hmacy(b_jval, b_secret);
    b64_jval = base64.b64encode(b_jval);
    b64_sig = base64.b64encode(b_sig);
    assert type(b64_sig) is bytes and B_SIGN_SEP not in b64_sig;
    b_signed = b64_sig + B_SIGN_SEP + b64_jval;
    return toStr(b_signed);

def signUnwrap (signed, secret):
    if not (type(signed) is str and toStr(B_SIGN_SEP) in signed):
        return None;
    # otherwise ...
    b_secret = toBytes(secret)
    b_signed = toBytes(signed);
    b64_sig, b64_jval = b_signed.split(B_SIGN_SEP, 1);
    b_jval = base64.b64decode(b64_jval);
    b_sig = base64.b64decode(b64_sig);
    b_sigComputed = hmacy(b_jval, b_secret);
    if b_sig != b_sigComputed:
        return None;
    # otherwise ...
    return json.loads(toStr(b_jval));

def test_signWrap (value, secret):
    assert signUnwrap(signWrap(value, secret), secret) == value;

############################################################
# Request: #################################################
############################################################

def buildRequest (environ):
    req = dotsi.fy({});
    
    req.getEnviron = lambda: environ;
    
    def ekey (key, default=None):
        # Utf8-friendly wrapper around environ.
        if key not in environ: return default;
        return latin1_to_utf8(environ[key]);
        ##Consider::
        #value = environ[key];
        #if value is str: return latin1_to_utf8(value);
        #return value;
    req._ekey = ekey;
    
    req.getPathInfo = lambda: ekey("PATH_INFO", "/");
    req.getVerb = lambda: ekey("REQUEST_METHOD", "GET").upper();
    req.wildcards = [];
    req.matched = None;
    req.cookieJar = http.cookies.SimpleCookie(ekey("HTTP_COOKIE", ""));
    
    req.app = None;
    req.response = None;
    def bindApp (app, response):
        req.app = app;
        req.response = response;
    req.bindApp = bindApp;
    
    req.bodyBytes = b"";
    def fillBody ():
        fileLike = environ["wsgi.input"]; # Not ekey(.)
        req.bodyBytes = fileLike.read(MAX_REQUEST_BODY_SIZE);
        assert type(req.bodyBytes) is bytes;
        if fileLike.read(1) != b"":
            raise HttpError("<h2>Request Too Large</h2>", 413, "requestTooLarge");
    fillBody(); # Immediately called.
    
    req.url = "";
    req.splitUrl = urllib.parse.urlsplit("");
    def reconstructUrl ():
        # Scheme:
        scheme = ekey("wsgi.url_scheme", "http");
        # Netloc:
        netloc = ekey("HTTP_HOST");
        if not netloc:
            netloc = ekey("SERVER_NAME");
            port = ekey("SERVER_PORT");
            if port and port != ("80" if scheme == "http" else "443"):
                netloc = netloc + ":" + port;
        # Path:
        path = (    # ? urllib.parse.un/quot() ?
            ekey("SCRIPT_NAME", "")  + ekey("PATH_INFO", "")
        );
        # Query:
        query = ekey("QUERY_STRING", "")
        # Fragment:
        fragment = "";
        # Full URL:
        req.splitUrl = urllib.parse.SplitResult(
            scheme, netloc, path, query, fragment,
        );
        #print("type(req.splitUrl) = ", type(req.splitUrl));
        #print("(req.splitUrl) = ", (req.splitUrl));
        req.url = req.splitUrl.geturl();
    reconstructUrl();   # Immediately called.
    
    def getHeader (name):
        cgikey = name.upper().replace("-", "_");
        if cgikey not in ["CONTENT_TYPE", "CONTENT_LENGTH"]:
            cgikey = "HTTP_" + cgikey;
        return ekey(cgikey);
    req.getHeader = getHeader;
    req.contentType = getHeader("CONTENT_TYPE");
    
    def parseQs (qs):
        "Parses query string into dict.";
        return dict(urllib.parse.parse_qsl(qs, keep_blank_values=True));    # parse_qsl(.) returns list of 2-tuples, then dict-ify
    req.qdata = parseQs(req.splitUrl.query);    # IMMEDIATE.
    
    
    def helper_parseMultipartFormData ():
        assert req.contentType.startswith("multipart/form-data");
        parsedData = {};
        miniEnviron = {
            # Not ekey(.), use environ.get(.) directly:
            "QUERY_STRING": environ.get("QUERY_STRING"),
            "REQUEST_METHOD": environ.get("REQUEST_METHOD"),
            "CONTENT_TYPE": environ.get("CONTENT_TYPE"),
            "CONTENT_LENGTH": len(req.bodyBytes),
        };
        fieldData = cgi.FieldStorage(
            fp = io.BytesIO(req.bodyBytes),
            environ = miniEnviron, encoding = "utf8",
            keep_blank_values = True,
        );
        fieldList = fieldData.list or [];
        for field in fieldList:
            if field.filename:
                parsedData[field.name] = {
                    "filename": field.filename,
                    "bytes": field.file.read(),
                    "mimeType": field.headers.get_content_type(),       # TODO: Investigate if this includes charset.
                    #?"charset": field.headers.get_charset(),
                    #?"headers": field.headers,
                };
            else:
                parsedData[field.name] = field.value;
        return parsedData;
    
    req.fdata = {};
    def fill_fdata ():
        if not req.contentType:
            pass;   # Falsy contentType, ignore.
        elif req.contentType == "application/x-www-form-urlencoded":
            req.fdata = parseQs(req.bodyBytes.decode("latin1"));        # "utf8" doesn't seem to work. "latin1" does?!?
        elif req.contentType == "application/json":
            req.fdata = json.loads(req.bodyBytes);
        elif req.contentType.startswith("multipart/form-data"):
            req.fdata = helper_parseMultipartFormData();
        else:
            pass;   # Other contentType, ignore.
    fill_fdata();       # Immediately called.

    def getUnsignedCookie (name):
        morsel = req.cookieJar.get(name);
        return morsel.value if morsel else None;
    req.getUnsignedCookie = getUnsignedCookie;
    
    def getCookie (name, secret=None):
        uVal = getUnsignedCookie(name); # Unsigned-ready val.
        if not uVal: return None;
        if not secret: return uVal;
        return signUnwrap(uVal, secret);
    req.getCookie = getCookie;

    # Return built `req`:
    return req;

############################################################
# Response: ################################################
############################################################

def buildResponse (start_response):
    res = dotsi.fy({});
    res.statusLine = "200 OK";
    res.contentType = "text/html; charset=UTF-8";
    res._headerMap = {};
    res.cookieJar = http.cookies.SimpleCookie();
    #res._bOutput = b"";
   
    res.update({"app": None, "request": None});
    def bindApp (appObject, reqObject):
        res.update({"app": appObject, "request": reqObject});
    res.bindApp = bindApp;
    
    def setHeader (name, value):
        name = name.strip().upper();
        if name == "CONTENT-TYPE":
            res.contentType = value;
        elif name == "CONTENT-LENGTH":
            raise Exception("The Content-Length header will be automatically set.");
        else:
            res._headerMap[name] = value;
    res.setHeader = setHeader;
    
    def getHeader (name):
        return res._headerMap.get(name.strip().upper());
    res.getHeader = getHeader;
    
    def setHeaders (headerList):
        if type(headerList) is dict:
            headerList = list(headerList.items());
        assert type(headerList) is list;
        mapli(headerList, lambda pair: setHeader(*pair));
    res.setHeaders = setHeaders;
    
    def setUnsignedCookie (name, value, opt=None):
        assert type(value) is str;
        res.cookieJar[name] = value;
        morsel = res.cookieJar[name]
        assert type(morsel) is http.cookies.Morsel;
        opt = opt or {};
        dictDefaults(opt, {
            "path": "/", "httponly": True, #"secure": True,
        });
        for optKey, optVal in opt.items():
            morsel[optKey] = optVal;
        return value;   # `return` helps w/ testing.
    res.setUnsignedCookie = setUnsignedCookie;

    def setCookie (name, value, secret=None, opt=None):
        uVal = signWrap(value, secret) if secret else value;    # Unsigned-ready val.
        setUnsignedCookie(name, uVal, opt);
        return uVal;    # `return` helps w/ testing.
    res.setCookie = setCookie;
    
    #def getCookie (name, value):
    #    pass; # ??? For getting just-res-set cookies.
    #res.getCookie = getCookie;
    
    def staticFile (filepath, mimeType=None):
        if not mimeType:
            mimeType, encoding = mimetypes.guess_type(filepath);
            mimeType = mimeType or  "application/octet-stream";
        try:
            with open(filepath, "rb") as f:
                res.contentType = mimeType;
                return f.read();
        except FileNotFoundError:
            raise HttpError("<h2>File Not Found<h2>", 404, "fileNotFound");
    res.staticFile = staticFile;
    
    def redirect (url):
        res.statusLine = "302 Found";                       # Better to use '303 See Other' for HTTP/1.1 environ['SERVER_PROTOCOL']
        res.setHeader("Location", url);                     # but 302 is backward compataible, and doesn't need access to req object.
        return b"";
    res.redirect = redirect;

    
    def _bytify (x):
        if type(x) is str:
            return x.encode("utf8");
        if type(x) is bytes:
            return x;
        if isinstance(x, (dict, list)):
            res.contentType = "application/json";
            return json.dumps(x).encode("utf8");            # ? latin1 ?
        # otherwise ...
        return str(x).encode("utf8");
    
    def _finish (handlerOut):
        bBody = _bytify(handlerOut);
        headerList = (
            list(res._headerMap.items()) +
            mapli(
                res.cookieJar.values(),            
                lambda m: ("SET-COOKIE", m.OutputString()),
            ) +
            list({
                "CONTENT-TYPE": res.contentType,
                "CONTENT-LENGTH": str(len(bBody)),
            }.items()) #+
        );
        #print("res.statusLine = ", res.statusLine);
        #pprint.pprint(headerList);
        latin1_headerList = [];
        for (name, value) in headerList:
            latin1_headerList.append((name, utf8_to_latin1(value)));
        #pprint.pprint(latin1_headerList);
        start_response(
            utf8_to_latin1(res.statusLine), latin1_headerList,
        );
        return [bBody];
    res._finish = _finish;
    
    # Return built `res`:
    return res;

############################################################
# Routing: #################################################
############################################################

def detectRouteMode (route_path):
    "Auto-detects routing mode from `route_path`.";
    if "(" in route_path and ")" in route_path: return "re";
    if "*" in route_path: return "wildcard";
    return "exact";

def validateWildcardPath (wPath):
    assert "*" in wPath;
    if wPath.startswith("*"):
        raise SyntaxError("WildcardError:: Path can't being with '*'.");
    wSegLi = wPath.split("/");
    for wSeg in wSegLi[:-1]:
        if ("*" in wSeg) and (wSeg != "*"):
            raise SyntaxError("WildcardError:: Non-trailing '*' must span entire segment.");
    # otherwise ...
    lwSeg = wSegLi[-1];     # Last wSeg
    if ("*" in lwSeg) and (lwSeg not in ["*", "**"]):
        raise SyntaxError("WildcardError:: Invalid trailing wildcard, must be '*' or '**'.");
    # otherwise ...
    return True;

def buildRoute(verb, path, fn, mode=None, name=None):
    verb = [verb] if type(verb) is str else verb;
    mode = detectRouteMode(path) if not mode else mode;
    assert mode in ["re", "wildcard", "exact"];
    if mode == "wildcard":
        assert validateWildcardPath(path);
    return dotsi.fy({
        "verb": verb,  "path": path,  "fn": fn,
        "mode": mode,  "name": name,
    });

def checkWildcardMatch (wPath, aPath, req):
    # 1. Prelims:
    wildcards = [];
    wSlashCount = wPath.count("/");
    aSegLi = aPath.split("/", wSlashCount);
    wSegLi = wPath.split("/", wSlashCount);
    if len(aSegLi) != len(wSegLi):
        return False;
    # 
    # 2. Match non-last segment:
    for (aSeg, wSeg) in zip(aSegLi[ : -1], wSegLi[ : -1]):
        assert (wSeg == "*") or ("*" not in wSeg);
        assert "/" not in aSeg;
        if wSeg == "*":
            wildcards.append(aSeg);
        elif wSeg != aSeg:
            return False;
    
    # 3. Match last segment or multi-segment:
    laSeg, lwSeg = aSegLi[-1], wSegLi[-1];
    assert (lwSeg == "*") or (lwSeg == "**") or ("*" not in lwSeg);
    if lwSeg == "*":
        if "/" in laSeg:
            return False;
        else:
            wildcards.append(laSeg);
    elif lwSeg == "**":
        wildcards.append(laSeg);
    elif wSeg != aSeg:
        return False;
    #
    # 4. Finish:
    req.wildcards = wildcards;
    return True;

def checkReMatch (rePath, aPath, req):
    m = re.match(rePath, aPath);
    if not m:
        return False;
    # otherwise ...
    req.matched = m;
    return True;

def checkRouteMatch (route, req):
    #print("Checking route: ", route);
    aPath = req.getPathInfo();  # Actual Path
    if route.mode == "exact":
        return route.path == aPath;
    if route.mode == "wildcard":
        return checkWildcardMatch(route.path, aPath, req);
    return checkReMatch(route.path, aPath, req);

############################################################
# App: #####################################################
############################################################
    

def buildApp ():
    app = dotsi.fy({});
    app.routeList = [];
    app.pluginList = [];
    
    def addRoute(verb, path, fn, mode=None, name=None):
        "Add a route handler `fn` against `path`, for `verb`.";
        route = buildRoute(verb, path, fn, mode, name);
        app.routeList.append(route);
    app.addRoute = addRoute;
            
    def route (verb, path, mode=None, name=None):
        "Decorator for adding routes.";
        def identityDecorator (fn):
            addRoute(verb, path, fn, mode, name);
            return fn;
        return identityDecorator;
    app.route = route;
    
    def install (plugin):
        app.pluginList.append(plugin);
    app.install = install;
    
    def plugRoute (matchedRoute):
        pfn = matchedRoute.fn;  # pfn: Plugged fn.
        for plugin in app.pluginList:
            pfn = plugin(pfn);  # Apply each plugin.
        return pfn;

    
    def mkDefault_viloErrTag_handler (code, msg=None):
        statusLine = getStatusLineFromCode(code);
        def defaultErrorHandler (xReq, xRes, xErr):
            if xReq.contentType == "application/json":
                return  {"status": statusLine, "msg": msg};
            # otherwise ...
            return escfmt("<h2>%s</h2><pre>%s</pre>", [statusLine, msg]);
        return defaultErrorHandler;
    
    app.inDebugMode = False;
    def setDebug (boolean):
        app.inDebugMode = bool(boolean);
    app.setDebug = setDebug;

    def default_viloErrTag_handler_unexpectedError (xReq, xRes, xErr):
        print();
        traceback.print_exc();
        print();
        if not app.inDebugMode:
            return "<h2>500 Internal Server Error</h2>";
        # otherwise ...
        return escfmt("""
            <h2>500 Internal Server Error</h2>
            <hr>
            <h3>Traceback</h3>
            <pre>%s</pre>
        """, traceback.format_exc());
        
    
    app.viloErrorTagMap = {
        "routeNotFound": mkDefault_viloErrTag_handler(404, "No such route."),
        "fileNotFound": mkDefault_viloErrTag_handler(404, "No such file."),
        "requestTooLarge": mkDefault_viloErrTag_handler(413, "Request too large."),
        "unexpectedError": default_viloErrTag_handler_unexpectedError,
    };
    def decorator_supply_viloErrorTagHandler (viloTag):
        if viloTag not in app.viloErrorTagMap:
            raise KeyError(viloTag);
        def identityDecorator (oFunc):
            app.viloErrorTagMap[viloTag] = oFunc;
            return oFunc;
        return identityDecorator;
    app.onViloErrorTag = decorator_supply_viloErrorTagHandler;        
    
    def getMatchingRoute (req):
        reqVerb = req.getVerb();
        reqPath = req.getPathInfo();
        
        verbMatch = lambda rt: (
            (type(rt.verb) is str and reqVerb == rt.verb) or
            (type(rt.verb) is list and reqVerb in rt.verb) #or
        );
        for rt in app.routeList:
            if reqVerb in rt.verb and checkRouteMatch(rt, req):
                return rt;
        # otherwise ..
        raise HttpError("<h2>Route Not Found</h2>", 404, "routeNotFound");
    
    def wsgi (environ, start_response):
        #pprint.pprint(environ);
        #wsgiInput = environ["wsgi.input"];
        #print('type(wsgiInput) =', type(wsgiInput));
        #print("wsgiInput =", wsgiInput);
        #print(dir(wsgiInput));
        req = buildRequest(environ);
        res = buildResponse(start_response);
        req.bindApp(app, res);
        res.bindApp(app, req);
        #print(req.bodyBytes);
        try:
            mRoute = getMatchingRoute(req);
            pfn = plugRoute(mRoute);
            handlerOut = pfn(req, res);
        except HttpError as e:
            res.statusLine = e.statusLine;
            if e.viloTag in app.viloErrorTagMap:
                efn = app.viloErrorTagMap[e.viloTag];       # <-- TODO: Consider plugin application? (Leaning toward 'No'.)
                handlerOut = efn(req, res, e);
            else:            
                handlerOut = e.body;
        except Exception as orgErr:
            #stacktrace = traceback.format_exc();
            #print(stacktrace);
            httpErr = HttpError("<h2>Internal Server Error</h2>", 500, "unexpectedError");
            efn = app.viloErrorTagMap[httpErr.viloTag];     # <-- TODO: Consider plugin application? (Leaning toward 'No'.)
            handlerOut = efn(req, res, orgErr);
        return res._finish(handlerOut);
    app.wsgi = wsgi;
    
    # Return built `app`:
    return app;

# End ######################################################
