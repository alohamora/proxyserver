import socket
import os
import sys
import string
import time
import thread
PORT = 12345

def recv_buffer( s ):
    buffer = ""
    while True:
        try:
            data = s.recv(1000)
            buffer += data
            if not data:
                break
        except socket.timeout:
            break
    return buffer

def save_to_file(resp,req_file,flag):
    headers = resp.split('\r\n')[0:7]
    content_length = headers[4].split(' ')[1]
    cache_control = headers[6].split(' ')[1]
    
    if flag == 0 and cache_control != 'no-cache':
        filelist = os.listdir('.')
        filelist.remove('proxyserver.py')
        if len(filelist) >= 3:
            os.remove(filelist[0])

    if cache_control != 'no-cache':
        content = resp[len(resp)-int(content_length):len(resp)]
        fd = open(req_file,"wb")
        fd.write(content)
        fd.close()
    return None

def getcache(buf,client_sock):
    origin_addr = buf.split('\r\n')[1].split(" ")[1]
    host,port = origin_addr.split(':')
    origin_addr = "http://" + origin_addr
    buf = buf.replace(origin_addr,"")
    req_file = buf.split('\r\n')[0].split(' ')[1].strip('/')
    
    try:
        origin_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        origin_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        origin_sock.settimeout(1)
        origin_sock.connect((host,int(port)))
        origin_sock.settimeout(None)
    except socket.error as err:
        print "Error connecting to origin server: %s" %(err)
        return None
    
    try:
        fd = open(req_file,"r")
        timestamp = time.ctime(os.path.getmtime(req_file))
        mod_header = 'If-Modified-Since: ' + str(timestamp)
        a = buf.strip('\r\n')
        a += '\r\n' + mod_header + '\r\n\r\n'
        origin_sock.send(a)
        resp = recv_buffer(origin_sock)
        status = resp.split('\r\n')[0].split(' ')[1]
        if status == '304':
            content = fd.read()
            a = resp.strip('\r\n')
            a = a.replace('304','200')
            a = a.replace('Not Modified','OK')
            a += '\r\n' + 'Content-Length: ' + str(len(content))
            a += '\r\n\r\n'
            resp = a + content
            print "[PROXY::BAY] - - Cached response..."
        elif status == '200':
            fd.close()
            save_to_file(resp,req_file,1)
    except IOError:
        origin_sock.send(buf)
        resp = ""
        resp = recv_buffer(origin_sock)
        status = resp.split('\r\n')[0].split(' ')[1]
        if status == '200':        
            save_to_file(resp,req_file,0)
    client_sock.send(resp)
    client_sock.close()
    print "[PROXY::BAY] - - [%s] Response sent successfully...Filename %s" %(status,req_file)
    return None

def main():
    try:
        server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    except socket.error as err:
        print "Error in socket creation: %s" %(err)
        raise
    try:
        server_socket.bind(('',PORT))
    except:
        print "Error in socket binding: %s" %(socket.error)
        raise
    server_socket.listen(5)

    while True:
        print "Initating server..."
        client_sock,addr = server_socket.accept()
        client_sock.settimeout(0.5)
        req_buffer = recv_buffer(client_sock)
        thread.start_new_thread(getcache,(req_buffer,client_sock))
main()