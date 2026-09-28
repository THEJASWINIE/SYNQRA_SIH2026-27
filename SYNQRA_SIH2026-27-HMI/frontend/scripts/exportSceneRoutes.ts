/**
 * Export the Mine-Cast demonstration routes for the backend simulation (MINECAST-02).
 *
 *   npx vite-node scripts/exportSceneRoutes.ts
 *
 * Writes `contracts/scene_routes.json` from `demoRoutes()`, using the SAME TerrainConfig
 * the scene builds its terrain and corridors from - the published extent's measured size -
 * so the exported waypoints are exactly the drawn roads. `demoRoutes.test.ts` fails if the
 * committed file is stale, so the two consumers cannot drift apart unnoticed.
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

import { toSceneRoutesDocument } from "../src/minecast/demoRoutes";
import { terrainConfig } from "../src/minecast/terrainField";
import { bailadilaDeposit5, extentSizeMetres, toDecimalExtent } from "../src/state/geoSite";

const OUT = resolve(__dirname, "..", "..", "contracts", "scene_routes.json");

const size = extentSizeMetres(toDecimalExtent(bailadilaDeposit5().extent));
const document = toSceneRoutesDocument(terrainConfig(size.widthM, size.heightM));

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, `${JSON.stringify(document, null, 2)}\n`, "utf-8");

for (const route of document.routes) {
  console.log(
    `${route.vehicle_id}  ${route.route_id}  ${route.waypoints.length} waypoints  ${route.length_m} m  ${route.behaviour}`,
  );
}
console.log(`wrote ${OUT}`);
