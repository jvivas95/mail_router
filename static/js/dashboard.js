/**
 * dashboard.js — Lógica del lado del cliente
 */

// ── Flash messages: Ocultar automáticamente ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    const flashes = Array.from(document.querySelectorAll(".flash, #flash-msg"));
    if (flashes.length === 0) return;

    setTimeout(() => {
        flashes.forEach((el) => {
            el.style.transition = "opacity 0.5s, transform 0.5s";
            el.style.opacity = "0";
            el.style.transform = "translateX(20px)";
            setTimeout(() => el.remove(), 500);
        });
    }, 4000);
});

    // ── Stats: polling cada 30 segundos ───────────────────────────────────────────
    function updateStats() {
    fetch("/api/stats")
    .then((r) => r.json())
    .then((data) => {
        const map = {
        "stat-total": data.total,
        "stat-forwarded": data.forwarded,
        "stat-pending": data.pending,
        "stat-errors": data.errors,
        };
        Object.entries(map).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el && el.textContent !== String(val)) {
            el.textContent = val;
            el.style.transition = "color 0.3s";
            el.style.color = "#fff";
            setTimeout(() => (el.style.color = ""), 400);
        }
        });
    })
    .catch(() => {}); // silenciar errores de red
}

setInterval(updateStats, 30_000);
updateStats(); // actualización inicial