import { rarityColors } from "./rarityConfig";

interface DataElement {
  data: (key: string) => string | number | undefined;
}

export const cytoscapeStyles = [
  {
    selector: "node",
    style: {
      shape: "roundrectangle",
      "background-color": (ele: DataElement) => {
        const rarity = ele.data("rarity") as string | undefined;
        const bgColors: Record<string, string> = {
          Common: "rgba(153,159,165,0.15)",
          Uncommon: "rgba(86,203,134,0.15)",
          Rare: "rgba(30,150,252,0.2)",
          Epic: "rgba(216,41,155,0.15)",
          Legendary: "rgba(251,199,0,0.15)",
          missing: "rgba(100,100,100,0.1)",
        };
        if (!rarity) {
          return bgColors.Common;
        }
        return bgColors[rarity] ?? bgColors.Common;
      },
      "background-image": (ele: DataElement) => {
        const imageUrl = ele.data("imageUrl") as string | undefined;
        // Return "none" for empty/missing images to avoid Cytoscape warnings
        return imageUrl && imageUrl.length > 0 ? imageUrl : "none";
      },
      "background-fit": "contain",
      "background-clip": "none",
      "background-position-x": "50%",
      "background-position-y": "50%",
      padding: "12px",
      label: "data(label)",
      color: "#e9d5ff",
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 8,
      "font-size": "11px",
      "font-weight": "bold",
      width: 100,
      height: 100,
      "border-width": 3,
      "border-color": (ele: DataElement) => {
        const rarity = ele.data("rarity") as string | undefined;
        if (!rarity) {
          return "#717471";
        }
        // Handle missing items with a distinct gray border
        if (rarity === "missing") {
          return "#555555";
        }
        const key = rarity as keyof typeof rarityColors;
        return rarityColors[key] ?? "#717471";
      },
      "text-wrap": "wrap",
      "text-max-width": 90,
      "text-background-color": "#07020b",
      "text-background-opacity": 0.85,
      "text-background-padding": 3,
    },
  },
  {
    selector: 'node[type="center"]',
    style: {
      "border-width": 5,
      width: 140,
      height: 140,
      "font-size": "14px",
      "font-weight": "bold",
      "text-margin-y": 10,
    },
  },
  {
    selector: 'node[type="input"]',
    style: {
      "border-width": 3,
    },
  },
  {
    selector: 'node[type="output"]',
    style: {
      "border-width": 3,
    },
  },
  {
    selector: 'node[nodeType="trader"]',
    style: {
      shape: "ellipse",
      "border-color": "#fbbf24",
      width: 120,
      height: 120,
      "background-color": "rgba(251,191,36,0.15)",
    },
  },
  {
    selector: 'node[nodeType="trader"][type="center"]',
    style: {
      width: 160,
      height: 160,
    },
  },
  // Style for missing items (not in database)
  {
    selector: 'node[isMissing="true"], node[rarity="missing"]',
    style: {
      "border-style": "dashed",
      "border-color": "#555555",
      opacity: 0.7,
    },
  },
  {
    selector: "edge",
    style: {
      width: 3,
      "line-color": "#6366f1",
      "target-arrow-shape": "none",
      "curve-style": "unbundled-bezier",
      "control-point-distances": (ele: DataElement) => {
        const curvatureRaw = ele.data("curvature");
        const curvature = typeof curvatureRaw === "number" ? curvatureRaw : 0;
        const dist = Math.abs(curvature) * 0.35;
        return curvature >= 0 ? `${dist} -${dist}` : `-${dist} ${dist}`;
      },
      "control-point-weights": "0.33 0.67",
      "edge-distances": "node-position",
      "source-endpoint": "90deg",
      "target-endpoint": "270deg",
      label: "data(label)",
      "font-size": "11px",
      "line-height": 1.6,
      color: "#c4b5fd",
      "text-outline-color": "#07020b",
      "text-outline-width": 5,
      "text-outline-opacity": 1,
      "text-background-color": "#07020b",
      "text-background-opacity": 1,
      "text-background-padding": 6,
      "text-background-shape": "roundrectangle",
      "text-border-width": 1,
      "text-border-color": "#6366f1",
      "text-border-opacity": 0.4,
      "text-margin-y": -12,
      "text-wrap": "wrap",
      "text-max-width": 140,
    },
  },
  // Edge coloring by relation type
  {
    selector: 'edge[relation*="repair"]',
    style: {
      "line-color": "#ef4444",
    },
  },
  {
    selector: 'edge[relation*="upgrade"]',
    style: {
      "line-color": "#ec4899",
    },
  },
  {
    selector: 'edge[relation*="salvage"]',
    style: {
      "line-color": "#10b981",
    },
  },
  {
    selector: 'edge[relation*="recycle"]',
    style: {
      "line-color": "#34d399",
    },
  },
  {
    selector: 'edge[relation*="craft"]',
    style: {
      "line-color": "#60a5fa",
    },
  },
  {
    selector: 'edge[relation*="trader"], edge[relation*="sold_by"], edge[relation*="trade"]',
    style: {
      "line-color": "#fbbf24",
    },
  },
  {
    selector: ":selected",
    style: {
      "border-width": 6,
      "border-color": "#e879f9",
      "overlay-opacity": 0.3,
      "overlay-color": "#c084fc",
    },
  },
];
