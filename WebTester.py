import ssl
import socket
import re
import sys

"""
CSC 361 Assignment 1 
Build a tool that collect information regarding a web server
"""
PASS_PRO = False # whether it is password protected or not 

def https_connect(host):
    #create the socket using ssl and alpn for https requests
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()
        context.set_alpn_protocols(['http/1.1'])
    
        ssl_sock = context.wrap_socket(sock, server_hostname=host)
 
    except Exception as e:
        print(e)
        sys.exit("Error creating socket")

    try:
        ssl_sock.connect((host, 443))
    except Exception as e:
        print(e)
        sys.exit("Error connecting to server")
        
    return ssl_sock


def http_connect(host):
    #create the socket for http requests
    try: 
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except Exception as e:
        print(e)
        sys.exit(1)
    try:
        sock.connect((host, 80))
    except Exception as e:
        print(e)
        sys.exit(1)

    return sock

def send_req(sock, host, path):
    #send the http or https requests through their respective sockets. Allows for redirect requests

    global PASS_PRO
    print("---Request Begin---\n")
    try:
        http_req = (
            "GET /{} HTTP/1.1\r\n"
            "HOST: {}\r\n"
            "Connection: Keep-Alive\r\n\r\n"
        ).format(path, host)
        sock.sendall(http_req.encode())
    except Exception as e:
        print(e)
        sys.exit(1)

    print(http_req) #only for debugging 
    print("---Request End---\n")
    print("HTTP request sent, waiting for response... \n\n")

    http_resp = b""
    redirect = False # if a redirect is necessary var 

    while True:
        
        chunk = sock.recv(1024)
        if not chunk:
            break
        # if either 302 or 301 redirect requests appear in the response
        if(b"302" in chunk or b"301" in chunk):
            redirect = True

        http_resp += chunk

        if b"\r\n\r\n" in chunk:
            break

    print("---Response Header---")
   # print(http_resp.decode()) # this is only for debugging take out when submitting 
    print("---Response End---\n")
    
    if(redirect):
        #find the new uri from the response
        resp_lines = http_resp.decode('utf-8', 'ignore').splitlines()
        location = [line for line in resp_lines if 'Location:' in line]
        
        if(location):
            
            location_red = location[0].split('://')
          #  print(location_red)
            new_location, new_path = parse_uri(location_red[1])
            print("Redirecting to: " + new_location + "\n")

            # open new socket of redirecting from http to https
            if "https" in location_red[0] and sock.getpeername()[1] == 80:
                port = 443
                sock.close()
                new_sock = https_connect(new_location)
                send_req(new_sock, new_location, new_path)
            else:
                # otherwise keep using same socket for redirect
                send_req(sock, new_location, new_path)
    
        
    sock.close()

    # Error handling for 401, 404, 505 errors and also printing the cookies when correct page found 202
    

    if(b"200 " in http_resp):
        
        print_cookies(get_cookie_list(http_resp))
    elif(b"401" in http_resp):
        PASS_PRO = True
        
        print_cookies(get_cookie_list(http_resp))
    elif(b"404 " in http_resp):
        print("Error 404: Requested document does not exist on server")
        
        print_cookies(get_cookie_list(http_resp))
    elif(b"505 " in http_resp):
        print("Error 505: HTTP Version not supported")

def get_port(hostname):
    #find out which port is needed 443 for https or 80 for http and if it supports h2
        #returns port that socket will use

    # Create a default SSL context
    context = ssl.create_default_context()
    context.set_alpn_protocols(['h2', 'http/1.1'])

    try:
        # Create a TCP connection to the hostname on port 443 (HTTPS)
        sock = socket.create_connection((hostname, 443))
    except Exception as e:
        print(e)
        sys.exit("failed to create socket when testng http2 support")
    try:
        #wrap ssl and get alpn protocol to determine if website supports h2
        ssl_sock = context.wrap_socket(sock, server_hostname=hostname)
        sel_protocol = ssl_sock.selected_alpn_protocol()

        if sel_protocol:
            h2_sup = "yes"
            port = 443
        else:
            h2_sup = "no"
            port = 80

        
        print("1. Supports http2: " + h2_sup + "\n")
    except ssl.CertificateError as e:
        print(e)
        print("1. Supports http2: no")
        print("2. Cookie List: None")
        print("3. Password Protected: False")
        sys.exit("Error, invalid website URI")
    except ssl.SSLError as e:
        print(e)
        print("1. Supports http2: no")
        print("2. Cookie List: None")
        print("3. Password Protected: False")
        sys.exit("Error, something went wrong with SSL")
       
    except Exception as e:
        print("Error:", e)
        print("1. Supports http2: no")
        print("2. Cookie List: None")
        print("3. Password Protected: False")
        sys.exit("Error in support http2")
    

    ssl_sock.close()
    sock.close()
    
    return port

def parse_uri(host_n):
    # parse the uri and eliminte unecessary bits
        #returns the cleaned up website name and the path

    clean_n = re.sub(r' ', '', host_n)
    clean_n = re.sub(r'https?://', '', clean_n)
    clean_n = clean_n.strip("/")

    #if there is a path, then separate it 
    if "/" in clean_n:

        clean_n = clean_n.split("/", 1)
        clean_name = clean_n[0]
        path_name = clean_n[1]
    else:
        clean_name = clean_n
        path_name = ""
   
    return clean_name, path_name

def get_cookie_list(http_response):
    # get all of the Set-Cookies from the response
    resp = http_response.decode('utf-8', 'ignore').splitlines()
   # print("get cookie list resp")
    cookie_list = [line for line in resp if "Set-Cookie:" in line]
    return cookie_list

def print_cookies(cookie_list):
    # prints the cookie list
    print("2. List of Cookies: \n")
    if len(cookie_list) == 0:
        print("None")

    for cookie in cookie_list:

        # split set-cookie at ;
         # find Set-Cookie: replace with cookie name
        # if possible find expires time
        # if possible find domain_times
        l_of_cook = re.split(";", cookie)
        for cook in l_of_cook:

            if re.search("Set-Cookie: ", cook):
                cookie_name = re.sub("Set-Cookie:", "cookie-name: ", cook)
                cookie_name = re.sub("=(.*)", "", cookie_name)
                print(cookie_name)
            elif re.search(" domain=", cook):
                print(re.sub(" domain=", "domain name: ", cook))
            elif re.search(" Expires=", cook):
                print(re.sub(" Expires=", "expires time: ", cook))
    print("\n")
       


def main ():

    if len(sys.argv)!= 2:
        sys.exit("incorrect input\n")

    host_name, path = parse_uri(sys.argv[1])

    print("website: " + host_name)

    port = get_port(host_name)

    #using the found port create the sockets
    if(port == 443):
        the_sock = https_connect(host_name)

    else:
        the_sock = http_connect(host_name)
    
    send_req(the_sock, host_name, path)
    
    print("3. Password Protected: " + str(PASS_PRO) + "\n")


if __name__ == "__main__":
         main()