export interface DesktopUpdate {
  commit: string;
  assets: Array<{ name: string; url: string }>;
}

const RELEASE_URL =
  "https://api.github.com/repos/Newman10p/coolie/releases/tags/desktop-latest";
const INSTALLER_NAMES = new Set([
  "Coolie-Windows-Setup.exe",
  "Coolie-macOS-Intel.dmg",
  "Coolie-macOS-Apple-Silicon.dmg",
  "Coolie-Linux-x86_64.sh",
]);

export async function checkForDesktopUpdate(): Promise<DesktopUpdate | null> {
  const response = await fetch(RELEASE_URL, {
    headers: { Accept: "application/vnd.github+json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Update check failed (HTTP ${response.status}).`);
  }

  const release: unknown = await response.json();
  if (!release || typeof release !== "object" || !("body" in release) || !("assets" in release)) {
    throw new Error("The update service returned an invalid release record.");
  }
  if (typeof release.body !== "string" || !Array.isArray(release.assets)) {
    throw new Error("The update service returned an incomplete release record.");
  }

  const commitMatch = release.body.match(/Build commit:\s*`?([0-9a-f]{40})`?/i);
  if (!commitMatch) {
    throw new Error("The latest desktop build does not include a valid commit identifier.");
  }
  const assets = release.assets.flatMap((asset: unknown) => {
    if (
      !asset ||
      typeof asset !== "object" ||
      !("name" in asset) ||
      typeof asset.name !== "string" ||
      !INSTALLER_NAMES.has(asset.name) ||
      !("browser_download_url" in asset) ||
      typeof asset.browser_download_url !== "string"
    ) {
      return [];
    }
    return [{ name: asset.name, url: asset.browser_download_url }];
  });
  if (assets.length !== INSTALLER_NAMES.size) {
    throw new Error("The latest desktop build is missing one or more platform installers.");
  }
  if (commitMatch[1] === import.meta.env.VITE_COOLIE_BUILD_SHA) return null;
  return { commit: commitMatch[1], assets };
}

export function getCurrentDesktopBuild(): string {
  return import.meta.env.VITE_COOLIE_BUILD_SHA || "development";
}
