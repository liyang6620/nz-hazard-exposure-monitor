import type { MmiBand } from "../data/types";

export function chartBands(bands: MmiBand[]): MmiBand[] {
  return bands.filter((band) => !["<4", "4"].includes(band.mmi_band));
}
