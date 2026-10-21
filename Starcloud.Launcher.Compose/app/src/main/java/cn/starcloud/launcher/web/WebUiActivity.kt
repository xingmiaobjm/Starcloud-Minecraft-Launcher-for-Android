package cn.starcloud.launcher.web

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.view.ViewGroup
import android.util.Log
import android.webkit.ConsoleMessage
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient

/**
 * Web UI 壳：一个全屏 WebView 加载 `assets/web/app/index.html`。
 *
 * 为什么不是 Electron：Electron 只能跑在桌面（它自带 Chromium + Node 主进程），
 * 安卓上跑不了。要做到「桌面 Electron 与安卓用同一套界面」，可行的做法是
 * **同一份 Web 前端 + 两个容器**：桌面上是 Electron，安卓上是这个 WebView 壳，
 * 两边都通过同一组桥接方法（`window.starcloud.*`）调用原生能力。
 *
 * 资源用 `file://` 读 assets，并打开 `allowFileAccessFromFileURLs` /
 * `allowUniversalAccessFromFileURLs`：ES module 与静态资源在 file:// 下会被
 * CORS 拦掉（白屏），放开后模块与相对路径都能正常工作。
 * （不用 WebViewAssetLoader：它要 androidx.webkit，离线环境拉不到新依赖。）
 *
 * Compose 界面保持原样，这个 Activity 不设 launcher 入口，用
 *   adb shell am start -n cn.starcloud.launcher.compose/cn.starcloud.launcher.web.WebUiActivity
 * 进入。
 */
class WebUiActivity : Activity() {

    private var webView: WebView? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val view = WebView(this).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT
            )
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            // 页面要适配手机竖屏：跟随系统字号缩放，但别把布局撑爆
            settings.textZoom = 100
            settings.allowFileAccess = true
            settings.allowFileAccessFromFileURLs = true
            settings.allowUniversalAccessFromFileURLs = true
            webViewClient = WebViewClient()
            // 把网页的 console / 异常转到 logcat：WebView 里的报错默认看不见，
            // 白屏时只能靠这个定位（tag = StarcloudWeb）
            webChromeClient = object : WebChromeClient() {
                override fun onConsoleMessage(m: ConsoleMessage): Boolean {
                    Log.i("StarcloudWeb", "[${m.messageLevel()}] ${m.message()} @${m.lineNumber()}")
                    return true
                }
            }
            // 回调统一走主线程 + evaluateJavascript：@JavascriptInterface 的执行线程不是 UI 线程
            val self = this
            addJavascriptInterface(
                StarcloudBridge(this@WebUiActivity) { js ->
                    post { self.evaluateJavascript(js, null) }
                },
                "starcloud",
            )
            loadUrl("file:///android_asset/web/app/index.html")
        }
        webView = view
        setContentView(view)
    }

    override fun onDestroy() {
        // WebView 持有桥对象，销毁前先解绑，避免泄漏 Activity
        webView?.apply {
            removeJavascriptInterface("starcloud")
            destroy()
        }
        webView = null
        super.onDestroy()
    }

    private companion object {
    }
}
