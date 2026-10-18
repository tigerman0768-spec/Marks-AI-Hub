#!/usr/bin/env bash
set -euo pipefail

mkdir -p app/build/install
adb install -r app/build/install/Mark_s_AI_v2604.apk
adb shell am start -W -n com.marksai.app/.MainActivity || true
sleep 12
adb logcat -d -t 8000 > app/build/install/emulator-logcat.txt

if ! adb shell pidof com.marksai.app >/dev/null; then
  echo "status=failed; reason=app process not running after launch" > app/build/install/EMULATOR_SMOKE.txt
  exit 1
fi
if grep -E "FATAL EXCEPTION|Process: com\\.marksai\\.app" app/build/install/emulator-logcat.txt; then
  echo "status=failed; reason=crash signature after launch" > app/build/install/EMULATOR_SMOKE.txt
  exit 1
fi

adb shell uiautomator dump /sdcard/marks-ai-ui.xml >/dev/null 2>&1
adb pull /sdcard/marks-ai-ui.xml app/build/install/emulator-ui.xml >/dev/null
adb shell screencap -p /sdcard/marks-ai-home.png
adb pull /sdcard/marks-ai-home.png app/build/install/emulator-home-screen.png >/dev/null

if ! grep -Eiq "create film|film creator|ai filmmaking studio|filmmaking studio|generate screenplay" app/build/install/emulator-ui.xml; then
  echo "status=failed; reason=film-creation entry not found in accessible UI" > app/build/install/EMULATOR_SMOKE.txt
  exit 1
fi

python3 tools/emulator_find_film_entry.py app/build/install/emulator-ui.xml app/build/install/create-film-tap.txt
TAP_X="$(sed -n 's/^x=//p' app/build/install/create-film-tap.txt)"
TAP_Y="$(sed -n 's/^y=//p' app/build/install/create-film-tap.txt)"
if [[ -z "$TAP_X" || -z "$TAP_Y" ]]; then
  echo "status=failed; reason=film-creation entry has no tappable coordinates" > app/build/install/EMULATOR_SMOKE.txt
  exit 1
fi
cp app/build/install/emulator-ui.xml app/build/install/emulator-ui-before-film-tap.xml
adb shell input tap "$TAP_X" "$TAP_Y"
sleep 8
adb shell uiautomator dump /sdcard/marks-ai-film-ui.xml >/dev/null 2>&1
adb pull /sdcard/marks-ai-film-ui.xml app/build/install/emulator-film-creator-ui.xml >/dev/null
adb shell screencap -p /sdcard/marks-ai-film-screen.png
adb pull /sdcard/marks-ai-film-screen.png app/build/install/emulator-film-creator-screen.png >/dev/null
adb logcat -d -t 8000 > app/build/install/emulator-logcat.txt

if ! adb shell pidof com.marksai.app >/dev/null; then
  echo "status=failed; reason=app process died after tapping film creation" > app/build/install/EMULATOR_SMOKE.txt
  exit 1
fi
if grep -E "FATAL EXCEPTION|Process: com\\.marksai\\.app" app/build/install/emulator-logcat.txt; then
  echo "status=failed; reason=crash after tapping film creation" > app/build/install/EMULATOR_SMOKE.txt
  exit 1
fi
if cmp -s app/build/install/emulator-ui-before-film-tap.xml app/build/install/emulator-film-creator-ui.xml; then
  echo "status=failed; reason=film-creation tap did not change accessible UI" > app/build/install/EMULATOR_SMOKE.txt
  exit 1
fi

echo "status=passed; api=30; installed=true; launched=true; film_entry_visible=true; film_entry_tapped=true; screen_changed=true; process_alive=true; crash_signature=none" > app/build/install/EMULATOR_SMOKE.txt
