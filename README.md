# Starcloud Minecraft Launcher · Android

Starcloud 启动器的 Android 客户端。桌面端（Windows / Linux）在另一个仓库
[Starcloud-Minecraft-Launcher](https://github.com/xingmiaobjm/Starcloud-Minecraft-Launcher)。

## 结构

```
Starcloud.Launcher.Compose/    当前前端：Kotlin + Jetpack Compose
  app/src/main/java/cn/starcloud/launcher/compose/
    MainActivity.kt            入口：横屏 + 左侧五格竖排导航
    screens/                   页面（主页 / 版本 / 下载 / 存档 / Nova / 设置 …）
    data/                      版本清单、下载器、组件部署
    game/                      启动参数、JVM 拉起、运行时选择
  app/src/main/java/cn/starcloud/launcher/web/
    WebUiActivity.kt           Web UI 壳（Phase 0）：全屏 WebView
    StarcloudBridge.kt         Web ↔ Kotlin 桥（appInfo / versions / log）
  app/src/main/assets/web/     Web UI 页面（后续接 React 产物）
  app/src/main/cpp/            libstarcloudjvm.so：JNI_CreateJavaVM 封装

src/Starcloud.Android.Core/    安卓内核：下载引擎、版本解析、启动参数
src/Starcloud.Android.Host/    宿主层：JVM 嵌入、SDL、输入法、系统调用
src/Starcloud.Launcher.Uno/    早期 Uno 前端（已停更，保留参考）
src/Starcloud.Launcher.Phone/  更早的移动壳
spike-uno/ spikes/             技术验证（JVM 嵌入、SDL 等）
components/                    fetch-components.ps1：按需下载 JRE / LWJGL / Mesa
tests/                         安卓内核单测
```

## 构建

前置：JDK 17、Android SDK（`compileSdk 36`）、NDK（`libstarcloudjvm.so` 需要 CMake 3.22.1）。

```bash
cd Starcloud.Launcher.Compose

# 组件包（JRE / LWJGL / Mesa，约 340 MB，不入库）
powershell -ExecutionPolicy Bypass -File ../components/fetch-components.ps1

./gradlew assembleDebug          # 或本机 gradle 8.7+
```

产物：`app/build/outputs/apk/debug/app-debug.apk`。

## 界面路线

同一份 Web 前端 + 两个容器：桌面用 Electron，安卓用 WebView（Electron 本身跑不到安卓）。
安卓侧的 Web 壳已经落地 Phase 0，不设启动入口，验证方式：

```bash
adb shell am start -n cn.starcloud.launcher.compose/cn.starcloud.launcher.web.WebUiActivity
adb logcat -s StarcloudWeb
```

详见 `docs/2026-10-21-android-web-ui-shell-design.md`。

## 约定

- 版本号唯一来源：`Starcloud.Launcher.Compose/app/build.gradle.kts` 的 `versionName`。
- 业务逻辑只在 `Android.Core` / `compose/data` / `compose/game`，界面层不写业务。
- 提交前跑一次 `gradle :app:assembleDebug`，要求 0 错误。
- 组件包、构建产物、反编译参考（`spikes/fcl-src`）不入库。
