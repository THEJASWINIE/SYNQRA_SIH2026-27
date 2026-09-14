/**
 * Terrain mesh.
 *
 * Turns the height grid from `terrainField.ts` into a Three.js `BufferGeometry`. All the
 * arithmetic lives in that pure module; this file is the thin bridge to the GPU.
 *
 * ==========================================================================
 *  THE SURFACE IS SYNTHETIC. THE MESH INHERITS THAT, IT DOES NOT LAUNDER IT.
 *
 *  Nothing here makes the terrain more trustworthy than the field it came from. The
 *  grid's own `provenance` travels with it, the layer drawer marks it
 *  SYNTHETIC_FOR_DEMO, and `MineScene` paints a persistent caption over the viewport.
 * ==========================================================================
 *
 * BUILT ONCE
 *
 * The geometry is memoised on the grid identity. Terrain does not change when telemetry
 * arrives, and rebuilding ~9k vertices on every frame or every WebSocket message would
 * spend the frame budget for no visual difference.
 *
 * COORDINATE FRAME
 *
 *   x = metres east of the extent's south-west corner
 *   z = metres north of the same corner
 *   y = relative elevation in metres (up)
 *
 * WebGL only. Not unit tested: there is no WebGL context in this Node test environment
 * (M4D-C), so the testable behaviour was pushed into `terrainField.ts` instead.
 */

import { useMemo } from "react";
import { BufferAttribute, BufferGeometry } from "three";

import { type HeightGrid, slopeAt, terrainShade } from "./terrainField";

export function MineTerrain({ grid, visible = true }: { grid: HeightGrid; visible?: boolean }) {
  const geometry = useMemo(() => {
    const { size, widthM, heightM, heights, minM, maxM, verticalExaggeration } = grid;
    const span = maxM - minM || 1;

    const vertexCount = size * size;
    const positions = new Float32Array(vertexCount * 3);
    const colours = new Float32Array(vertexCount * 3);

    for (let row = 0; row < size; row += 1) {
      for (let col = 0; col < size; col += 1) {
        const index = row * size + col;
        const elevation = heights[index] ?? 0;

        positions[index * 3] = (col / (size - 1)) * widthM;
        // TRUE metres come from the field; the multiplier is a DRAW-TIME choice and is
        // disclosed on the viewport caption and in the provenance panel.
        positions[index * 3 + 1] = elevation * verticalExaggeration;
        positions[index * 3 + 2] = (row / (size - 1)) * heightM;

        // Shelves light, faces dark: the slope is what separates a bench top from the
        // wall below it. Pure function, so the contrast is under test.
        const [r, g, b] = terrainShade((elevation - minM) / span, slopeAt(grid, col, row));
        colours[index * 3] = r;
        colours[index * 3 + 1] = g;
        colours[index * 3 + 2] = b;
      }
    }

    // Two triangles per grid cell.
    const indices = new Uint32Array((size - 1) * (size - 1) * 6);
    let cursor = 0;
    for (let row = 0; row < size - 1; row += 1) {
      for (let col = 0; col < size - 1; col += 1) {
        const topLeft = row * size + col;
        const topRight = topLeft + 1;
        const bottomLeft = topLeft + size;
        const bottomRight = bottomLeft + 1;

        indices[cursor] = topLeft;
        indices[cursor + 1] = bottomLeft;
        indices[cursor + 2] = topRight;
        indices[cursor + 3] = topRight;
        indices[cursor + 4] = bottomLeft;
        indices[cursor + 5] = bottomRight;
        cursor += 6;
      }
    }

    const built = new BufferGeometry();
    built.setAttribute("position", new BufferAttribute(positions, 3));
    built.setAttribute("color", new BufferAttribute(colours, 3));
    built.setIndex(new BufferAttribute(indices, 1));
    // Normals are still needed for lighting; the material's flat shading then uses the
    // face normal per triangle so a bench edge is a crisp break, not a smoothed slope.
    built.computeVertexNormals();
    return built;
  }, [grid]);

  return (
    <mesh geometry={geometry} visible={visible}>
      <meshStandardMaterial vertexColors flatShading roughness={0.95} metalness={0} />
    </mesh>
  );
}
