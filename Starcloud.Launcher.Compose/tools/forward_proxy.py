# 临时转发代理 v9：设备经 adb reverse / WiFi 访问 8889，按路径选上游并 404 回落。
# 所有上游统一走 curl 子进程：本机加速器 TUN 对 python-urllib 的外网请求有拦截/污染
# （同 URL shell curl 200 而 urllib 404，/v1/packages/ 与 Maven Central 均复现），curl 稳定。
import http.server
import subprocess
import tempfile
import os

BMCLAPI = "https://bmclapi2.bangbang93.com"

# 固定 Git Bash 自带 curl：Windows PATH 里 System32 的 schannel 版在本机环境下行为异常，
# 且需打印 remote_ip 诊断加速器 TUN 分流（详见 proxy.log）。
CURL = r"C:\Program Files\Git\mingw64\bin\curl.exe"

def upstreams(path: str):
    # /v1/packages/（Mojang 新版清单格式）BMCLAPI 无此路径，官方 piston-meta 优先
    if path.startswith("/v1/packages/"):
        return ["https://piston-meta.mojang.com" + path, BMCLAPI + path]
    # /maven/（BMCLAPI 镜像布局）：BMCLAPI 与官方 CDN 对 26.x 新依赖库缺货 → Maven Central
    if path.startswith("/maven/"):
        official = "https://libraries.minecraft.net" + path.replace("/maven/", "/", 1)
        central = "https://repo1.maven.org/maven2" + path.replace("/maven/", "/", 1)
        return [BMCLAPI + path, central, official]
    if path.startswith("/assets/"):
        return [BMCLAPI + path, "https://resources.download.minecraft.net" + path]
    if path.startswith("/versions/"):
        return [BMCLAPI + path, "https://piston-meta.mojang.com" + path]
    # 无前缀（libraries.minecraft.net 官方 URL 的裸路径）：官方直连优先，
    # 回落 piston-data maven、Maven Central（26.x 新依赖在此）与 BMCLAPI
    return ["https://libraries.minecraft.net" + path,
            "https://piston-data.mojang.com/maven" + path,
            "https://repo1.maven.org/maven2" + path,
            BMCLAPI + path]

def fetch_upstream(url: str, timeout: int = 120):
    """curl 子进程拉取。返回 (status, data, peer)；status 为 HTTP 码，连接失败为 0。"""
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        r = subprocess.run(
            [CURL, "-s", "-v", "--max-time", str(timeout), "-A", "starcloud-proxy",
             "-w", "%{http_code} %{remote_ip}", "-o", tmp, url],
            capture_output=True)
        txt = r.stdout.decode("ascii", "ignore")
        parts = txt.split()
        code = int(parts[0]) if parts and parts[0].isdigit() else 0
        peer = parts[1] if len(parts) > 1 else "?"
        data = open(tmp, "rb").read() if code == 200 else b""
        if code != 200:
            try:
                body = open(tmp, "rb").read()[:160]
                if body:
                    print("[body] " + repr(body), flush=True)
            except Exception:
                pass
        return code, data, peer
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

class Proxy(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        last = "no upstream"
        for up in upstreams(self.path):
            url = up + self.path
            code, data, peer = fetch_upstream(url)
            if code == 200:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                print(f"[proxy] 200 {self.path} <- {up} via {peer} ({len(data)}B)", flush=True)
                return
            print(f"[proxy] {code} {self.path} <- {up} via {peer}", flush=True)
            last = f"upstream {code}"
            if code != 404:
                break
        self.send_error(502, last)

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    # 监听 8889：与 VersionDownloader.LOCAL_PROXY 一致
    print("[proxy] v9 listening on 0.0.0.0:8889 (curl upstream + fallback)", flush=True)
    http.server.ThreadingHTTPServer(("0.0.0.0", 8889), Proxy).serve_forever()
