// Presentation only. The native navigation/tab bars keep the host's own sizing.
function textScale(host) {
  try {
    const info = host.getAppBaseInfo ? host.getAppBaseInfo() : {};
    const scale = Number(info.fontSizeScaleFactor) || Number(info.fontSizeSetting) / 16;
    return Number.isFinite(scale) && scale > 0 ? Math.max(1, scale) : 1;
  } catch (_) { return 1; }
}
module.exports = { textScale };
