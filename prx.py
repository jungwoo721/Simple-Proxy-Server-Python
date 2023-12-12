import sys
import re
import socket
import threading
import traceback

# Class for Proxy Server
class ProxyServer:
    def __init__(self, host, port):
        '''
        Initializing Proxy Server.
        Create socket, bind it to (local)host, start to listen for incoming requests.
        '''
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(1)
        print(f'Starting proxy server on port {self.port}')
        
        self.filter_img = False
        self.num_logger = 1
        
    def run(self):
        ''' Create new thread for each client.'''
        try:
            while True:
                client_socket, client_addr = self.server.accept()
                threading.Thread(target=self.proxy_thread, args=(client_socket, client_addr)).start()
        except KeyboardInterrupt:
            self.server.close()
            sys.exit(0)
        
    def proxy_thread(self, client_socket, client_addr):
        redirect_url = False        
        try:
            ## [CLI ==> PRX --- SRV]
            client_request = client_socket.recv(4096).decode('utf-8')
            client_request_lines = client_request.split('\r\n')

            # Extract the User-Agent header (for logging info)
            user_agent = None
            for line in client_request_lines:
                if line.startswith('User-Agent:'):
                    # Extract the User-Agent value using regular expression
                    user_agent_match = re.match(r'User-Agent:\s*(.*)', line)
                    if user_agent_match:
                        user_agent = user_agent_match.group(1)
                        break
            
            # Get method, url of the request
            client_request_method, client_request_url, client_request_version = client_request_lines[0].split()
            client_request_host = client_request_lines[1].split()[1]
            
            # Copy request info for forwarding from proxy server
            proxy_request_host = client_request_host
            proxy_request = client_request
            proxy_request_url = client_request_url
            
            # URL filter: Redirect URL if URL containing "korea"
            if "korea" in client_request_url:
                redirect_url = True        
                proxy_request_host = 'mnet.yonsei.ac.kr'
                proxy_request_url = 'http://mnet.yonsei.ac.kr/'
                proxy_request.replace(client_request_url, proxy_request_url)
                
            # Img filter: Check if URL contains parameter (for changing filter_img option)
            if "?img_off" in client_request_url:
                self.filter_img = True
            elif "?img_on" in client_request_url:
                self.filter_img = False
            
            # Disable persistent connection
            proxy_request.replace('keep-alive', 'close')
            
            ## [CLI --- PRX ==> SRV]
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy_request_port = 80
            server.connect((proxy_request_host, proxy_request_port))  
            server.sendall(proxy_request.encode('utf-8'))
            
            ## [CLI --- PRX <== SRV]
            current_header = '' # for logging info
            is_img = False
            while True:
                try:
                    server_response = server.recv(4096)
                    server_response_header = server_response.split(b'\r\n\r\n')[0]

                    if not server_response:
                        break
                    
                    if self.filter_img:
                        if b'Content-Type: image' in server_response_header:
                    # If the content type is image, drop the response from the server. (or pass '404 Not Found')
                            response_for_image = f'HTTP/1.1 404 Not Found\r\n\r\n'.encode('utf-8')
                            client_socket.sendall(response_for_image)
                            is_img = True
                            
                    # Forwarding server response to the client
                        else:   
                            client_socket.sendall(server_response)
                    else:
                        client_socket.sendall(server_response)
                        
                    # for logging info
                    current_header = server_response_header
                    
                except Exception as e:
                    #print(e)
                    pass
                    
            # Close related sokets
            server.close()
            client_socket.close()

            # Lox proxy information
            self.log_proxy_info(redirect_url=redirect_url, 
                                client_addr=client_addr, 
                                client_request_method=client_request_method,
                                client_request_url=client_request_url, 
                                user_agent=user_agent, 
                                proxy_request_host=proxy_request_host,
                                proxy_request_port=proxy_request_port,
                                proxy_request_url=proxy_request_url,
                                response_header=current_header,
                                is_img=is_img
                                )
            
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            #print(traceback.format_exc())
            #print(e)
            pass
    
    def log_proxy_info(self, redirect_url,
                       client_addr, 
                       client_request_method='GET', 
                       client_request_url='', 
                       user_agent='',
                       proxy_request_host='',
                       proxy_request_port=80,
                       proxy_request_url='',
                       response_header=b'',
                       is_img=False
                       ):
        
        '''Function for logging Proxy Information'''
        
        # [CLI ==> PRX --- SRV]
        # Format for logging User-Agent
        user_agent_index = user_agent.find(')')
        user_agent_simple = user_agent
        if user_agent_index != -1:
            user_agent_simple = user_agent[:user_agent_index+1]
        
        # Default content type (will be changed below. only for few cases where error might occur)
        file_formats = {'.jpeg':'image/jpeg', '.png':'image/png', '.gif':'image/gif', '.jpg':'image/jpg', '.bmp':'image/bmp', '.tiff':'image/tiff', '.webp':'image/webp', '.svg':'image/svg+xml', '.js':'application/javascript', '.css': 'text/css', '':'text/html'}
        
        filename = client_request_url.split('/')[-1]
        response_content_type = ''
        def_response_content_type =''
        for ext, type in file_formats.items():
            if ext in filename:
               response_content_type = type
               def_response_content_type = type
               break
           
        ## [CLI --- PRX <== SRV]
        head_list = response_header.split(b'\r\n')

        response_status = '200 OK'
        response_status_img = '404 Not Found'
        response_content_length = ''
        for line in head_list:
            if b'HTTP/' in line:
                # Get response status, reason
                response_status = ' '.join(line.decode().split()[1:])
            if b'Content-Length:' in line:
                # Get content length
                response_content_length += line.decode().split()[1]
            if b'Content-Type:' in line:
                # Get content type
                response_content_type = ' '.join(line.decode().split()[1:])
                if response_content_type == '':
                    response_content_type = def_response_content_type
                    
        if not response_content_length == '':
            response_content_length += ' bytes'

        '''Log proxy information'''
        print(f"-"*47)
        print(f"{self.num_logger} [{'O' if redirect_url is True else 'X'}] Redirected [{'O' if self.filter_img is True else 'X'}] Image filter")
        print(f'[CLI connected to {client_addr[0]}:{client_addr[1]}]')
        print(f'[CLI ==> PRX --- SRV]\n  > {client_request_method} {client_request_url}\n  > {user_agent_simple}')
        print(f'[SRV connected to {proxy_request_host}:{proxy_request_port}]')
        print(f'[CLI --- PRX ==> SRV]\n  > {client_request_method} {proxy_request_url}\n  > {user_agent_simple}')
        print(f'[CLI --- PRX <== SRV]\n  > {response_status}\n  > {response_content_type} {response_content_length}')
        if is_img:
            print(f'[CLI <== PRX --- SRV]\n  > {response_status_img}')
        else:
            print(f'[CLI <== PRX --- SRV]\n  > {response_status}\n  > {response_content_type} {response_content_length}')
        print('[CLI disconnected]\n[SRV disconnected]')
        
        self.num_logger += 1
            

# Run proxy server with custom port
if __name__ == '__main__':
    proxy_port = int(sys.argv[1])
    server = ProxyServer('localhost', proxy_port)
    server.run()
