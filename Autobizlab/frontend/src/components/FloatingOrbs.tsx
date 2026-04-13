const ORBS = [
  { left: "8%", top: "12%", size: 280, delay: "0s", duration: "24s" },
  { left: "72%", top: "8%", size: 200, delay: "-4s", duration: "20s" },
  { left: "45%", top: "65%", size: 340, delay: "-8s", duration: "28s" },
  { left: "18%", top: "48%", size: 160, delay: "-2s", duration: "18s" },
  { left: "85%", top: "42%", size: 220, delay: "-12s", duration: "22s" },
  { left: "55%", top: "22%", size: 120, delay: "-6s", duration: "16s" },
  { left: "5%", top: "78%", size: 190, delay: "-10s", duration: "26s" },
  { left: "92%", top: "75%", size: 140, delay: "-14s", duration: "19s" },
  { left: "38%", top: "88%", size: 260, delay: "-3s", duration: "25s" },
  { left: "62%", top: "52%", size: 100, delay: "-7s", duration: "17s" },
];

export function FloatingOrbs() {
  return (
    <div className="orb-layer" aria-hidden>
      {ORBS.map((o, i) => (
        <div
          key={i}
          className="orb"
          style={{
            left: o.left,
            top: o.top,
            width: o.size,
            height: o.size,
            animationDelay: o.delay,
            animationDuration: o.duration,
          }}
        />
      ))}
    </div>
  );
}
