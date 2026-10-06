#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: package-linux-installer.sh <Coolie executable> <output .sh>" >&2
  exit 2
fi

binary=$1
output=$2
if [ ! -f "$binary" ]; then
  echo "Coolie executable not found: $binary" >&2
  exit 1
fi

mkdir -p "$(dirname "$output")"
{
  cat <<'INSTALLER'
#!/bin/sh
set -eu

case "$(uname -m)" in
  x86_64|amd64) ;;
  *)
    echo "This Coolie installer supports Linux x86_64 only." >&2
    exit 1
    ;;
esac

app_dir="${HOME}/.local/opt/coolie"
launcher_dir="${XDG_DATA_HOME:-${HOME}/.local/share}/applications"
mkdir -p "$app_dir" "$launcher_dir"
payload_line=$(awk '/^__COOLIE_PAYLOAD_BELOW__$/ { print NR + 1; exit }' "$0")
if [ -z "$payload_line" ]; then
  echo "Coolie installer payload is missing." >&2
  exit 1
fi
tail -n "+$payload_line" "$0" | tar -xz --no-same-owner -C "$app_dir"
chmod 755 "$app_dir/Coolie"
printf '%s\n' \
  '[Desktop Entry]' \
  'Type=Application' \
  'Name=Coolie' \
  'Comment=Open the Coolie owner workroom' \
  "Exec=\"$app_dir/Coolie\"" \
  'Terminal=false' \
  'Categories=Office;' > "$launcher_dir/coolie.desktop"
chmod 644 "$launcher_dir/coolie.desktop"
printf 'Coolie installed. Launch it from your application menu or run: %s/Coolie\n' "$app_dir"
exit 0
__COOLIE_PAYLOAD_BELOW__
INSTALLER
  tar -czf - -C "$(dirname "$binary")" "$(basename "$binary")"
} > "$output"
chmod 755 "$output"
