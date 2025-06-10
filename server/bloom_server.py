import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer

class BloomFilter:
    def __init__(self, size: int, hash_functions: list):
        self.size = size
        self.hash_functions = hash_functions
        self.bit_array = bytearray((size + 7) // 8)
    
    def _set_bit(self, position: int):
        byte_index = position // 8
        bit_offset = position % 8
        self.bit_array[byte_index] |= (1 << bit_offset)
    
    def _get_bit(self, position: int) -> bool:
        byte_index = position // 8
        bit_offset = position % 8
        return (self.bit_array[byte_index] & (1 << bit_offset)) != 0
    
    def insert(self, key):
        for hash_func in self.hash_functions:
            position = hash_func(key) % self.size
            self._set_bit(position)
    
    def search(self, key) -> bool:
        for hash_func in self.hash_functions:
            position = hash_func(key) % self.size
            if not self._get_bit(position):
                return False
        return True

class BloomFilterServer:
    """Класс для хранения состояния сервера"""
    bloom_filter = None
    key_type = 'str'
    
    hash_registry = {
        'default_str': lambda x: hash(x),
        'default_int': lambda x: hash(x),
        'str_simple': lambda s: sum(ord(c) for c in s),
        'str_polynomial': lambda s: sum(ord(c) * 31**i for i, c in enumerate(s)),
        'int_multiply': lambda i: (i * 2654435761) & 0xFFFFFFFF,
        'int_xor': lambda i: (i ^ 0xDEADBEEF) & 0xFFFFFFFF,
        'universal_sha256': lambda x: int.from_bytes(__import__('hashlib').sha256(str(x).encode()).digest()[:4], 'big'),
        'universal_md5': lambda x: int.from_bytes(__import__('hashlib').md5(str(x).encode()).digest()[:4], 'big')
    }

class BloomAPIHandler(BaseHTTPRequestHandler):
    server_state = BloomFilterServer()
    
    def _parse_payload(self):
        content_length = int(self.headers['Content-Length'])
        return json.loads(self.rfile.read(content_length))
    
    def _send_response(self, status, data):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        if self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'pong')
        
        elif self.path.startswith('/search'):
            if not self.server_state.bloom_filter:
                self._send_response(400, {"error": "Bloom filter not initialized"})
                return
            
            query = self.path.split('?', 1)[1] if '?' in self.path else ''
            params = dict(p.split('=') for p in query.split('&') if '=' in p)
            key = params.get('key', '')
            
            try:
                if self.server_state.key_type == 'int':
                    key = int(key)
                elif self.server_state.key_type == 'float':
                    key = float(key)
            except ValueError:
                self._send_response(400, {"error": "Invalid key format"})
                return
            
            exists = self.server_state.bloom_filter.search(key)
            self._send_response(200, {"key": key, "exists": exists})
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        if self.path == '/init':
            try:
                data = self._parse_payload()
                size = data['size']
                hash_names = data['hash_functions']
                key_type = data.get('key_type', 'str')
                
                hash_funcs = []
                for name in hash_names:
                    if name in self.server_state.hash_registry:
                        hash_funcs.append(self.server_state.hash_registry[name])
                    else:
                        self._send_response(400, {"error": f"Hash function '{name}' not found"})
                        return
                
                self.server_state.bloom_filter = BloomFilter(size, hash_funcs)
                self.server_state.key_type = key_type
                
                self._send_response(200, {
                    "status": "initialized",
                    "size": size,
                    "hash_functions": hash_names,
                    "key_type": key_type
                })
            except Exception as e:
                self._send_response(400, {"error": str(e)})
        
        elif self.path == '/insert':
            if not self.server_state.bloom_filter:
                self._send_response(400, {"error": "Bloom filter not initialized"})
                return
            
            try:
                data = self._parse_payload()
                key = data['key']
                
                if self.server_state.key_type == 'int' and not isinstance(key, int):
                    raise ValueError("Expected integer key")
                elif self.server_state.key_type == 'float' and not isinstance(key, float):
                    raise ValueError("Expected float key")
                elif self.server_state.key_type == 'str' and not isinstance(key, str):
                    raise ValueError("Expected string key")
                
                self.server_state.bloom_filter.insert(key)
                self._send_response(200, {"status": "inserted", "key": key})
            except Exception as e:
                self._send_response(400, {"error": str(e)})
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, BloomAPIHandler)
    print('Server running on http://localhost:8000')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
