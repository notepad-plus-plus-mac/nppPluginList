# Notepad++ macOS Plugin List

Plugin registry for the [Notepad++ macOS port](https://github.com/nppmss/notepad-plus-plus-macos).

## Format

`pl.macos-arm64.json` — JSON registry of available macOS ARM64 plugins.

Each entry:
```json
{
    "folder-name": "PluginName",
    "display-name": "Plugin Display Name",
    "version": "1.0.0",
    "id": "<sha256 of zip>",
    "repository": "https://github.com/.../releases/download/.../Plugin.zip",
    "description": "What the plugin does",
    "author": "Author Name",
    "homepage": "https://github.com/..."
}
```

## Plugin Development

macOS plugins are `.dylib` shared libraries built against `NppPluginInterfaceMac.h`.

### Required Exports

```c
void        setInfo(NppData nppData);
const char* getName(void);
FuncItem*   getFuncsArray(int *nbF);
void        beNotified(SCNotification *notifyCode);
intptr_t    messageProc(uint32_t Message, uintptr_t wParam, intptr_t lParam);
```

### Key Differences from Windows

| Windows | macOS |
|---------|-------|
| `.dll` (PE) | `.dylib` (Mach-O) |
| `__declspec(dllexport)` | `__attribute__((visibility("default")))` |
| `wchar_t*` (UTF-16) | `char*` (UTF-8) |
| `::SendMessage(hwnd, msg, w, l)` | `nppData._sendMessage(handle, msg, w, l)` |
| `HWND` | `uintptr_t` (opaque handle) |
| Win32 dialogs (.rc) | Native AppKit (NSPanel/NSAlert) |
| INI files (`GetPrivateProfileString`) | JSON files |

### Installation

Place your plugin at:
```
~/.notepad++/plugins/PluginName/PluginName.dylib
```

Restart Notepad++ macOS to load it.

## Ported Plugins

| Plugin | Status | Repository |
|--------|--------|------------|
| Reverse Lines | Ported | [qkNppReverseLines-MacOS](https://github.com/nppmss/qkNppReverseLines-MacOS) |
| URL Plugin | Ported | [nppURLPlugin-MacOS](https://github.com/nppmss/nppURLPlugin-MacOS) |
