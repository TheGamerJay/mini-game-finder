export function getMode(def = "easy") {
    const p = location.pathname.split('/').filter(Boolean);
    // /play/<mode>
    if (p[0] === "play") return (p[1] || def).toLowerCase();
    // /riddle/mode/<mode>
    if (p[0] === "riddle" && p[1] === "mode") return (p[2] || def).toLowerCase();
    // fallback ?mode=
    const q = new URLSearchParams(location.search).get("mode");
    return (q || def).toLowerCase();
}

export function setModeInURL(mode) {
    const validModes = ["easy", "medium", "hard"];
    if (!validModes.includes(mode.toLowerCase())) {
        mode = "easy";
    }

    const p = location.pathname.split('/').filter(Boolean);

    // Handle /play/<mode> pattern
    if (p[0] === "play") {
        location.href = `/play/${mode.toLowerCase()}`;
        return;
    }

    // Handle /riddle/mode/<mode> pattern
    if (p[0] === "riddle" && p[1] === "mode") {
        location.href = `/riddle/mode/${mode.toLowerCase()}`;
        return;
    }

    // Fallback: use query parameter
    const url = new URL(location);
    url.searchParams.set("mode", mode.toLowerCase());
    location.href = url.toString();
}