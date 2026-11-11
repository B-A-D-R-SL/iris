// AI contribution: 50% or more AI-generated
import { fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../../test/render";
import { ListingPhoto } from "./ListingPhoto";

describe("ListingPhoto", () => {
  it("shows the placeholder without a photo", () => {
    const { container } = renderWithProviders(<ListingPhoto url={null} size="thumb" />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("falls back to the placeholder when the link has expired, and tries a new link", () => {
    const { container, rerender } = renderWithProviders(
      <ListingPhoto url="https://storage.example/a.jpg?sig=old" size="large" />,
    );
    fireEvent.error(container.querySelector("img")!);
    expect(container.querySelector("img")).toBeNull();

    rerender(<ListingPhoto url="https://storage.example/a.jpg?sig=new" size="large" />);
    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "https://storage.example/a.jpg?sig=new",
    );
  });
});
