// AI contribution: 50% or more AI-generated
/**
 * Live QR preview for store pickup confirmation (US-44). Uses @zxing/browser
 * with the rear camera when available; callers keep a typed-code fallback.
 */
import { BrowserQRCodeReader, type IScannerControls } from "@zxing/browser";
import { useEffect, useEffectEvent, useRef } from "react";
import { useTranslation } from "react-i18next";

import { logger } from "../../../shared/logger";
import classes from "./PickupScanner.module.css";

export type ScannerStatus = "starting" | "live" | "denied" | "unavailable";

export interface PickupScannerProps {
  /** When false, the camera stays off (review and success steps). */
  active: boolean;
  onDetected: (text: string) => void;
  onStatus: (status: ScannerStatus) => void;
}

function stopTracks(video: HTMLVideoElement | null) {
  const stream = video?.srcObject;
  if (stream instanceof MediaStream) {
    for (const track of stream.getTracks()) track.stop();
  }
  if (video) video.srcObject = null;
}

function cameraStatus(error: unknown): ScannerStatus {
  const name =
    error && typeof error === "object" && "name" in error
      ? String((error as { name: unknown }).name)
      : "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") return "denied";
  return "unavailable";
}

async function startDecoder(
  video: HTMLVideoElement,
  onDetected: (text: string) => void,
  controlsRef: { current: IScannerControls | null },
): Promise<IScannerControls> {
  const reader = new BrowserQRCodeReader();
  return reader.decodeFromConstraints(
    { video: { facingMode: { ideal: "environment" } } },
    video,
    (result, _error, ctrl) => {
      controlsRef.current = ctrl;
      if (result) onDetected(result.getText());
    },
  );
}

/** Continuous QR decode into `onDetected`; stops cleanly on unmount or when inactive. */
export function PickupScanner({ active, onDetected, onStatus }: PickupScannerProps) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const controlsRef = useRef<IScannerControls | null>(null);
  const reportDetected = useEffectEvent((text: string) => onDetected(text));
  const reportStatus = useEffectEvent((status: ScannerStatus) => onStatus(status));

  useEffect(() => {
    if (!active || !videoRef.current) return;
    const video = videoRef.current;
    let cancelled = false;
    reportStatus("starting");
    void startDecoder(video, reportDetected, controlsRef)
      .then((controls) => {
        if (cancelled) {
          controls.stop();
          stopTracks(video);
          return;
        }
        controlsRef.current = controls;
        reportStatus("live");
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          logger.warning("pickup_camera_unavailable");
          reportStatus(cameraStatus(error));
        }
      });
    return () => {
      cancelled = true;
      controlsRef.current?.stop();
      controlsRef.current = null;
      stopTracks(video);
    };
  }, [active]);

  return (
    <div className={classes.frame} data-active={active || undefined}>
      <video
        ref={videoRef}
        className={classes.video}
        muted
        playsInline
        autoPlay
        aria-label={t("reservation.confirm.cameraPreview")}
      />
      <div className={classes.reticle} aria-hidden />
    </div>
  );
}
