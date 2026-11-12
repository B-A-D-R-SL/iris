// AI contribution: 50% or more AI-generated
import { render, screen, waitFor } from "@testing-library/react";
import type { IScannerControls } from "@zxing/browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../../shared/i18n";
import { logger } from "../../../shared/logger";
import { PickupScanner } from "./PickupScanner";

type DecodeCallback = (
  result: { getText: () => string } | undefined,
  error: unknown,
  controls: IScannerControls,
) => void;

const decodeFromConstraints = vi.fn();
const stopControls = vi.fn();
const stopTrack = vi.fn();

vi.mock("@zxing/browser", () => ({
  BrowserQRCodeReader: class {
    decodeFromConstraints = decodeFromConstraints;
  },
}));

vi.mock("../../../shared/logger", () => ({
  logger: {
    warning: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

class FakeMediaStream {
  constructor(private readonly tracks: { stop: () => void }[]) {}
  getTracks() {
    return this.tracks;
  }
}

function mockDecode(outcome: "live" | "denied" | "unavailable" | "cancel-race") {
  decodeFromConstraints.mockImplementation(
    async (
      _constraints: unknown,
      video: HTMLVideoElement,
      callback: DecodeCallback,
    ): Promise<IScannerControls> => {
      const controls: IScannerControls = { stop: stopControls };
      if (outcome === "denied") {
        throw Object.assign(new Error("blocked"), { name: "NotAllowedError" });
      }
      if (outcome === "unavailable") {
        throw Object.assign(new Error("missing"), { name: "NotFoundError" });
      }
      video.srcObject = new FakeMediaStream([{ stop: stopTrack }]) as unknown as MediaStream;
      if (outcome === "cancel-race") {
        await Promise.resolve();
        callback(undefined, undefined, controls);
        return controls;
      }
      callback({ getText: () => "P4WZ8H" }, undefined, controls);
      return controls;
    },
  );
}

beforeEach(async () => {
  vi.stubGlobal("MediaStream", FakeMediaStream);
  decodeFromConstraints.mockReset();
  stopControls.mockReset();
  stopTrack.mockReset();
  vi.mocked(logger.warning).mockReset();
  await i18n.changeLanguage("fr");
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("PickupScanner", () => {
  it("starts the rear camera, reports live, and forwards a decoded code", async () => {
    mockDecode("live");
    const onDetected = vi.fn();
    const onStatus = vi.fn();

    render(<PickupScanner active onDetected={onDetected} onStatus={onStatus} />);

    expect(
      screen.getByLabelText("Aperçu de la caméra pour le code QR de cueillette"),
    ).toBeInTheDocument();
    await waitFor(() => expect(onStatus).toHaveBeenCalledWith("starting"));
    await waitFor(() => expect(onStatus).toHaveBeenCalledWith("live"));
    expect(onDetected).toHaveBeenCalledWith("P4WZ8H");
    expect(decodeFromConstraints).toHaveBeenCalledWith(
      { video: { facingMode: { ideal: "environment" } } },
      expect.any(HTMLVideoElement),
      expect.any(Function),
    );
  });

  it("maps permission errors to denied and logs without a stack", async () => {
    mockDecode("denied");
    const onStatus = vi.fn();

    render(<PickupScanner active onDetected={vi.fn()} onStatus={onStatus} />);

    await waitFor(() => expect(onStatus).toHaveBeenCalledWith("denied"));
    expect(logger.warning).toHaveBeenCalledWith("pickup_camera_unavailable");
  });

  it("maps other camera failures to unavailable", async () => {
    mockDecode("unavailable");
    const onStatus = vi.fn();

    render(<PickupScanner active onDetected={vi.fn()} onStatus={onStatus} />);

    await waitFor(() => expect(onStatus).toHaveBeenCalledWith("unavailable"));
    expect(logger.warning).toHaveBeenCalledWith("pickup_camera_unavailable");
  });

  it("does not start when inactive, and stops tracks on unmount", async () => {
    mockDecode("live");
    const onStatus = vi.fn();
    const inactive = render(
      <PickupScanner active={false} onDetected={vi.fn()} onStatus={onStatus} />,
    );
    expect(decodeFromConstraints).not.toHaveBeenCalled();
    inactive.unmount();

    const active = render(<PickupScanner active onDetected={vi.fn()} onStatus={onStatus} />);
    await waitFor(() => expect(onStatus).toHaveBeenCalledWith("live"));
    active.unmount();
    expect(stopControls).toHaveBeenCalled();
    expect(stopTrack).toHaveBeenCalled();
  });

  it("stops a decoder that resolves after the effect was cancelled", async () => {
    mockDecode("cancel-race");
    const { unmount } = render(<PickupScanner active onDetected={vi.fn()} onStatus={vi.fn()} />);
    unmount();
    await waitFor(() => expect(stopControls).toHaveBeenCalled());
    expect(stopTrack).toHaveBeenCalled();
  });
});
