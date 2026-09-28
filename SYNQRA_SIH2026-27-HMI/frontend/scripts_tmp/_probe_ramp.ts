import { bailadilaDeposit5, extentSizeMetres, toDecimalExtent } from "../src/state/geoSite";
import { terrainConfig, elevationAt } from "../src/minecast/terrainField";
import { rampCentreline } from "../src/minecast/pitMorphology";

const size = extentSizeMetres(toDecimalExtent(bailadilaDeposit5().extent));
const config = terrainConfig(size.widthM, size.heightM);
const ramp = rampCentreline(config.pit);
console.log("total points", ramp.length);
// legs: approach 0..10, first 11..50 (40 steps -> 41 pts, minus first dup = 40 new), second next 40, third next 30
// indices boundary: approach len 11 (0..10), first.slice(1) len 40 -> indices 11..50, second.slice(1) len40 -> 51..90, third.slice(1) len30 -> 91..120
const boundaries = [10, 11, 50, 51, 90, 91];
for (let i = 1; i < ramp.length; i++) {
  const a = ramp[i-1], b = ramp[i];
  const dx = b.x - a.x, dy = b.y - a.y;
  const dist = Math.hypot(dx, dy);
  const ea = elevationAt(a.x, a.y, config);
  const eb = elevationAt(b.x, b.y, config);
  const dElev = eb - ea;
  if (Math.abs(dElev) > 1.5 || boundaries.includes(i)) {
    console.log(`i=${i} dist=${dist.toFixed(2)} dElev=${dElev.toFixed(2)} u_a=${a.u.toFixed(3)} u_b=${b.u.toFixed(3)} depth_a=${a.depthM.toFixed(1)} depth_b=${b.depthM.toFixed(1)}`);
  }
}
