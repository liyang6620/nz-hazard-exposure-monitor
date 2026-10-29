import { useEffect, useMemo, useState } from "react";

interface WaveformData {
  network: string;
  station: string;
  location: string;
  channel: string;
  quantity: string;
  unit: string;
  start_time: string;
  event_origin_time: string;
  points: [number, number][];
}

export function EventWaveform() {
  const [waveform, setWaveform] = useState<WaveformData | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/data/waveforms/2016p858000-wtmc-hnz.json", {
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error("Waveform unavailable");
        return response.json() as Promise<WaveformData>;
      })
      .then(setWaveform)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError"))
          setWaveform(null);
      });
    return () => controller.abort();
  }, []);

  const path = useMemo(() => {
    if (!waveform?.points.length) return "";
    const duration = waveform.points.at(-1)?.[0] ?? 1;
    const maximum = Math.max(
      ...waveform.points.map((point) => Math.abs(point[1])),
      0.001,
    );
    return waveform.points
      .map(([seconds, value], index) => {
        const x = (seconds / duration) * 1000;
        const y = 110 - (value / maximum) * 92;
        return `${index ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
  }, [waveform]);

  if (!waveform)
    return <div className="waveform-loading">Loading GeoNet waveform…</div>;
  return (
    <figure className="waveform-figure">
      <svg
        viewBox="0 0 1000 220"
        role="img"
        aria-labelledby="waveform-title waveform-description"
      >
        <title id="waveform-title">Kaikōura earthquake station waveform</title>
        <desc id="waveform-description">
          Vertical ground acceleration recorded by GeoNet station WTMC, HNZ
          channel, beginning 26 seconds before the earthquake origin.
        </desc>
        <line className="waveform-axis" x1="0" y1="110" x2="1000" y2="110" />
        <path className="waveform-trace" d={path} />
      </svg>
      <figcaption>
        GeoNet station <strong>{waveform.station}</strong> · {waveform.location}
        .{waveform.channel} · {waveform.quantity}, {waveform.unit} · CC BY 3.0
        NZ
      </figcaption>
    </figure>
  );
}
