// AI contribution: 50% or more AI-generated
import { IconPhoto } from "@tabler/icons-react";
import { useState } from "react";

import classes from "../household.module.css";

export interface ListingPhotoProps {
  /** A read-only link that expires within five minutes, or null without a photo. */
  url: string | null;
  size: "thumb" | "large";
}

/**
 * The listing's photo, or the mockups' placeholder when there is none or its
 * link has expired. The title next to it says what it shows, so alt is empty.
 */
export function ListingPhoto({ url, size }: ListingPhotoProps) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);

  if (!url || failedUrl === url) {
    return (
      <div className={`${classes.photo} ${classes.placeholder}`} data-size={size}>
        <IconPhoto size={size === "thumb" ? 24 : 32} stroke={1.5} aria-hidden />
      </div>
    );
  }
  return (
    <img
      src={url}
      alt=""
      className={classes.photo}
      data-size={size}
      // The signed link must not leak to another site through the Referer header.
      referrerPolicy="no-referrer"
      onError={() => setFailedUrl(url)}
    />
  );
}
