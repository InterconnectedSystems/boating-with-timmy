[app]
title = Boating With Timmy
package.name = boatingwithtimmy
package.domain = com.interconnectedsystems

source.dir = .
source.include_exts = py

version = 1.0

requirements = python3==3.10.14,pygame2

orientation = landscape
fullscreen = 1

android.permissions =
android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.sdk = 33
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = False

[buildozer]
log_level = 2
warn_on_root = 1
