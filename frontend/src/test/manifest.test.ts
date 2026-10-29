// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import indexHtml from "../../index.html?raw";
import manifestText from "../../public/manifest.webmanifest?raw";

interface ManifestIcon {
  src: string;
  sizes: string;
  type: string;
  purpose: string;
}

const manifest = JSON.parse(manifestText) as {
  name: string;
  short_name: string;
  start_url: string;
  display: string;
  icons: ManifestIcon[];
};
const publicIcons = Object.keys(import.meta.glob("../../public/icons/*.png")).map((path) =>
  path.replace("../../public", ""),
);

describe("installable on a phone (SET-16)", () => {
  it("has what browsers require to offer installation", () => {
    expect(manifest.name).toBeTruthy();
    expect(manifest.short_name).toBe("Iris");
    expect(manifest.start_url).toBe("/");
    expect(manifest.display).toBe("standalone");
    const sizes = manifest.icons.filter((icon) => icon.purpose === "any").map((icon) => icon.sizes);
    expect(sizes).toEqual(expect.arrayContaining(["192x192", "512x512"]));
    expect(manifest.icons.some((icon) => icon.purpose === "maskable")).toBe(true);
  });

  it("points only to icons that exist", () => {
    for (const icon of manifest.icons) {
      expect(publicIcons).toContain(icon.src);
    }
    expect(publicIcons).toContain("/icons/apple-touch-icon.png");
  });

  it("is linked from the page, with the iPhone icon", () => {
    expect(indexHtml).toContain('<link rel="manifest" href="/manifest.webmanifest" />');
    expect(indexHtml).toContain(
      '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />',
    );
    expect(indexHtml).toContain('<html lang="fr">');
  });
});
