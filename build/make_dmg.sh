#!/bin/bash
# PII Masker の .dmg ビルドスクリプト
#
# 出力:
#   dist/PII-Masker.dmg
#     └─ PII Masker/ （フォルダ丸ごと /Applications にドラッグする想定）
#         ├─ Install PII Masker.app
#         ├─ Start PII Masker.app
#         ├─ Stop PII Masker.app
#         └─ （リポジトリ本体: Dockerfile, core/, ui/ など）
#
# 使い方:
#   bash build/make_dmg.sh              # 署名なし
#   DEVELOPER_ID="Developer ID Application: Your Name (XXXXXXXXXX)" bash build/make_dmg.sh

set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"
DIST_DIR="${REPO_ROOT}/dist"
STAGE_DIR="${DIST_DIR}/stage"
APP_ROOT="${STAGE_DIR}/PII Masker"
DMG_PATH="${DIST_DIR}/PII-Masker.dmg"
VOLNAME="PII Masker"

echo "==> クリーンアップ"
rm -rf "${DIST_DIR}"
mkdir -p "${APP_ROOT}"

# ---------- .app ラッパーを生成する関数 ----------
# $1 = .app 名（拡張子なし）  $2 = 実行する .command ファイル名
make_app() {
  local appname="$1"
  local target_cmd="$2"
  local app_dir="${APP_ROOT}/${appname}.app"
  local bundle_id="com.piimasker.$(echo "$appname" | tr '[:upper:] ' '[:lower:]-')"

  mkdir -p "${app_dir}/Contents/MacOS"

  cat > "${app_dir}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTD/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>${bundle_id}</string>
    <key>CFBundleName</key>
    <string>${appname}</string>
    <key>CFBundleDisplayName</key>
    <string>${appname}</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

  # launcher は Terminal.app を使って親フォルダ内の .command を実行する
  # （Terminal で開くことでログが見え、非エンジニアにも進行状況が伝わる）
  cat > "${app_dir}/Contents/MacOS/launcher" <<LAUNCHER
#!/bin/bash
# .app の位置: .../PII Masker/<Name>.app/Contents/MacOS/launcher
# 親フォルダ（リポジトリ本体）に移動して .command を Terminal で開く
APP_DIR="\$(cd "\$(dirname "\$0")/../../.." && pwd)"
TARGET="\${APP_DIR}/${target_cmd}"
if [ ! -f "\${TARGET}" ]; then
  osascript -e "display alert \"PII Masker\" message \"${target_cmd} が見つかりません。\\n\\n配布フォルダを /Applications か Documents にコピーしてから実行してください。\""
  exit 1
fi
open -a Terminal "\${TARGET}"
LAUNCHER
  chmod +x "${app_dir}/Contents/MacOS/launcher"

  # 署名（任意）
  if [ -n "${DEVELOPER_ID:-}" ]; then
    echo "  signing ${appname}.app"
    codesign --force --deep --sign "${DEVELOPER_ID}" "${app_dir}"
  fi
}

echo "==> .app ラッパーを生成"
make_app "Install PII Masker" "install.command"
make_app "Start PII Masker"   "start.command"
make_app "Stop PII Masker"    "stop.command"

echo "==> リポジトリファイルをステージング"
# git tracked files のみコピー（不要ファイル混入を防ぐ）
cd "${REPO_ROOT}"
while IFS= read -r -d '' f; do
  case "$f" in
    dist/*) continue ;;
  esac
  mkdir -p "${APP_ROOT}/$(dirname "$f")"
  cp -p "$f" "${APP_ROOT}/$f"
done < <(git ls-files -z)

# .command ファイルに実行権限を付与（git 管理下では保持されるが念のため）
chmod +x "${APP_ROOT}/install.command" "${APP_ROOT}/start.command" "${APP_ROOT}/stop.command"

# /Applications へのエイリアスを配置（ドラッグ&ドロップ導線）
ln -s /Applications "${STAGE_DIR}/Applications"

echo "==> .dmg を作成"
hdiutil create \
  -volname "${VOLNAME}" \
  -srcfolder "${STAGE_DIR}" \
  -ov -format UDZO \
  "${DMG_PATH}"

rm -rf "${STAGE_DIR}"

echo ""
echo "✓ 完成: ${DMG_PATH}"
echo ""
echo "配布時の案内例:"
echo "  1. PII-Masker.dmg をダブルクリック"
echo "  2. 「PII Masker」フォルダを Applications にドラッグ"
echo "  3. /Applications/PII Masker/Install PII Masker.app を右クリック → 開く"
echo "  4. 以降は Start PII Masker.app をダブルクリック"
