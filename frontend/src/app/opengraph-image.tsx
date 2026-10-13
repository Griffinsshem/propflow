import { ImageResponse } from "next/og";

export const alt = "PropFlow: maintenance requests that don't get lost";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** The card shown when a PropFlow link is shared (WhatsApp, LinkedIn, Slack). */
export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px",
        background: "linear-gradient(135deg, #4f46e5 0%, #312e81 100%)",
        color: "white",
      }}
    >
      <div style={{ fontSize: 40, fontWeight: 700, opacity: 0.9 }}>PropFlow</div>
      <div style={{ fontSize: 72, fontWeight: 700, marginTop: 24, lineHeight: 1.1 }}>
        {"Maintenance requests that don't get lost."}
      </div>
      <div style={{ fontSize: 32, marginTop: 28, opacity: 0.85 }}>
        {"From a tenant's report to a closed work order."}
      </div>
    </div>,
    size,
  );
}
