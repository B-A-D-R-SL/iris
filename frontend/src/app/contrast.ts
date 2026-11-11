// AI contribution: 50% or more AI-generated
/** WCAG 2.1 sRGB relative luminance, for opaque six-digit hexadecimal tokens. */
function luminance(color: string): number {
  if (!/^#[0-9a-f]{6}$/i.test(color)) {
    throw new TypeError("Expected an opaque six-digit hexadecimal colour");
  }
  const channels = [1, 3, 5].map((offset) => {
    const channel = Number.parseInt(color.slice(offset, offset + 2), 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

/** Contrast is symmetric and ranges from 1 (identical) to 21 (black and white). */
export function contrastRatio(first: string, second: string): number {
  const a = luminance(first);
  const b = luminance(second);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}
