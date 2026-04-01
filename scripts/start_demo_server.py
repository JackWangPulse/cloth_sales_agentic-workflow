from _bootstrap import PROJECT_ROOT  # noqa: F401
#!/usr/bin/env python3
"""绠€鍗曠殑鏈湴 HTTP 鏈嶅姟鍣紝鐢ㄤ簬杩愯 demo.html

浣跨敤鏂规硶锛?
    python scripts/start_demo_server.py

鐒跺悗鍦ㄦ祻瑙堝櫒璁块棶锛?
    http://127.0.0.1:8080/demo.html
"""
import http.server
import socketserver
import webbrowser
import os

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

    
    def end_headers(self):
        # 娣诲姞 CORS 澶达紝鍏佽璺ㄥ煙璇锋眰
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        """澶勭悊 OPTIONS 棰勬璇锋眰"""
        self.send_response(200)
        self.end_headers()

def main():

    os.chdir(PROJECT_ROOT)
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        demo_url = f"http://127.0.0.1:{PORT}/demo.html"
        vision_demo_url = f"http://127.0.0.1:{PORT}/demo_vision_similar.html"
        print("=" * 60)
        # print("馃殌 Demo 鏈嶅姟鍣ㄥ凡鍚姩锛?)
        print("=" * 60)
        print(f"馃摫 閿€鍞缓璁?Demo: {demo_url}")
        print(f"馃摫 鎷嶇収璇嗗浘 Demo: {vision_demo_url}")
        print(f"馃敡 API 鍚庣: http://127.0.0.1:8000")
        print("=" * 60)
        # print("鎸?Ctrl+C 鍋滄鏈嶅姟鍣?)
        print("=" * 60)
        
        # 鑷姩鎵撳紑娴忚鍣紙榛樿鎵撳紑閿€鍞缓璁?Demo锛?
        try:
            webbrowser.open(demo_url)
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n鏈嶅姟鍣ㄥ凡鍋滄")

if __name__ == "__main__":
    main()


