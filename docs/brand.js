// The Katip mark: a split-flap tile with a lime K, from the same family as the F on fikrifirat.com.
// Shared by the optional centre stamp on masked PDFs and images. Units: a 32 x 32 tile, y down.
// Paths are lists of commands: ["M", x, y], ["L", x, y], ["C", x1, y1, x2, y2, x, y], ["Z"].
const K = 0.5523;
function halfTile(y, h, r, top) {
  // a rectangle with rounded corners on one side (top half: top corners; bottom half: bottom corners)
  const x0 = 0, x1 = 32, y0 = y, y1 = y + h, c = r * K;
  return top
    ? [["M", x0, y1], ["L", x0, y0 + r], ["C", x0, y0 + r - c, x0 + r - c, y0, x0 + r, y0], ["L", x1 - r, y0],
       ["C", x1 - r + c, y0, x1, y0 + r - c, x1, y0 + r], ["L", x1, y1], ["Z"]]
    : [["M", x0, y0], ["L", x1, y0], ["L", x1, y1 - r], ["C", x1, y1 - r + c, x1 - r + c, y1, x1 - r, y1], ["L", x0 + r, y1],
       ["C", x0 + r - c, y1, x0, y1 - r + c, x0, y1 - r], ["Z"]];
}
export const MARK = {
  top: halfTile(0, 15.4, 6, true),       // #1F242B
  bottom: halfTile(16.6, 15.4, 6, false), // #191D23
  k: [["M", 11, 7], ["L", 11, 25], ["M", 21.5, 7], ["L", 11.6, 16.6], ["M", 15.2, 13.2], ["L", 21.5, 25]],  // lime stroke 3.6, round
  colors: { top: [0.122, 0.141, 0.169], bottom: [0.098, 0.114, 0.137], k: [0.831, 1, 0.227] },
  stroke: 3.6,
};

// Draw the mark on a 2D canvas context at (ox, oy), scale k per unit.
export function drawMark(g, ox, oy, s, alpha) {
  const css = v => `rgb(${v.map(x => Math.round(x * 255)).join(",")})`;
  const path = cmds => { g.beginPath(); for (const [op, ...a] of cmds) {
    const p = a.map((v, i) => (i % 2 ? oy : ox) + v * s);
    if (op === "M") g.moveTo(...p); else if (op === "L") g.lineTo(...p); else if (op === "C") g.bezierCurveTo(...p); else g.closePath(); } };
  g.save(); g.globalAlpha = alpha;
  g.fillStyle = css(MARK.colors.top); path(MARK.top); g.fill();
  g.fillStyle = css(MARK.colors.bottom); path(MARK.bottom); g.fill();
  g.strokeStyle = css(MARK.colors.k); g.lineWidth = MARK.stroke * s; g.lineCap = "round"; g.lineJoin = "round"; path(MARK.k); g.stroke();
  g.restore();
}
